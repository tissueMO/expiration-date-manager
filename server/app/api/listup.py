##############################################################################
#    Slackに本登録済みの情報を非同期的に列挙するAPI
##############################################################################
import os
import datetime
import requests
import traceback
import json
import subprocess
from requests.exceptions import HTTPError
from datetime import datetime as dt
from typing import Any, Dict, List
from configparser import ConfigParser

# 独自モジュール読み込み
import app.log as log
import app.common as common
from model.products import Product
logger = log.get_logger("listup")

# 設定ファイル読み込み
config = ConfigParser()
config.read("settings.conf", encoding="utf-8")

##### 設定読み込み ####################
# このサーバーの外から見たときのURLのベース
URL_NAME_BASE = config.get("slack", "url_name_base")

##### 定数定義 ####################
# 本登録済みの商品イメージ画像を取得するためのURL
GET_IMAGE_URL = f"https://{URL_NAME_BASE}/images/"
# 非同期的にSlackに商品イメージ画像と賞味期限を送信するためのURL
LISTUP_ASYNC_URL = f"http://localhost/listup/async"


def execute(request) -> Dict[str, Any]:
    """本登録済みの商品のうち、期限前で未アクションの商品イメージ画像と賞味期限をすべてSlack通知します。
    Slackコマンドへの応答速度を優先するため、実際の通知は非同期的に行います。

    Arguments:
        request -- POST リクエスト

    Returns:
        Dict[str, Any] -- 処理結果
            {
                // 表示メッセージ
                "text": "..."
            }
    """
    logger.info(f"API Called.")

    with common.create_session() as session:
        # 期限前で未アクションの商品をすべて抽出
        target_date = dt.combine(dt.now(), datetime.time())
        products = session \
            .query(Product) \
            .filter(Product.expiration_date >= target_date) \
            .filter(Product.added_shopping_list == 0) \
            .filter(Product.consumed == 0) \
            .order_by(Product.expiration_date) \
            .order_by(Product.created_time) \
            .all()

        # 非同期的にSlackに情報を送信
        _send_products_async(products)

        if len(products) > 0:
            message = f"現在、{len(products)}件の商品が管理されています。"
        else:
            message = f"現在管理されている商品はありません。"

        response = {
            "text": message,
        }

    logger.info(f"API Exit: {response}")
    return response


def _send_products_async(products: List[Product]):
    """非同期的にSlackの通知用リストチャンネルに商品情報を投稿します。

    Arguments:
        products {List[Product]} -- 商品リスト

    Raises:
        HTTPError - Slack API の呼出に失敗
    """
    # 公開用画像URLのリストに変換
    image_urls = [
        f"{GET_IMAGE_URL}{os.path.basename(product.image_path)}"
        for product in products
    ]

    # POST リクエストパラメーターを生成
    parameters = {
        "text": "",
        "attachments": [
            {
                "text": "",
                "image_url": image_urls[i],
                "fallback": "This food have not expired yet.",
                # "color": "good",
                "attachment_type": "default",
                "pretext": f"期限日：{dt.strftime(product.expiration_date, '%Y-%m-%d')} ({dt.strftime(product.created_time, '登録日：%Y-%m-%d')})",
            }
            for i, product in enumerate(products)
        ],
    }
    logger.debug(f"Slack API Request Parameters:\n{json.dumps(parameters, indent=4)}")

    # 非同期的にメッセージを送信する
    command = [
      "curl", "-X", "POST", "-H", "Content-Type: application/json",
      "-d", json.dumps(parameters), LISTUP_ASYNC_URL
    ]
    subprocess.Popen(command)
