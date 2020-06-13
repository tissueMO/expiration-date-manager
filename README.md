賞味期限管理ソリューション
====

## Summary

食料品の賞味期限・消費期限を管理するソリューションです。  
期限の読み取りにOCRを利用しているため、写真を撮影するだけで手入力が一切不要なのが特徴です。  
期限日が迫ってきた際にSlackで通知するための機能や、再購入できるように買い物リスト用のチャンネルに投稿する機能も実装しています。  

![03_PassThrough](https://user-images.githubusercontent.com/20965271/84577266-d62baa00-adf5-11ea-863c-892e7f101203.gif)


## Description

### アーキテクチャー全体図

![Architecture](https://github.com/tissueMO/expiration-date-manager/blob/master/_figures/architecture.drawio.svg)


#### カメラ部 [UnitV AI Camera]

食料品イメージと賞味期限の撮影を担います。  
作者は UnitV AI Camera を使用していますが、シリアル通信が可能でK210互換の機器であれば使用可能です。  
UnitV AI Camera を使用する場合は MaixPy IDE を用いてソースコードを書き込みます。  

UnitV AI Camera の場合、Wi-Fiモジュールを搭載していないためサーバーへの送信のため一旦撮影データを
Wi-Fi対応機器に転送するようにしています。  


#### プレビュー部 [M5Stack]

カメラ部から受信した画像をリアルタイムでLCDに映しながらプレビューを行い、サーバー部に転送する中継役を担います。  
各種操作には、M5Stack に標準搭載されている3つのボタンから行います。  

M5Stack へは Arduino IDE を用いてソースコードをコンパイルして書き込みます。  


#### サーバー部 [Server]

受信した画像をOCR (Google Cloud Vision API) にかけて賞味期限を読み取ります。  
さらに、賞味期限を正しく読み取れていれば食料品イメージ画像と合わせて永続化します。  

このサーバーアプリケーションには Apache2 + mod_wsgi および Python の Flask が使われています。  
`/server/Dockerfile` を用いてコンテナーイメージをビルドし、Dockerコンテナー上で動かします。  
また、データの永続化には SQLite3 とファイルストレージを使用するため、適宜ホスト環境とのボリュームマウントが必要となります。  


#### メッセージング部 [Slack]

通知や任意のコマンドを実行します。  
登録した食料品の確認や期限が迫っている食料品に対する更新アクションはここから行います。  

予め稼働させるワークスペースに自作したアプリとしてインストールしておく必要があります。


### ユースケース

- 食料品の賞味期限・消費期限を撮影して日付を読み取る
- (読み取った日付が正しい場合) 食料品のイメージを撮影して登録する
- (登録した食料品の期限日が迫っている場合) Slackに通知が来る
- Slackの通知メッセージに付随するコマンドを実行する (消費済み/買い物リストに追加/無視)


## Dependency

#### カメラ部 [UnitV AI Camera]

- MaixPy IDE
- K210


#### プレビュー部 [M5Stack]

- Arduino IDE
- ESP32
- ESP8266
- Arduino_JSON


#### サーバー部 [Server]

- Docker
- Python 3.7
    - Python パッケージ
        - Flask
        - alembic
        - SQLAlchemy
        - その他については `/server/requirements.txt` を参照
- Apache2
    - mod_wsgi 4.5
- Slack API


#### メッセージング部 [Slack]

- Slack


## Setup

本リポジトリーを Clone してから実際に動かすまでの手順を示します。


#### カメラ部 [UnitV AI Camera]

- UnitV AI Camera と M5Stack を Grove対応の4ピンケーブルで接続します。
- UnitV AI Camera の USB TypeC ポートを通して開発用PCに接続します。
- MaixPy IDE から `/unitv/camera.py` を開きます。
- UnitV AI Camera との接続設定を行い、プログラムを boot.py に書き込みます。


#### プレビュー部 [M5Stack]

- UnitV AI Camera と M5Stack を Grove対応の4ピンケーブルで接続します。
- M5Stack の USB TypeC ポートを通して開発用PCに接続します。
- Arduino IDE から `/m5stack/m5stack.ino` を開きます。
- `/m5stack/settings.example.h` をもとに適宜設定値を含めた `/m5stack/settings.h` を作成し、環境依存する値のマクロを定義します。
- コンパイル & M5Stack への書き込みを行います。


#### サーバー部 [Server]

- `/server/settings.sample.conf` をもとに適宜設定値を含めた `/server/settings.conf` を作成し、環境依存する値の設定を行います。
- コマンドライン上で `/server` 相当のディレクトリーに移動します。
- 以下のコマンドからDockerイメージのビルドを実行します。
    - `$ docker build -t {TAG_NAME} .`
    - ビルドに失敗した場合、適宜Dockerfileを修正して下さい。
- 以下のコマンドで SQLite3 の初回マイグレーションを実行します。
    - `$ docker run --rm -v {HOST_DIRECTORY_PATH}:/var/www/apache-flask/db -it {TAG_NAME} alembic upgrade head`
- 以下のコマンドでサーバーを起動します。
    - `$ docker run --rm -e TZ=Asia/Tokyo -p 3000:80 -v {HOST_DIRECTORY_PATH}:/var/www/apache-flask/db -itd {TAG_NAME}`
- 必要に応じて cron 実行する設定をホスト環境上に追加します。
    - 例1. 期限3日前にSlack通知する
        - `0 0 * * * root curl -cL http://localhost:3000/remind?days=3`
    - 例2. 期限当日にSlack通知する
        - `0 0 * * * root curl -cL http://localhost:3000/remind?days=0`
    - 例3. 日次で古いデータを削除する
        - `0 18 * * * root curl -cL http://localhost:3000/cleanup`
- Flaskの内蔵サーバーを起動してVSCodeからリモートデバッグを行うには、以下のコマンドを実行します。
    - `$ docker run --rm -e TZ=Asia/Tokyo -p 3000:80 -p 5000:5000 -v {HOST_DIRECTORY_PATH}:/var/www/apache-flask/db -it {TAG_NAME} python app/main.py`
    - ポート番号は5000番、接続先はDockerホスト、リモートrootは `/var/www/apache-flask/app` と指定することでアタッチできます。


#### メッセージング部 [Slack]

- [Slack API](https://api.slack.com/) にてアプリケーションを作成します。
- Incoming Webhooks をアクティベートして Webhook URL を追加します。
    - ここで追加したURLはサーバー部の設定ファイルに必要となります。
- Interactivity をアクティベートして Request URL にサーバーAPI `/command` へのURLを設定します。
    - 外部からアクセス可能なURLとして公開しておく必要があります。
- Slash Commands に任意の名前でコマンドを追加 (例: `/listupfoods`) して Request URL にサーバーAPI `/listup` へのURLを設定します。
    - 外部からアクセス可能なURLとして公開しておく必要があります。
- OAuth & Permissions にて必要な情報を取得・設定します。
    - Bot User OAuth Access Token に記載されている文字列はサーバー部の設定ファイルに必要となります。
    - 以下の Bot Token Scopes を追加します。
        - chat:write
        - files:write
        - incoming-webhook
        - commands
    - 以下の User Token Scopes を追加します。
        - chat:write
        - files:write
    - Reinstall App を実行します。


## Usage

#### カメラ部 [UnitV AI Camera]

(Setup/カメラ部 [UnitV AI Camera] での工程が完了している前提とします)

- UnitV AI Camera と M5Stack を Grove対応の4ピンケーブルで接続します。
- M5Stack の電源を入れると UnitV AI Camera も通電されます。
- 取り込みたい食料品の賞味期限・消費期限、および食料品そのものをカメラで撮影します。(後述)

![01_Ready](https://user-images.githubusercontent.com/20965271/84576626-2fdda580-adf1-11ea-887f-e767cdf04f3f.jpg)


#### プレビュー部 [M5Stack]

(Setup/プレビュー部 [M5Stack] での工程が完了している前提とします)

- UnitV AI Camera と M5Stack を Grove対応の4ピンケーブルで接続します。
- M5Stack の USB TypeC ポートを通して電源と接続します。
- M5Stack を起動し、Wi-Fi への接続が完了するとカメラの画像がリアルタイムで表示されます。
- M5Stack の右ボタン (Detect) を押して、取り込みたい食料品の賞味期限・消費期限をカメラで撮影します。
    - 日付を読み取れた場合、LCD上にその日付が表示されます。
    - 日付を読み取れなかった場合もしくは読み取った日付に誤りがある場合、この操作をやり直す必要があります。
- 読み取った日付が正しければ、M5Stack の中央ボタン (Register) を押して、食料品そのものをカメラで撮影します。
    - 直前に読み取った日付と食料品のイメージ画像を合わせて登録します。
- 日付を読み取った直後にキャンセルして別の食料品を取り込みたい場合、M5Stack の左ボタン (Cancel) を押して直前に読み取ったデータを破棄することができます。

![02_Detected](https://user-images.githubusercontent.com/20965271/84576629-366c1d00-adf1-11ea-85d2-da857a26d20a.jpg)


#### サーバー部 [Server]

(Setup/サーバー部 [Server] での工程が完了している前提とします)

- サーバーに疎通できるクライアント環境のブラウザーから以下のURLにアクセスします。
    - `http://{DOMAIN_NAME}:3000/health`
        - これはヘルスチェック用のAPIです。
- 画面上に `{}` とだけ表示されれば正常に起動できています。

- サーバーログを確認するには、以下の手順でコマンドを実行します。
    - `$ docker ps`
        - 起動中のコンテナーの CONTAINER ID を確認します。
    - `$ docker logs {CONTAINER_ID}`


#### メッセージング部 [Slack]

(Setup/メッセージング部 [Slack] での工程が完了している前提とします)

- サーバー部のリマインドAPIによって通知用メッセージが送られると、期限日が近い(もしくは期限到来している)食料品に対して任意のアクションを実行できます。
    - 消費済み: 既に消費している場合は不要な通知であることが明らかになるため、以後通知対象とはみなされなくなります。
    - 買い物リストに追加: 買い物リスト用のチャンネルに食料品のイメージ画像が投稿された上で、以後通知対象とはみなされなくなります。
    - 無視: 特に登録データの更新を行わず、その後も通知対象とします。

![01_remind](https://user-images.githubusercontent.com/20965271/84576578-d4131c80-adf0-11ea-9c86-acbcf809d8ed.png)

![02_shoppinglist](https://user-images.githubusercontent.com/20965271/84576579-d6757680-adf0-11ea-9529-2fa2fff8b88d.png)

- アプリに登録したコマンド (例: `/listupfoods`) を実行すると、登録済みでまだ期限日が到来していないデータをリストアップできます。
    - コマンドの結果そのものは登録件数が表示されるのみですが、非同期的にすべての食料品のイメージ画像と期限日、登録日を含むメッセージが送られます。

![03_listupcommand](https://user-images.githubusercontent.com/20965271/84576580-d7a6a380-adf0-11ea-801c-1756206e1e52.png)

![04_listedup](https://user-images.githubusercontent.com/20965271/84576581-d7a6a380-adf0-11ea-9855-290c4cf6f932.png)


## References

- [tfuru/MaixPy](https://github.com/sipeed/MaixPy)
- [arduino-libraries/Arduino_JSON](https://github.com/arduino-libraries/Arduino_JSON)
- [UnitV で画像シリアル転送の味見 -エッジAI活用への道 12-](https://homemadegarbage.com/ai12)
- [Slack API](https://api.slack.com/)


## License

[MIT](LICENSE.md)


## Author

[tissueMO](https://github.com/tissueMO)
