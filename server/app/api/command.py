##############################################################################
#    本登録テーブルを更新するコマンド系API
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
        request -- GET リクエスト
            request.args.get("action"): "used" or "shoppinglist" or "remind",
                // used: 既に消費したものとして扱う
                // shopppinglist: Slackの買い物リストチャンネルに追記して以後通知の対象から外す
                // remind: 賞味期限が切れたときに再通知する
            request.args.get("product_id"): xxxxx
                // 本登録テーブル上のID

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

    # クエリー文字列取り出し
    action = request.args.get("action")
    product_id = request.args.get("product_id")

    with common.create_session() as session:
        try:
            product = session \
                .query(Product) \
                .filter(Product.id == product_id) \
                .one()
        except NoResultFound:
            response = {
                "success": False,
                "message": f"指定された本登録IDに該当するレコードを特定できませんでした: {product_id}",
            }
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
                message = f"買い物リストチャンネルへの投稿に失敗しました"
                logger.exception(message, e)
                response = {
                    "success": False,
                    "message": message,
                }
                logger.info(f"API Exit: {response}")
                return response

            product.added_shopping_list = 1
        else:
            response = {
                "success": False,
                "message": f"無効な操作名が指定されました: {action}",
            }
            logger.info(f"API Exit: {response}")
            return response

        session.commit()

    response = {
        "success": True,
        "message": None,
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
