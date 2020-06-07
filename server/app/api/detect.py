##############################################################################
#    画像から賞味期限を読み取って仮登録を行うAPI
##############################################################################
import cv2
import numpy as np
import requests
import json
import re
import uuid
import datetime
from datetime import datetime as dt
from typing import Any, Dict, List
from configparser import ConfigParser

# 独自モジュール読み込み
import app.common as common
from model.temporary_products import TemporaryProduct
logger = common.get_logger("detect")

# 設定ファイル読み込み
config = ConfigParser()
config.read("settings.conf", encoding="utf-8")

##### 設定読み込み ####################
# 賞味期限フォーマットパターン
DATE_FORMAT_PATTERNS = json.loads(config.get("detect", "date_format_patterns"))
# 現在の日付よりも古い期限を許可する日数差分
OLD_LIMIT_DAYS = int(config.get("detect", "old_limit_days"))
# 現在の日付よりも新しい期限を許可する日数差分
NEW_LIMIT_DAYS = int(config.get("detect", "new_limit_days"))
# OCRに使用するAPIキー
API_KEY = config.get("detect", "api_key")

##### 定数定義 ####################
# 賞味期限フォーマットに従って分解したときの格納順序と格納先のキー名を表したリスト
EXPIRATION_DATE_KEYS = ["year" , "month", "day"]
# OCRに使用するAPIのURL
OCR_API_URL = f"https://vision.googleapis.com/v1/images:annotate?key={API_KEY}"


def execute(request) -> Dict[str, Any]:
    """JPEG形式の画像を整数の配列で表したデータをもとに賞味期限を抽出し、仮登録テーブルに保存します。

    Arguments:
        request -- POST リクエスト
            {
                // JPEG圧縮した画像を uint8 配列で並べたデータ
                "image": [uint8, uint8, ...]
            }

    Returns:
        Dict[str, Any] -- 処理結果
            {
                // 解析に成功したかどうか
                "success": False or True,

                // 賞味期限として抽出された年月日
                "expiration_date": { "year": yyyy, "month": mm, "day": dd },

                // 仮登録テーブルに紐づけられたセッションID
                "session_id": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",

                // 解析に失敗した原因を表すメッセージ
                "message": "..."
            }
    """
    logger.info(f"API Called.")

    # リクエストパラメーター取り出し
    image = common.convert_request_image_to_ndarray(request.json["image"])

    # [デバッグ用] リクエスト画像をファイルに書き出し
    # cv2.imwrite("./target.jpg", image)

    # 画像からテキストを解析
    response_json = _call_ocr(image)

    # [デバッグ用] 解析結果をファイルに書き出し
    # with open("./response.json", "w") as w:
    #     w.write(json.dumps(response_json, ensure_ascii=False, indent=4))

    # OCRによって得られた文字列を取り出す
    found_text = _extract_text_from_ocr_result(response_json)
    logger.debug(f"OCRから得られたテキスト: [{found_text}]")
    if found_text == "":
        response = {
            "success": False,
            "expiration_date": None,
            "session_id": None,
            "message": f"画像内にテキストが含まれていませんでした",
        }
        logger.info(f"API Exit: {response}")
        return response

    # 得られた文字列から賞味期限に相当する箇所を解析
    expiration_date = _find_expiration_date(found_text)
    is_success = expiration_date is not None
    session_id = None
    message = None

    if is_success:
        # 仮登録テーブルにセッションIDと賞味期限のペアを格納
        session_id = str(uuid.uuid4()).replace("-", "")

        with common.create_session() as session:
            session.add(TemporaryProduct(
                session_id=session_id,
                expiration_date=dt.strptime(f"{expiration_date['year']}-{expiration_date['month']:02}-{expiration_date['day']:02}", "%Y-%m-%d"),
                created_time=dt.now()
            ))
            session.commit()
        message = "賞味期限の取り出しに成功しました"
    else:
        message = "OCRによって得られたテキストから賞味期限を抽出できませんでした"

    response = {
        "success": is_success,
        "expiration_date": expiration_date,
        "session_id": session_id,
        "message": None if is_success else message,
    }
    logger.info(f"API Exit: {response}")
    return response


