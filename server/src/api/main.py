##############################################################################
#   Cloud Functions 互換のAPI群
##############################################################################
import cv2
import numpy as np
import requests
import json
from typing import Any, Dict
from configparser import ConfigParser

# 独自モジュール読み込み
from api import common

# 設定ファイル読み込み
config = ConfigParser()
config.read("settings.conf", encoding="utf-8")

# 設定読み込み
# APIキー
API_KEY = config.get("gcp", "api_key")
VISION_API_URL = f"https://vision.googleapis.com/v1/images:annotate?key={API_KEY}";

def health(request) -> str:
    """ヘルスチェック用関数

    Args:
        request: GET リクエスト

    Returns:
        str: OK
    """
    return "OK"

def detect(request) -> Dict[str, Any]:
    """RGB565形式で送られてきた画像を Google Cloud Vision API に投げて結果を返します。

    Args:
        request: POST リクエスト

    Returns:
        Dict[str, Any]: Google Cloud Vision API から得られた結果
    """
    # リクエストパラメーター取り出し
    width = request.json["width"]
    height = request.json["height"]
    image_1d = request.json["image"]
    CHANNEL_LENGTH = 3

    # R, G, B の順で分解
    image_1d_3ch = [
      [
        [(rgb565 & 0x1f)],
        [(rgb565 >> 5) & 0x3f],
        [(rgb565 >> 11) & 0x1f]
      ] for rgb565 in image_1d
    ]

    # R, G, B をそれぞれ正規化
    image_1d_3ch_normalized = [
      [
        [(rgb888[0][0] << 3) | (rgb888[0][0] >> 2)],
        [(rgb888[1][0] << 2) | (rgb888[1][0] >> 4)],
        [(rgb888[2][0] << 3) | (rgb888[2][0] >> 2)]
      ] for rgb888 in image_1d_3ch
    ]
    image_1d_3ch_normalized = np.array(image_1d_3ch)

    # 縦横で軸を分離する
    image_2d_3ch = image_1d_3ch_normalized.reshape(height, width, CHANNEL_LENGTH)

    # 画像ファイル書き出し
    cv2.imwrite("./target.bmp", image_2d_3ch)

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
                ]
            }
        ]
    }))
    response_str = json.dumps(response.json(), ensure_ascii=False, indent=4)
    print(response_str)

    # レスポンスをファイルに書き出し
    with open("./response.json", "w") as w:
        w.write(json.dumps(response.json(), ensure_ascii=False, indent=4))

    return "Detected OK."
