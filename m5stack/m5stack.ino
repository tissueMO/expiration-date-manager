#include <M5Stack.h>
#include <WiFi.h>
#include <HTTPClient.h>

// スピーカー設定
#define SPEAKER_PIN 25

// Wi-Fi 接続、通信設定
#include "settings.h"
#define TIMEOUT_MS 10000

// 受け取る画像の仕様とバッファーを確保
const int x = 160;
const int y = 120;
const int jpegWidth = x * 2;
const int jpegHeight = y * 2;
uint8_t imageBuffer8bits[x * y * 2];
uint16_t imageBuffer16bits[x * y];
int imageBufferLength = -1;
const int jpegHeaderPacketLength = 10;
static const uint8_t jpegHeaderFixedPackets[3] = {0xFF, 0xD8, 0xEA};
static String currentSessionID = "";

void setup() {
  M5.begin();
  Serial.begin(115200);

  // M5Stack Groveポート
  Serial2.begin(1152000, SERIAL_8N1, 21, 22);
  Serial2.setTimeout(1000);

  // Wi-Fi 接続
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(SSID);
  WiFi.begin(SSID, PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    // 接続待ち
    delay(500);
    Serial.print(".");
  }

  // 接続成功後
  Serial.println("");
  Serial.println("Wi-Fi connected.");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());

  // カメラからの受信を開始する
  Serial2.println("resume");
}

void beep(int freq, int duration, uint8_t volume) {
  // freq(Hz), duration(ms), volume(1-255)
  int t = 1000000 / freq / 2;
  unsigned long start = millis();

  while ((millis() - start) < duration) {
    dacWrite(SPEAKER_PIN, 0);
    delayMicroseconds(t);
    dacWrite(SPEAKER_PIN, volume);
    delayMicroseconds(t);
  }

  dacWrite(SPEAKER_PIN, 0);
}

void beepOK() {
  beep(2000, 100, 5);
}

void beepFailure() {
  beep(2000, 100, 5);
  delay(100);
  beep(2000, 100, 5);
}

void beepFatal() {
  beep(1000, 500, 5);
  delay(200);
  beep(1000, 100, 5);
  delay(100);
  beep(1000, 100, 5);
}

