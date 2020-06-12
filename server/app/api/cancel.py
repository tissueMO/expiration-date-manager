##############################################################################
#    仮登録セッションIDを破棄するAPI
##############################################################################
import os
import json
from typing import Any, Dict, List
from configparser import ConfigParser
from sqlalchemy.orm.exc import NoResultFound

# 独自モジュール読み込み
import app.common as common
import app.log as log
from model.temporary_products import TemporaryProduct
from model.products import Product
logger = log.get_logger("cancel")

# 設定ファイル読み込み
config = ConfigParser()
config.read("settings.conf", encoding="utf-8")


def execute(request) -> Dict[str, Any]:
    """与えられたセッションIDに該当する仮登録レコードを削除します。

    Arguments:
        request -- POST リクエスト
            {
                // 仮登録テーブルに紐づけられたセッションID
                "session_id": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
            }

    Returns:
        Dict[str, Any] -- 処理結果
            {
                // 仮登録のキャンセルに成功したかどうか
                "success": False or True,

                // 仮登録のキャンセルに失敗した原因を表すメッセージ
                "message": "..."
            }
    """
    logger.info(f"API Called.")

    # リクエストパラメーター取り出し
    session_id = request.json["session_id"]
    logger.info(f"仮登録セッションID: [{session_id}]")

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
                "message": f"指定されたセッションIDから仮登録テーブル上の該当するレコードを特定できませんでした: {session_id}"
            }
            logger.info(f"API Exit: {response}")
            return response

        # 仮登録テーブルから該当レコードを削除
        session.delete(target_temporary_product)

        session.commit()

    response = {
        "success": True,
        "message": None,
    }
    logger.info(f"API Exit: {response}")
    return response
