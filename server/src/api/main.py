##############################################################################
#   Cloud Functions 互換のAPI群
##############################################################################
import cv2
import numpy as np
import requests
import json
import re
import uuid
import datetime
from datetime import datetime as dt
from typing import Any, Dict
from configparser import ConfigParser

# 独自モジュール読み込み
from api import common

# 定数定義
# 賞味期限フォーマットに従って分解したときの格納順序と格納先のキー名を表したリスト
EXPIRATION_DATE_KEYS = ["year" , "month", "day"]

# 設定ファイル読み込み
config = ConfigParser()
config.read("settings.conf", encoding="utf-8")

# 設定読み込み
# 賞味期限フォーマットパターン
DATE_FORMAT_PATTERNS = json.loads(config.get("format", "date_format_patterns"))
# 現在の日付よりも古い期限を許可する日数差分
OLD_LIMIT_DAYS = int(config.get("limit", "old_limit_days"))
# 現在の日付よりも新しい期限を許可する日数差分
NEW_LIMIT_DAYS = int(config.get("limit", "new_limit_days"))
# APIキー
API_KEY = config.get("gcp", "api_key")
VISION_API_URL = f"https://vision.googleapis.com/v1/images:annotate?key={API_KEY}"

def health(request) -> str:
    """ヘルスチェック用関数

    Args:
        request: GET リクエスト

    Returns:
        str: OK
    """
    return "OK"

def detect(request) -> Dict[str, Any]:
    """JPEG形式の画像を整数の配列で表したデータをもとに Google Cloud Vision API に投げて結果を返します。

    Args:
        request: POST リクエスト

    Returns:
        Dict[str, Any]: Google Cloud Vision API から得られた結果
    """
    # リクエストパラメーター取り出し
    image_string = json.dumps(request.json["image"], separators=(",", ":")).strip("[]")
    image_bytearray = np.fromstring(image_string, np.uint8, sep=",")
    image_2d_3ch = cv2.imdecode(image_bytearray, cv2.IMREAD_COLOR)

    # 画像ファイル書き出し
    cv2.imwrite("./target.jpg", image_2d_3ch)

    # Vision API に投げて結果を得る
    image_base64 = common.image_to_base64(image_2d_3ch)
    response = requests.post(VISION_API_URL, data=json.dumps({
        "requests": [
            {
                "image": {
                    "content": image_base64
                },
                "features": [
                    {
                        "type": "TEXT_DETECTION"
                    }
                ],
                "imageContext": {
                    "languageHints": ["en"]
                }
            }
        ]
    }))
    response_json = response.json()
    response_str = json.dumps(response_json, ensure_ascii=False, indent=4)
    print(response_str)

    # レスポンスをファイルに書き出し
    with open("./response.json", "w") as w:
        w.write(json.dumps(response_json, ensure_ascii=False, indent=4))

    # レスポンスのうち全文テキストの半角スペースをすべて除去した上で抜き出す
    found_text = response_json \
        .get("responses", [{}])[0] \
        .get("textAnnotations", [{}])[0] \
        .get("description", "") \
        .replace(" ", "") \
        .replace("\r", " ") \
        .replace("\n", " ")
    print(f"found_test: {found_text}")

    if found_text == "":
        return {
            "success": False,
            "result": None
        }

    # 賞味期限っぽい部分を抜き出す
    expiration_date = None
    for date_format_pattern in DATE_FORMAT_PATTERNS:
        # 正規表現で表されるパターンで抜き出す
        print(date_format_pattern)
        result = re.match(date_format_pattern, found_text)
        if not result:
            print("Expiration Date is not found.")
            continue

        # 年月日に分解し、日が省略されている場合は None として埋める
        date_parts = list(result.groups())
        try:
            expiration_date = {
                key: int(date_parts[index]) if index < len(date_parts) else None
                for index, key in enumerate(EXPIRATION_DATE_KEYS)
            }
        except ValueError:
            # 整数に変換できない値を拾ってしまった場合はやり直し
            print("Cannot parseInt Expiration Date.")
            expiration_date = None
            continue

        if expiration_date["year"] < 100:
            # 年を4桁表記に直す
            upper = int(dt.now().year / 100)
            lower = dt.now().year % 100
            if expiration_date["year"] < lower:
                # Y2K問題対策: 年の下二桁が現在よりも小さいときは上二桁に繰り上がりが起きている
                upper += 1
            expiration_date["year"] = f"{upper:02}{expiration_date['year']:02}"

        # 存在する年月日かどうか検証
        print(expiration_date)
        try:
            if expiration_date["day"] is None:
                date = dt.strptime(f"{expiration_date['year']}-{expiration_date['month']:02}", "%Y-%m")

                # 翌月の初日から差し引いて月末の日にちを割り出す
                temp_year = expiration_date["year"]
                temp_month = expiration_date["month"] + 1
                if temp_month > 12:
                    temp_year += 1
                    temp_month %= 12
                next_month_date = dt.strptime(f"{temp_year}-{temp_month:02}", "%Y-%m")
                expiration_date["day"] = (next_month_date - date).days
                print(expiration_date)
            else:
                date = dt.strptime(f"{expiration_date['year']}-{expiration_date['month']:02}-{expiration_date['day']:02}", "%Y-%m-%d")
        except ValueError:
            # 無効な日付を読み取ってしまった場合はやり直し
            print("Expiration Date is Invalid.")
            expiration_date = None
            continue

        # 現在の日付を起点に見て古すぎないか検証
        now = dt.now()
        if date < now and (now - date).days > OLD_LIMIT_DAYS:
            print(f"Expiration Date is too old.")
            expiration_date = None
            continue

        # 現在の日付を起点に見て未来すぎないか検証
        if now <= date and (date - now).days > NEW_LIMIT_DAYS:
            print("Expiration Date is too future.")
            expiration_date = None
            continue

        session_id = str(uuid.uuid4()).replace("-", "")
        break

    # TODO: 仮登録テーブルにセッションIDと賞味期限のペアを格納する

    return {
        "success": expiration_date is not None,
        "expiration_date": expiration_date if expiration_date is not None else None,
        "session_id": session_id if expiration_date is not None else None
    }

def register(request) -> Dict[str, Any]:
    """JPEG形式の画像を整数の配列で表したデータとセッションIDを紐づけて本登録を行います。

    Args:
        request: POST リクエスト

    Returns:
        Dict[str, Any]: 処理結果
    """
    # TODO: 本登録テーブルにセッションIDと賞味期限のペアを移動させる (仮登録テーブルの該当セッションIDは削除)
    # TODO: セッションIDのファイル名でサーバーに商品画像を保管する
    pass
