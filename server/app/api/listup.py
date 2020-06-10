##############################################################################
#    Slackに本登録済みの情報を列挙するAPI
##############################################################################
import os
import datetime
import requests
import traceback
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
# Slack 通知用チャンネル
SLACK_NOTIFY_CHANNEL = config.get("slack", "notify_channel")

##### 定数定義 ####################
# メッセージを書き込むための Slack API エンドポイント
SLACK_POST_MESSAGE_URL = "https://slack.com/api/chat.postMessage"
# 本登録済みの商品イメージ画像を取得するためのURL
GET_IMAGE_URL = "images/"


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
        _send_products(request.host_url, products)

    response = {
        "success": True,
    }
    logger.info(f"API Exit: {response}")
    return response


def _send_products(host_url: str, products: List[Product]):
    """Slackの通知用リストチャンネルに商品情報を投稿します。

    Arguments:
        host_url {str} -- このサーバーのホスト名
        products {List[Product]} -- 商品リスト

    Raises:
        HTTPError - Slack API の呼出に失敗
    """
    # 公開用画像URLのリストに変換
    image_urls = [
        f"{host_url}{GET_IMAGE_URL}{os.path.basename(products.image_path)}"
        for product in products
    ]

    # POST リクエストパラメーターを生成
    parameters = {
        "token": SLACK_TOKEN,
        "channels": SLACK_NOTIFY_CHANNEL,
        "text": "現在管理されている商品は以下の通りです。",
        "attachments": [
            {
                "fallback": "This food have not expired yet.",
                # "color": "good",
                "image_url": image_urls[i],
                "attachment_type": "default",
                "pretext": f"期限: {dt.strftime(product.expiration_date, '%Y-%m-%d')}",
            }
            for i, product in enumerate(products)
        ],
    }

    # Slack API に POST する
    response = requests.post(
        url=SLACK_POST_MESSAGE_URL,
        params=parameters
    )
    logger.debug(f"Slack API Response: {response.status_code}\n{response.text}")

    # ステータスコードが 200 以外であれば例外を投げる
    response.raise_for_status()
