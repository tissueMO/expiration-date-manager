##############################################################################
#    Slackにリマインド通知を送るAPI
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
logger = common.get_logger("remind")

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
    """呼び出された時点の日付を起点に数えて {days} 日後に賞味期限が切れるものをピックアップしてSlack通知します。
    ただし、呼び出された時点の日付から {days} 日後までの間に期限切れとなるものについては対象外となります。
    たとえば、days=3 のとき 1日後、2日後に期限が切れるものは取得できず、3日後に期限が切れるものだけが抽出されます。

    Arguments:
        request -- GET リクエスト
            request.args.get("days"): ピックアップ対象とする呼出時点の日付を起点とした日数 (+で未来、0で当日、-で過去)

    Returns:
        Dict[str, Any] -- 処理結果
            {
                // 操作に成功したかどうか
                "success": False or True
            }
    """
    logger.info(f"API Called.")

    # クエリー文字列取り出し
    days = request.args.get("days")

    with common.create_session() as session:
        # 指定された日数後に賞味期限が切れるものを抽出
        target_date = dt.date(dt.today() + datetime.timedelta(days=days))
        target_products = session \
            .query(Product) \
            .filter(
                dt.date(Product.expiration_date) == target_date and \
                not Product.added_shopping_list and \
                not Product.consumed \
            ) \
            .all()

        # Slackにリマインド通知を送信
        _push_remind_to_slack(request.host_url, days, target_products)

    response = {
        "success": True,
    }
    logger.info(f"API Exit: {response}")
    return response


def _push_remind_to_slack(host_url: str, days: int, products: List[Product]):
    """Slackの通知用チャンネルにコマンドボタン付きリマインドを送信します。

    Arguments:
        host_url {str} -- このサーバーのホスト名
        days {int} -- あと何日で期限切れになるかを表す日数
        products {List[Product]} -- リマインド対象の本登録商品リスト

    Raises:
        HTTPError - Slack API の呼出に失敗
    """
    if len(products) == 0:
        # 1件も無い場合は何もしない
        logger.info(f"リマインド対象の商品がありません")
        return

    # 公開用画像URLのリストに変換
    image_urls = [
        f"{host_url}{GET_IMAGE_URL}{os.path.basename(products.image_path)}"
        for product in products
    ]

    if days == 0:
        message = f"本日、期限が切れます。"
    elif days > 0:
        message = f"あと {days} 日で期限が切れます。"
    else:
        message = f"{days} 日前に期限が切れています。"

    # POST リクエストパラメーターを生成
    parameters = {
        "token": SLACK_TOKEN,
        "channels": SLACK_NOTIFY_CHANNEL,
        "text": message,
        "attachments": [
            {
                "fallback": "This food has expired.",
                "callback_id": f"command_{product.id}",
                "color": "warning",
                "image_url": image_urls[i],
                "attachment_type": "default",
                "actions": [
                    {
                        "name": "action",
                        "type": "button",
                        "value": "used",
                        "text": "消費済み",
                    },
                    {
                        "name": "action",
                        "type": "button",
                        "value": "shoppinglist",
                        "text": "買い物リストに追加",
                    },
                    {
                        "name": "action",
                        "type": "button",
                        "value": "remind",
                        "text": "当日に再通知",
                    },
                ],
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
