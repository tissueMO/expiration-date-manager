##############################################################################
#   Dockerコンテナで動作するテスト用APIサーバー
##############################################################################
import os
import ptvsd
from flask import Flask, jsonify, request

if os.getenv("REMOTE_DEBUG") == "1":
    # リモートデバッグを有効にする
    ptvsd.enable_attach(address=("0.0.0.0", 5000))
    ptvsd.wait_for_attach()

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

# 自作API群ロード
from api import main

@app.route("/detect", methods=["POST"])
def detect():
    return jsonify(main.detect(request))

@app.route("/health")
def health():
    return jsonify(main.health(request))

if __name__ == "__main__":
    # テスト用サーバー起動
    app.run()
