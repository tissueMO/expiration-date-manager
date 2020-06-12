##############################################################################
#    Slackに本登録済みの情報を送信するAPI
#    numpy は同一プロセスの別スレッド内で重複して使用できないため注意が必要
##############################################################################
import os
import datetime
import requests
import traceback
import json
import time
from requests.exceptions import HTTPError
from datetime import datetime as dt
from typing import Any, Dict, List
from configparser import ConfigParser

# 独自モジュール読み込み
import app.log as log
from model.products import Product
logger = log.get_logger("listup_async")

# 設定ファイル読み込み
config = ConfigParser()
config.read("settings.conf", encoding="utf-8")

##### 設定読み込み ####################
# メッセージを送信するための Slack Incoming Webhook URL
SLACK_INCOMING_WEBHOOK_URL = config.get("slack", "incoming_webhook_url")


def execute(request):
    """与えられた商品イメージ画像と賞味期限の情報をすべてSlackへ書き出します。

    Arguments:
        request -- POST リクエスト
            {
                // JSON形式で与えられたパラメーターをそのままSlackに渡します
                ...
            }
    """
    logger.info(f"API Called.")

    # リクエストパラメーター取り出し
    parameters = json.dumps(request.json)
    logger.debug(f"Parameters={parameters}")

    # 一定時間待機して呼出元のリクエストが完了するのを待つ
    logger.debug(f"Waiting for source request...")
    time.sleep(1.0)

    # Slack API に POST する
    response = requests.post(
        url=SLACK_INCOMING_WEBHOOK_URL,
        data=parameters,
        headers={"Content-Type": "application/json"}
    )
    logger.debug(f"Slack API Response: {response.status_code}\n{response.text}")

    # ステータスコードが 200 以外であれば例外を投げる
    response.raise_for_status()

    logger.info(f"API Exit: {response.text}")
    return response.text
