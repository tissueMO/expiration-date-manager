###############################################################################
#    汎用処理群
###############################################################################
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm.session import Session
from sqlalchemy.pool import SingletonThreadPool
from typing import Any, Dict, List
import sys
import cv2
import numpy as np
import base64
import json
import urllib.parse
sys.path.insert(0, ".")

### ロギング設定ロード
import logging
from logging import config
config.fileConfig("./logging.ini")

### 設定値ロード
import configparser
config = configparser.ConfigParser()
config.read("./alembic.ini", "UTF-8")

# DB接続文字列
DB_PATH = config.get("alembic", "sqlalchemy.url")
print(DB_PATH)


class SessionFactory(object):
    """DB接続セッションを生成するファクトリークラスです。
    """

    def __init__(self, echo=False):
        self.engine = create_engine(DB_PATH, echo=echo, poolclass=SingletonThreadPool)

    def create(self) -> Session:
        Session = sessionmaker(bind=self.engine, autocommit=False)
        return Session()


class SessionContext(object):
    """with構文 に対応させたDB接続セッション管理クラスです。
    """

    def __init__(self, session):
        self.session = session

    def __enter__(self) -> Session:
        return self.session

    def __exit__(self, exc_type, exc_value, traceback):
        # with構文 を抜けるタイミングで自動的にコミット&クローズ
        self.session.flush()
        self.session.commit()
        self.session.close()


class SessionContextFactory(object):
    """with構文 に対応したDB接続セッションを生成するファクトリークラスです。
    """

    def __init__(self, echo=False):
        self.session_factory = SessionFactory(echo=echo)

    def create(self) -> SessionContext:
        return SessionContext(self.session_factory.create())


def create_session() -> SessionContext:
    """DB接続セッションを作成します。
    この関数の戻り値を受け取る呼出元変数は with構文 を用いて自動クローズの対象とすることを推奨します。

    Returns:
        Session -- DB接続セッション
    """
    return SessionContextFactory(echo=True).create()


def get_logger(name: str) -> logging.Logger:
    """指定したモジュール名でロガーオブジェクトを生成します。

    Arguments:
        name {str} -- モジュール名

    Returns:
        Logger -- ロガーオブジェクト
    """
    return logging.getLogger(name)


def convert_request_image_to_ndarray(request_image: List[int]) -> np.ndarray:
    """M5Stackからのリクエスト形式で表される画像データをOpenCVで扱える形式に変換します。

    Arguments:
        request_image {List[int]} -- M5Stackからのリクエスト形式で表される画像データ

    Returns:
        np.ndarray -- OpenCVで扱える形式の画像
    """
    image_string = json.dumps(request_image, separators=(",", ":")).strip("[]")
    image_bytearray = np.fromstring(image_string, np.uint8, sep=",")
    image = cv2.imdecode(image_bytearray, cv2.IMREAD_COLOR)
    return image


def image_to_base64(numpy_image: np.ndarray) -> str:
    """NumPy配列をBase64形式の画像にエンコードします。

    Arguments:
        numpy_image {np.ndarray} -- NumPy配列の画像

    Returns:
        str -- Base64形式の画像
    """
    _, data = cv2.imencode(".jpg", numpy_image)
    base64_image = base64.b64encode(data).decode(encoding="utf-8")
    return base64_image


def decode_request_payload(request) -> Dict[str, Any]:
    """URLエンコードされた形式のリクエストボディをデコードして辞書型に変換します。

    Arguments:
        request -- POST リクエスト

    Returns:
        Dict[str, Any] -- デコード済みのリクエストボディ
    """
    payload = request.get_data().decode("utf-8")
    payload = payload[len("payload="):]
    payload = urllib.parse.unquote(payload)
    return payload