void loop() {
  if (Serial2.available()) {
    // カメラから画像が送られてきたらLCDに表示する
    int bitmapLength = Serial2.readBytes(imageBuffer8bits, x * y * 2);
    Serial.println(String("Received Bitmap: ") + bitmapLength + " bytes");
    if (bitmapLength == x * y * 2) {
      // ビットマップ画像を受け取ってLCDに描画
      for (int i = 0; i < x * y; i++) {
        imageBuffer16bits[i] = (imageBuffer8bits[2 * i] << 8) + imageBuffer8bits[2 * i + 1];
      }
      M5.Lcd.drawBitmap(80, 60, x, y, imageBuffer16bits);
    } else {
      Serial.println("Warning: Bitmap Data is bad.");
    }

    // JPEG画像を受け取ってサーバーへの送信に備える
    uint8_t buf[jpegHeaderPacketLength];
    int receivedLength = Serial2.readBytes(buf, jpegHeaderPacketLength);
    Serial.println(String("JPEG Header Packets: ") + receivedLength + " bytes");
    if (receivedLength == jpegHeaderPacketLength) {
      // JPEG画像の直前に来るヘッダーパケットを確認
      Serial.print(buf[0]);
      Serial.print(", ");
      Serial.print(buf[1]);
      Serial.print(", ");
      Serial.println(buf[2]);

      if ((buf[0] == jpegHeaderFixedPackets[0])
          && (buf[1] == jpegHeaderFixedPackets[1])
          && (buf[2] == jpegHeaderFixedPackets[2])) {
        imageBufferLength = (uint32_t)(buf[4] << 16) | (buf[5] << 8) | buf[6];
        Serial.println(String("JPEG Data Length: ") + imageBufferLength + " bytes");
        Serial2.readBytes(imageBuffer8bits, imageBufferLength);
        if (imageBufferLength > x * y) {
          Serial.println("Warning: Received JPEG Image is too large.");
        }
      } else {
        Serial.println("Warning: JPEG Header Packets is bad.");
      }
    }
  }

  // ボタン押下状態更新
  M5.update();

  if (M5.BtnA.wasReleased()) {
    // カメラからの受信を一時停止する
    Serial2.println("pause");

    // 保持しているセッションIDをクリアする
    Serial.println("Pressed A (SessionID Clear) Button.");
    currentSessionID = "";
    beepOK();

    // カメラからの受信を再開する
    Serial2.println("resume");
  }

  if (M5.BtnB.wasReleased()) {
    // カメラからの受信を一時停止する
    Serial2.println("pause");

    // 最新の画像を商品イメージとしてサーバーに送る
    Serial.println("Pressed B (Sending Product Image) Button.");
    beepOK();

    // サーバーに接続
    Serial.println("Connecting to Server...");
    HTTPClient httpClient;
    if (!httpClient.begin(HOSTNAME, PORT, "/register")) {
      // HTTPコネクションの確立に失敗
      Serial.println("Connection Failed.");
      beepFatal();
    } else {
      // POSTリクエストを生成
      Serial.println("Connected.");
      httpClient.addHeader("Content-Type", "application/json");

      // リクエストボディを生成
      Serial.println("Buffering...");
      String requestPayload = String("{\"session_id\":\"") + currentSessionID + "\",\"image\":[";
      for (int i = 0; i < imageBufferLength; i++) {
        requestPayload += String(imageBuffer8bits[i]);
        if (i + 1 < imageBufferLength) {
          requestPayload += String(",");
        }
      }
      requestPayload += String("]}");
      Serial.println(String("Buffer Length: ") + requestPayload.length());

      // POSTリクエストを送信
      int httpCode = httpClient.POST(requestPayload);

      // レスポンス受信
      Serial.print(String("Response: [") + httpCode + "]");
      if (httpCode == HTTP_CODE_OK) {
        String payload = httpClient.getString();
        Serial.println(payload);

        // レスポンスの中身を画面上に表示
        M5.Lcd.fillScreen(TFT_BLACK);
        M5.Lcd.setCursor(0, 0);
        M5.Lcd.println(payload);

        // レスポンスの中身を取り出す
        bool success = (payload.indexOf("\"success\":true") != -1);
        if (success) {
          // 商品情報の確定に成功
          beepOK();
          // セッションIDをクリア
          currentSessionID = "";
        } else {
          // 商品情報の確定に失敗
          beepFailure();
        }
      }
      httpClient.end();
    }

    // カメラからの受信を再開する
    Serial2.println("resume");
  }

  if (M5.BtnC.wasReleased()) {
    // カメラからの受信を一時停止する
    Serial2.println("pause");

    // ボタン押下時点のカメラ画像をサーバーに送る
    Serial.println("Pressed C (Sending ExpirationDate Image) Button.");
    beepOK();

    // サーバーに接続
    Serial.println("Connecting to Server...");
    HTTPClient httpClient;
    if (!httpClient.begin(HOSTNAME, PORT, "/detect")) {
      // HTTPコネクションの確立に失敗
      Serial.println("Connection Failed.");
      beepFatal();
    } else {
      // POSTリクエストを生成
      Serial.println("Connected.");
      httpClient.addHeader("Content-Type", "application/json");

      // リクエストボディを生成
      Serial.println("Buffering...");
      String requestPayload = String("{\"image\":[");
      for (int i = 0; i < imageBufferLength; i++) {
        requestPayload += String(imageBuffer8bits[i]);
        if (i + 1 < imageBufferLength) {
          requestPayload += String(",");
        }
      }
      requestPayload += String("]}");
      Serial.println(String("Buffer Length: ") + requestPayload.length());

      // POSTリクエストを送信
      int httpCode = httpClient.POST(requestPayload);

      // レスポンス受信
      Serial.println(String("Response: [") + httpCode + "]");
      if (httpCode == HTTP_CODE_OK) {
        String payload = httpClient.getString();
        Serial.println(payload);

        // レスポンスの中身を画面上に表示
        M5.Lcd.fillScreen(TFT_BLACK);
        M5.Lcd.setCursor(0, 0);
        M5.Lcd.println(payload);

        // レスポンスの中身を取り出す
        bool success = (payload.indexOf("\"success\":true") != -1);
        if (success) {
          // セッションIDを保存
          String keyword = "\"session_id\":\"";
          int startIndex = payload.indexOf(keyword) + keyword.length();
          currentSessionID = payload.substring(startIndex, startIndex + 32);
          M5.Lcd.println(String("SessionID: ") + currentSessionID);

          // 賞味期限の読み取りに成功
          beepOK();
        } else {
          // 賞味期限の読み取りに失敗
          beepFailure();
        }
      }
      httpClient.end();
    }

    // カメラからの受信を再開する
    Serial2.println("resume");
  }
}
