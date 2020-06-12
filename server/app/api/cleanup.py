##############################################################################
#    古くなった不要データをクリーンアップするAPI
##############################################################################
import os
import datetime
import traceback
from datetime import datetime as dt
from typing import Any, Dict, List
from configparser import ConfigParser
from sqlalchemy import func

# 独自モジュール読み込み
import app.log as log
import app.common as common
from model.temporary_products import TemporaryProduct
from model.products import Product
logger = log.get_logger("cleanup")

# 設定ファイル読み込み
config = ConfigParser()
config.read("settings.conf", encoding="utf-8")

##### 設定読み込み ####################
# クリーンアップ対象とする現在の日にちを起点とした経過日数
THRESHOLD_DAYS = int(config.get("cleanup", "threshold_days"))


def execute(request) -> Dict[str, Any]:
    """古くなった不要データのクリーンアップを行います。

    Arguments:
        request -- GET リクエスト

    Returns:
        Dict[str, Any] -- 処理結果
            {
                // クリーンアップ処理に成功したかどうか
                "success": False or True,

                // クリーンアップしたレコードの総数
                "count": xxx
            }
    """
    logger.info(f"API Called.")

    with common.create_session() as session:
        count = 0
        target_date = dt.combine(dt.now(), datetime.time()) - datetime.timedelta(days=THRESHOLD_DAYS-1)

        temporary_products = session \
            .query(TemporaryProduct) \
            .filter(TemporaryProduct.created_time < target_date) \
            .all()
        count += len(temporary_products)
        for temporary_product in temporary_products:
            session.delete(temporary_product)

        # 本登録データは商品イメージ画像ファイルと合わせて削除
        products = session \
            .query(Product) \
            .filter(Product.expiration_date < target_date) \
            .all()
        count += len(products)
        for product in products:
            logger.debug(f"Deleting: {os.path.basename(product.image_path)}")
            os.remove(product.image_path)
            session.delete(product)

        # トランザクション確定
        session.commit()

    response = {
        "success": True,
        "count": count,
    }
    logger.info(f"API Exit: {response}")
    return response
