##############################################################################
#    Slackに本登録済みの情報を列挙するAPI
##############################################################################
import os
import datetime
import requests
import traceback
import json
from requests.exceptions import HTTPError
from datetime import datetime as dt
from typing import Any, Dict, List
from configparser import ConfigParser
from sqlalchemy.orm.exc import NoResultFound

# 独自モジュール読み込み
import app.common as common
from model.products import Product
logger = common.get_logger("listup")

# 設定ファイル読み込み
config = ConfigParser()
config.read("settings.conf", encoding="utf-8")

##### 設定読み込み ####################
# Slack API トークン
SLACK_TOKEN = config.get("slack", "token")
# メッセージを送信するための Slack Incoming Webhook URL
SLACK_INCOMING_WEBHOOK_URL = config.get("slack", "incoming_webhook_url")
# このサーバーの外から見たときのURLのベース
URL_NAME_BASE = config.get("slack", "url_name_base")

##### 定数定義 ####################
# 本登録済みの商品イメージ画像を取得するためのURL
GET_IMAGE_URL = f"https://{URL_NAME_BASE}/images/"


def execute(request) -> Dict[str, Any]:
    """本登録済みの商品のうち、期限前で未アクションの商品イメージ画像と賞味期限をすべてSlack通知します。

    Arguments:
        request -- GET リクエスト

    Returns:
        Dict[str, Any] -- 処理結果
            {
                // 操作に成功したかどうか
                "success": False or True
            }
    """
    logger.info(f"API Called.")

    with common.create_session() as session:
        # 期限前で未アクションの商品をすべて抽出
        products = session \
            .query(Product) \
            .filter(
                dt.date(Product.expiration_date) > dt.today() and \
                not Product.added_shopping_list and \
                not Product.consumed \
            ) \
            .all()

        # Slackに情報を送信
        _send_products(products)

    response = {
        "success": True,
    }
    logger.info(f"API Exit: {response}")
    return response


def _send_products(host_url: str, products: List[Product]):
    """Slackの通知用リストチャンネルに商品情報を投稿します。

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
        "token": SLACK_TOKEN,
        "channel": SLACK_NOTIFY_CHANNEL,
        "text": "現在管理されている商品は以下の通りです。" if len(products) > 0 else "現在管理されている商品はありません。",
        "attachments": [
            {
                "text": f"{dt.strftime(product.created_time, '登録日: %Y-%m-%d')}",
                "image_url": image_urls[i],
                "fallback": "This food have not expired yet.",
                # "color": "good",
                "attachment_type": "default",
                "pretext": f"期限: {dt.strftime(product.expiration_date, '%Y-%m-%d')}",
            }
            for i, product in enumerate(products)
        ],
    }
    logger.debug(f"Slack API Request Parameters:\n{json.dumps(parameters, indent=4)}")

    # Slack API に POST する
    response = requests.post(
        url=SLACK_INCOMING_WEBHOOK_URL,
        data=json.dumps(parameters),
        headers={"Content-Type": "application/json"}
    )
    logger.debug(f"Slack API Response: {response.status_code}\n{response.text}")

    # ステータスコードが 200 以外であれば例外を投げる
    response.raise_for_status()
