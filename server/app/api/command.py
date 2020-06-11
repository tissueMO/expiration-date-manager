##############################################################################
#    本登録テーブルを更新するコマンド系API
##############################################################################
import os
import datetime
import requests
import traceback
import re
import json
from requests.exceptions import HTTPError
from datetime import datetime as dt
from typing import Any, Dict, List
from configparser import ConfigParser
from sqlalchemy.orm.exc import NoResultFound

# 独自モジュール読み込み
import app.common as common
from model.products import Product
logger = common.get_logger("command")

# 設定ファイル読み込み
config = ConfigParser()
config.read("settings.conf", encoding="utf-8")

##### 設定読み込み ####################
# Slack API トークン
SLACK_TOKEN = config.get("slack", "token")
# Slack 買い物リストチャンネル
SLACK_SHOPPINGLIST_CHANNEL = config.get("command", "shoppinglist_channel")

##### 定数定義 ####################
# ファイルアップロードを行うための Slack API エンドポイント
SLACK_FILE_UPLOAD_URL = "https://slack.com/api/files.upload"


def execute(request) -> Dict[str, Any]:
    """本登録済みの商品に対して任意のアクションを行います。

    Arguments:
        request -- POST リクエスト
            {
                "callback_id": "command_xxx",
                    // SlackのAttachmentsに設定されたコールバックID、xxxの部分は本登録テーブル上のID
                "actions": [
                    {
                        "name": "command",
                        "value": "...",
                            // used: 既に消費したものとして扱う
                            // shopppinglist: Slackの買い物リストチャンネルに追記して以後通知の対象から外す
                            // remind: 賞味期限が切れたときに再通知する
                        ...
                    },
                ],
                ...
            }

    Returns:
        Dict[str, Any] -- 処理結果
            {
                // 操作に成功したかどうか
                "success": False or True,

                // 操作に失敗した原因を表すメッセージ
                "message": "..."
            }
    """
    logger.info(f"API Called.")

    # URLエンコードされた特殊なペイロードを辞書型に変換
    payload = common.decode_request_payload(request)
    logger.debug(f"payload={payload}")

    # リクエストパラメーター取り出し
    request_json = json.loads(payload)
    action = request_json["actions"][0]["value"]
    original_message = request_json["original_message"]
    callback_id = request_json["callback_id"]
    product_id = re.match(r"command_(\d+)", callback_id).groups()[0]
    attachment_index = [
        i
        for i, attachment in enumerate(request_json["original_message"]["attachments"])
        if attachment["callback_id"] == callback_id
    ][0]
    logger.debug(f"attachments[{attachment_index}]: callback_id={callback_id}")

    with common.create_session() as session:
        try:
            product = session \
                .query(Product) \
                .filter(Product.id == product_id) \
                .one()
        except NoResultFound:
            response = f"指定された本登録IDに該当するレコードを特定できませんでした: {product_id}"
            logger.info(f"API Exit: {response}")
            return response

        if action == "used":
            # 既に消費したので以後通知の対象としない
            product.consumed = 1
        elif action == "remind":
            # 特に何もしない
            pass
        elif action == "shoppinglist":
            # 買い物リストチャンネルに投稿して以後通知の対象としない
            try:
                _add_shopping_list(product.image_path)
            except HTTPError as e:
                response = f"買い物リストチャンネルへの投稿に失敗しました"
                logger.exception(response, e)
                logger.info(f"API Exit: {response}")
                return response

            product.added_shopping_list = 1
        else:
            response = f"無効な操作名が指定されました: {action}"
            logger.info(f"API Exit: {response}")
            return response

        session.commit()

    # コマンドの元となったメッセージのうち今回処理したデータを抜いて返す
    del original_message["attachments"][attachment_index]
    if len(original_message["attachments"]) > 0:
        # まだ他のリマインドが残っていたら元のメッセージを置き換える
        response = {
            "text": original_message["text"],
            "attachments": original_message["attachments"],
            "replace_original": True,
        }
    else:
        # すべてのリマインドを処理し終わったら元のメッセージを消す
        response = {
            "delete_original": True,
        }

    logger.info(f"API Exit: {response}")
    return response


def _add_shopping_list(product_image_path: str):
    """Slackの買い物リストチャンネルに追記します。

    Arguments:
        product_image_path {str} -- 追記する商品イメージ画像のパス

    Raises:
        HTTPError - Slack API の呼出に失敗
    """
    # POST リクエストパラメーターを生成
    target_files = {"file": open(product_image_path, "rb")}
    parameters = {
        "token": SLACK_TOKEN,
        "channels": SLACK_SHOPPINGLIST_CHANNEL,
        "filename": os.path.basename(product_image_path)
    }

    # Slack API に POST する
    response = requests.post(
        url=SLACK_FILE_UPLOAD_URL,
        params=parameters,
        files=target_files
    )
    logger.debug(f"Slack API Response: {response.status_code}\n{response.text}")

    # ステータスコードが 200 以外であれば例外を投げる
    response.raise_for_status()
