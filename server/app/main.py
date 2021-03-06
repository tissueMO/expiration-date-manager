###############################################################################
#    WSGI Webアプリケーションを定義します。
#    このスクリプトを単体で起動した場合は Flask 内蔵サーバーで立ち上がります。
###############################################################################
from flask import Flask, jsonify, request
from flask_cors import CORS
import sys
sys.path.insert(0, ".")

app = Flask(__name__)
CORS(app)
app.config["JSON_AS_ASCII"] = False

# 定数定義
FLASK_SERVER_PORT = 80
DEBUGGER_PORT = 5000


@app.route("/detect", methods=["POST"])
def detect():
    """与えられた画像から賞味期限を読み取ります。
    """
    from app.api import detect
    return jsonify(detect.execute(request))


@app.route("/register", methods=["POST"])
def register():
    """与えられた画像とセッションIDを紐づけて本登録を行います。
    """
    from app.api import register
    return jsonify(register.execute(request))


@app.route("/cancel", methods=["POST"])
def cancel():
    """与えられたセッションIDを持つ仮登録情報をキャンセルします。
    """
    from app.api import cancel
    return jsonify(cancel.execute(request))


@app.route("/command", methods=["POST"])
def command():
    """本登録済みの商品に対して任意のアクションを行います。
    """
    from app.api import command
    return jsonify(command.execute(request))


@app.route("/listup", methods=["POST"])
def listup():
    """本登録済みの商品イメージを非同期的にSlackへ通知します。
    """
    from app.api import listup
    return jsonify(listup.execute(request))


@app.route("/listup/async", methods=["POST"])
def listup_async():
    """与えられた本登録済みの商品イメージをすべてSlackへ通知します。
    """
    from app.api import listup_async
    return jsonify(listup_async.execute(request))


@app.route("/images/<string:file_name>")
def get_image(file_name):
    """[バイナリー返却] 本登録済みのイメージ画像を取得します。
    """
    from app.api import image
    return image.execute(file_name)


@app.route("/remind")
def remind():
    """n日後に期限が迫っているものがあればSlackへ通知します。
    """
    from app.api import remind
    return jsonify(remind.execute(request))


@app.route("/cleanup")
def cleanup():
    """古くなった過去データをクリーンアップします。
    """
    from app.api import cleanup
    return jsonify(cleanup.execute(request))


@app.route("/health")
def health():
    """ステータスコード 200 を返してシステムが正常な状態であることを表します。
    """
    return jsonify({})


if __name__ == "__main__":
    import os
    import ptvsd
    import app.log as log

    logger = log.get_logger("Entrypoint")

    # リモートデバッグを有効にする
    logger.info("Waiting for remote debugging...")
    ptvsd.enable_attach(address=("0.0.0.0", DEBUGGER_PORT))

    # 単体起動した場合は Flask 内蔵サーバーを立ち上げる
    app.run(host="0.0.0.0", port=FLASK_SERVER_PORT)
