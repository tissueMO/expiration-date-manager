##############################################################################
#    商品イメージと仮登録セッションIDを紐づけて本登録を行うAPI
##############################################################################
import os
import cv2
import numpy as np
import json
import datetime
from datetime import datetime as dt
from typing import Any, Dict, List
from configparser import ConfigParser
from sqlalchemy.orm.exc import NoResultFound

# 独自モジュール読み込み
import app.common as common
from model.temporary_products import TemporaryProduct
from model.products import Product
logger = common.get_logger("register")

# 設定ファイル読み込み
config = ConfigParser()
config.read("settings.conf", encoding="utf-8")

##### 設定読み込み ####################
# 画像保管先を表すディレクトリーパス
DESTINATION_DIRECTORY_PATH = config.get("register", "destination_directory_path")


def execute(request) -> Dict[str, Any]:
    """JPEG形式の画像を整数の配列で表したデータとセッションIDを紐づけて本登録を行います。

    Arguments:
        request -- POST リクエスト
            {
                // 仮登録テーブルに紐づけられたセッションID
                "session_id": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",

                // JPEG圧縮した画像を uint8 配列で並べたデータ
                "image": [uint8, uint8, ...]
            }

    Returns:
        Dict[str, Any] -- 処理結果
            {
                // 本登録に成功したかどうか
                "success": False or True,

                // 本登録に失敗した原因を表すメッセージ
                "message": "..."
            }
    """
    logger.info(f"API Called.")

    # リクエストパラメーター取り出し
    session_id = request.json["session_id"]
    image = common.convert_request_image_to_ndarray(request.json["image"])
    logger.info(f"仮登録セッションID: [{session_id}]")

    # セッションIDのファイル名でサーバーに商品画像を保管する
    if not os.path.exists(DESTINATION_DIRECTORY_PATH):
        os.makedirs(DESTINATION_DIRECTORY_PATH, exist_ok=True)
    image_path = os.path.join(DESTINATION_DIRECTORY_PATH, f"{session_id}.jpg")
    cv2.imwrite(image_path, image)

    with common.create_session() as session:
        # 仮登録テーブルの該当レコードを取得
        try:
            target_temporary_product = session \
                .query(TemporaryProduct) \
                .filter(TemporaryProduct.session_id == session_id) \
                .one()
        except NoResultFound:
            response = {
                "success": False,
                "message": f"指定されたセッションIDから仮登録テーブル上の該当するレコードを特定できませんでした: {session_id}",
            }
            logger.info(f"API Exit: {response}")
            return response

        # 本登録テーブルに追加
        session.add(Product(
            image_path=image_path,
            expiration_date=target_temporary_product.expiration_date,
            consumed=False,
            added_shopping_list=False,
            created_time=dt.now()
        ))

        # 仮登録テーブルから該当レコードを削除
        session.delete(target_temporary_product)

        session.commit()

    response = {
        "success": True,
        "message": None,
    }
    logger.info(f"API Exit: {response}")
    return response
