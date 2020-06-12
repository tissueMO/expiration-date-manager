##############################################################################
#    本登録済みの商品イメージ画像をバイナリーデータとして返すAPI
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
from flask import Response, send_from_directory

# 独自モジュール読み込み
import app.log as log
from model.products import Product
logger = log.get_logger("image")

# 設定ファイル読み込み
config = ConfigParser()
config.read("settings.conf", encoding="utf-8")

##### 設定読み込み ####################
# 画像保管先を表すディレクトリーパス
DESTINATION_DIRECTORY_PATH = config.get("register", "destination_directory_path")


def execute(file_name: str) -> Response:
    """指定したファイル名に合致する本登録済み商品イメージ画像のバイナリーを返します。

    Arguments:
        file_name {str} -- ファイル名

    Returns:
        Response -- 画像データ
            存在しないファイル名が指定された場合はステータスコード 404 として無効なレスポンスを返す
            ファイル名の中にディレクトリーをまたぐような記述が見られた場合はステータスコード 400 として無効なレスポンスを返す
    """
    logger.info(f"API Called.")

    # ディレクトリートラバーサル判定
    if re.match(r"\.\.|\\|\/", file_name) is not None:
        return Response(
            response="Includes Forbidden Characters",
            status=400
        )

    # ファイル存在チェック
    if not os.path.exists(os.path.join(DESTINATION_DIRECTORY_PATH, file_name)):
        return Response(
            response="Not Found",
            status=404
        )

    # ファイルを読み取って返す
    return send_from_directory(DESTINATION_DIRECTORY_PATH, file_name)