def _call_ocr(image: np.ndarray) -> Dict[str, Any]:
    """OCRエンジン (Google Cloud Vision API) に投げて結果を辞書にして返します。

    Arguments:
        image {np.ndarray} -- 解析対象の画像

    Returns:
        Dict[str, Any] -- Google Cloud Vision API の読み取り結果
    """
    image_base64 = common.image_to_base64(image)

    response = requests.post(
        OCR_API_URL,
        data=json.dumps({
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
        })
    )

    response_json = response.json()

    response_str = json.dumps(response_json, ensure_ascii=False, indent=4)
    logger.debug(f"Vision API のレスポンス: {response_str}")

    return response_json


def _extract_text_from_ocr_result(response_json: Dict[str, Any]) -> str:
    """OCRエンジンから得られたデータのうち、テキストのみを抽出します。

    Arguments:
        response_json {Dict[str, Any]} -- OCRエンジンから得られたデータ

    Returns:
        str -- 読み取った文字列
    """
    return response_json \
        .get("responses", [{}])[0] \
        .get("textAnnotations", [{}])[0] \
        .get("description", "") \
        .replace(" ", "") \
        .replace("\r", " ") \
        .replace("\n", " ")


def _find_expiration_date(found_text: str) -> Dict[str, int]:
    """与えられたテキストから賞味期限に相当する年月日を抽出します。

    Arguments:
        found_text {str} -- 抽出対象のテキスト

    Returns:
        Dict[str, int] -- {"year": yyyy, "month": mm, "day": dd}
    """
    expiration_date = None

    for date_format_pattern in DATE_FORMAT_PATTERNS:
        # 正規表現で表されるパターンで抜き出す
        logger.debug(f"正規表現パターン: {date_format_pattern}")
        result = re.match(date_format_pattern, found_text)
        if not result:
            logger.debug(f"現在の判定パターンでは賞味期限を抽出できませんでした: {date_format_pattern}")
            continue

        # 年月日に分解し、日が省略されている場合は None として埋める
        date_parts = list(result.groups())
        try:
            expiration_date = {
                key: int(date_parts[index]) if index < len(date_parts) else None
                for index, key in enumerate(EXPIRATION_DATE_KEYS)
            }
        except ValueError:
            logger.debug(f"年月日のいずれかに整数ではない文字が含まれているため無効とみなします: {date_parts}")
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
            logger.debug(f"年を4桁表記に補完: {expiration_date['year']}")

        # 存在する年月日かどうか検証
        try:
            if expiration_date["day"] is None:
                logger.debug(f"抽出した年月: {expiration_date}")
                date = dt.strptime(f"{expiration_date['year']}-{expiration_date['month']:02}", "%Y-%m")

                # 翌月の初日から差し引いて月末の日にちを割り出す
                temp_year = expiration_date["year"]
                temp_month = expiration_date["month"] + 1
                if temp_month > 12:
                    temp_year += 1
                    temp_month %= 12
                next_month_date = dt.strptime(f"{temp_year}-{temp_month:02}", "%Y-%m")
                expiration_date["day"] = (next_month_date - date).days
                logger.debug(f"省略表記されていた日を月末の日付で補完します: {expiration_date}")
            else:
                logger.debug(f"抽出した年月日: {expiration_date}")
                date = dt.strptime(f"{expiration_date['year']}-{expiration_date['month']:02}-{expiration_date['day']:02}", "%Y-%m-%d")
        except ValueError:
            # 無効な日付を読み取ってしまった場合はやり直し
            logger.debug(f"存在しない日付を抽出したため無効とみなします: {expiration_date}")
            expiration_date = None
            continue

        # 現在の日付を起点に見て古すぎないか検証
        now = dt.now()
        if date < now and (now - date).days > OLD_LIMIT_DAYS:
            logger.debug(f"抽出した日付が設定下限値よりも古いため無効とみなします: {expiration_date}")
            expiration_date = None
            continue

        # 現在の日付を起点に見て未来すぎないか検証
        if now <= date and (date - now).days > NEW_LIMIT_DAYS:
            logger.debug(f"抽出した日付が設定上限値よりも未来の日付であるため無効とみなします: {expiration_date}")
            expiration_date = None
            continue

        logger.debug(f"賞味期限の抽出に成功しました: {expiration_date}")
        return expiration_date

    logger.debug(f"賞味期限を抽出できませんでした")
    return None
