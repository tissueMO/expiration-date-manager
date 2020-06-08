#include <M5Stack.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <Arduino_JSON.h>

// スピーカー設定
#define SPEAKER_PIN 25

// Wi-Fi 接続、通信設定
#include "settings.h"
#define TIMEOUT_MS 10000

// LCDに表示しているメッセージ
String lcdFixedMessage;
String lcdMessage;

// 受け取る画像の仕様とバッファーを確保
const int jpegWidth = 320;
const int jpegHeight = 240;
const int bmpWidth = jpegWidth / 2;
const int bmpHeight = jpegHeight / 2;
uint8_t imageBuffer8bits[bmpWidth * bmpHeight * 2];
uint16_t imageBuffer16bits[bmpWidth * bmpHeight];
int jpegImageSize = -1;
const int jpegHeaderPacketLength = 10;
static const uint8_t jpegHeaderFixedPackets[3] = {0xFF, 0xD8, 0xEA};

// 現在保持している仮登録セッションID
String currentSessionID = "";

// 最後に何かしらのボタンが押された時刻
unsigned long lastPressedButtonMS = -1;

// 何も操作しなかった時間が一定以上続いた際に電源を切るまでのミリ秒数
#define SHUTDOWN_MS 60000


void setup() {
  M5.begin();
  Serial.begin(115200);

  // M5Stack Groveポート
  Serial2.begin(1152000, SERIAL_8N1, 21, 22);
  Serial2.setTimeout(1000);

  // LCD初期設定
  M5.Lcd.clear(BLACK);
  M5.Lcd.setTextColor(WHITE);
  M5.Lcd.setTextSize(2);
  M5.Lcd.println("Connecting to Wi-Fi...");

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

  // カメラからの受信を明示的に停止～再開することで受信バッファーに無駄なデータが貯まるのを防ぐ
  delay(3000);
  Serial2.println("pause");
  delay(500);
  while (Serial2.available() > 0) {
    // 受信バッファーをすべてクリア
    Serial2.read();
  }
  delay(500);
  Serial2.println("resume");

  Serial.println("Startup Completed.");
  M5.Lcd.clear(BLACK);
  M5.Lcd.setCursor(0, 0);
  M5.Lcd.println("Receiving Camera Image...");

  lastPressedButtonMS = millis();
}

void _beep(int freq, int duration, uint8_t volume) {
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
  _beep(2000, 100, 5);
  delay(300);
}

void beepFailure() {
  _beep(2000, 100, 5);
  delay(100);
  _beep(2000, 100, 5);
  delay(300);
}

void beepFatal() {
  _beep(1000, 500, 5);
  delay(200);
  _beep(1000, 100, 5);
  delay(100);
  _beep(1000, 100, 5);
  delay(300);
}

void refreshLcdScreen(String message, bool drawCameraImage) {
  M5.Lcd.clear(BLACK);
  M5.Lcd.setCursor(0, 0);
  if (lcdFixedMessage.length() > 0) {
    M5.Lcd.println(lcdFixedMessage);
    M5.Lcd.println();
  }
  M5.Lcd.println(message);
  lcdMessage = message;

  if (drawCameraImage) {
    M5.Lcd.drawBitmap(320 / 2 / 2, 240 / 2 / 2 * 2 - 30, bmpWidth, bmpHeight, imageBuffer16bits);
  }

  // 画面下にボタンガイドを表示する
  M5.Lcd.drawLine(0, 220, 320, 220, WHITE);
  M5.Lcd.drawCentreString("Cancel", 53, 222, 1);
  M5.Lcd.drawLine(106, 220, 106, 240, WHITE);
  M5.Lcd.drawCentreString("Register", 161, 222, 1);
  M5.Lcd.drawLine(214, 220, 214, 240, WHITE);
  M5.Lcd.drawCentreString("Detect", 267, 222, 1);
}

void applyLcdFixedMessage(String message) {
  lcdFixedMessage = message;
  refreshLcdScreen(lcdMessage, true);
}

void refreshLcdImage() {
  refreshLcdScreen(lcdMessage, true);
}

void _receiveImageForLcd() {
  int bitmapLength = Serial2.readBytes(imageBuffer8bits, bmpWidth * bmpHeight * 2);
  Serial.println(String("Received Bitmap: ") + bitmapLength + " bytes");

  if (bitmapLength != bmpWidth * bmpHeight * 2) {
    Serial.println("Warning: Bitmap Data is bad.");
    refreshLcdScreen("[Warning]\nCamera image is distorted.\nPlease wait or restart...", false);
    return;
  }

  // 8bit*2 の形式を 16bit*1 に変換
  for (int i = 0; i < bmpWidth * bmpHeight; i++) {
    imageBuffer16bits[i] = (imageBuffer8bits[2 * i] << 8) + imageBuffer8bits[2 * i + 1];
  }
}

void _receiveJpegImage() {
  uint8_t buf[jpegHeaderPacketLength];
  int receivedLength = Serial2.readBytes(buf, jpegHeaderPacketLength);
  Serial.println(String("JPEG Header Packets: ") + receivedLength + " bytes");

  if (receivedLength != jpegHeaderPacketLength) {
    Serial.println("Warning: JPEG Header Packets is bad.");
    refreshLcdScreen("[Warning]\nCamera image is distorted.\nPlease wait or restart...", false);
    return;
  }

  // JPEG画像の直前に来るヘッダーパケットをチェック
  Serial.print(buf[0]);
  Serial.print(", ");
  Serial.print(buf[1]);
  Serial.print(", ");
  Serial.println(buf[2]);

  if ((buf[0] != jpegHeaderFixedPackets[0])
      || (buf[1] != jpegHeaderFixedPackets[1])
      || (buf[2] != jpegHeaderFixedPackets[2])) {
    Serial.println("Warning: JPEG Header Packets is bad.");
    refreshLcdScreen("[Warning]\nCamera image is distorted.\nPlease wait or restart...", false);
    return;
  }

  jpegImageSize = (uint32_t)(buf[4] << 16) | (buf[5] << 8) | buf[6];
  Serial.println(String("JPEG Data Length: ") + jpegImageSize + " bytes");
  if (jpegImageSize > bmpWidth * bmpHeight * 2) {
    Serial.println("Warning: Received JPEG Image is too large.");
    refreshLcdScreen("[Warning]\nJPEG image is too large.\nPlease wait or restart...", false);
    return;
  }

  // サーバーへの送信に使用するJPEG画像として保管
  Serial2.readBytes(imageBuffer8bits, jpegImageSize);
  refreshLcdScreen("READY", true);
}

bool httpPOST(String uri, const String& requestPayload, String& responsePayload) {
  Serial.println("Connecting to Server...");
  HTTPClient httpClient;
  httpClient.setTimeout(TIMEOUT_MS);

  if (!httpClient.begin(HOSTNAME, PORT, uri)) {
    // HTTPコネクションの確立に失敗
    Serial.println("HTTP Connection Failed.");
    beepFatal();
    responsePayload = "";
    return false;
  }

  // POSTリクエストを生成
  Serial.println("HTTP Connection Started.");
  httpClient.addHeader("Content-Type", "application/json");

  // POSTリクエストを送信
  Serial.println(String("Request Payload Size: ") + requestPayload.length());
  int httpCode = httpClient.POST(requestPayload);

  // サーバーからのレスポンスを受信
  Serial.println(String("Response: [") + httpCode + "]");
  if (httpCode != HTTP_CODE_OK) {
    httpClient.end();
    beepFailure();
    responsePayload = "";
    return false;
  }

  // レスポンスボディを返す
  responsePayload = httpClient.getString();
  Serial.println(responsePayload);
  return true;
}

void _cancelSession() {
  if (currentSessionID == "") {
    beepOK();
    return;
  }

  // リクエストボディを生成
  String requestPayload = String("{\"session_id\":\"") + currentSessionID + "\"}";

  // サーバーにPOST
  String responsePayload;
  if (!httpPOST("/cancel", requestPayload, responsePayload)) {
    refreshLcdScreen("[Error]\nConnection Failed.\nPlease retry...", true);
    return;
  }

  // レスポンスの中身を取り出す
  JSONVar responseJSON = JSON.parse(responsePayload);
  bool success = (responseJSON.hasOwnProperty("success") && (bool)responseJSON["success"]);
  if (success) {
    // 仮登録セッションの削除に成功
    beepOK();
  } else {
    // 仮登録セッションの削除に失敗
    beepFailure();
  }

  // 結果に関わらずこの機器が保持しているセッションIDをクリアする
  currentSessionID = "";
  applyLcdFixedMessage("");
  refreshLcdScreen("SessionID Cleared.", true);
}

void _registerProduct() {
  if (currentSessionID == "") {
    beepFailure();
    return;
  }

  // リクエストボディを生成
  String requestPayload = String("{\"session_id\":\"") + currentSessionID + "\",\"image\":[";
  for (int i = 0; i < jpegImageSize; i++) {
    requestPayload += String(imageBuffer8bits[i]);
    if (i + 1 < jpegImageSize) {
      requestPayload += String(",");
    }
  }
  requestPayload += String("]}");

  // サーバーにPOST
  String responsePayload;
  if (!httpPOST("/register", requestPayload, responsePayload)) {
    refreshLcdScreen("[Error]\nConnection Failed.\nPlease retry...", true);
    return;
  }

  // レスポンスの中身を取り出す
  JSONVar responseJSON = JSON.parse(responsePayload);
  bool success = (responseJSON.hasOwnProperty("success") && (bool)responseJSON["success"]);
  if (success) {
    // 商品情報の確定に成功
    beepOK();

    // セッションIDをクリア
    currentSessionID = "";
    applyLcdFixedMessage("");
    refreshLcdScreen("Register OK.", true);
  } else {
    // 商品情報の確定に失敗
    beepFailure();
    refreshLcdScreen("[Error]\nRegister Failed.\nPlease retry...", true);
  }
}

void _detectExpirationDate() {
  // リクエストボディを生成
  Serial.println("Buffering...");
  String requestPayload = String("{\"image\":[");
  for (int i = 0; i < jpegImageSize; i++) {
    requestPayload += String(imageBuffer8bits[i]);
    if (i + 1 < jpegImageSize) {
      requestPayload += String(",");
    }
  }
  requestPayload += String("]}");

  // サーバーにPOST
  String responsePayload;
  if (!httpPOST("/detect", requestPayload, responsePayload)) {
    refreshLcdScreen("[Error]\nConnection Failed.\nPlease retry...", true);
    return;
  }

  // レスポンスの中身を取り出す
  JSONVar responseJSON = JSON.parse(responsePayload);
  bool success = (responseJSON.hasOwnProperty("success") && (bool)responseJSON["success"]);
  if (success) {
    if (!responseJSON.hasOwnProperty("session_id")) {
      // セッションIDの取り出しに失敗
      currentSessionID = "";
      beepFailure();
      return;
    }

    // セッションIDを一時的に保管
    currentSessionID = responseJSON["session_id"];

    // 検出した賞味期限を取り出す
    int year = (int)responseJSON["expiration_date"]["year"];
    int month = (int)responseJSON["expiration_date"]["month"];
    int day = (int)responseJSON["expiration_date"]["day"];

    // 賞味期限を画面上に表示
    applyLcdFixedMessage(
      String("Detect OK.\nDate: ") +
      year + "." + month + "." + day
    );

    // 賞味期限の読み取りに成功
    beepOK();
  } else {
    // 賞味期限の読み取りに失敗
    beepFailure();
  }
}

void loop() {
  if (Serial2.available()) {
    // カメラから画像が送られてきたらLCDに表示する
    _receiveImageForLcd();

    // JPEG画像を受け取ってサーバーへの送信に備える
    _receiveJpegImage();
  }

  // ボタン押下状態更新
  M5.update();

  // A: 現在の仮登録セッションをクリアする
  if (M5.BtnA.wasReleased()) {
    Serial.println("Pressed A Button: SessionID Clear");
    Serial2.println("pause");
    lastPressedButtonMS = millis();
    beepOK();
    _cancelSession();
    Serial2.println("resume");
    return;
  }

  // B: 最新の画像を商品イメージとしてサーバーに送って確定させる
  if (M5.BtnB.wasReleased()) {
    Serial.println("Pressed B Button: Sending Product Image");
    Serial2.println("pause");
    lastPressedButtonMS = millis();
    beepOK();
    _registerProduct();
    Serial2.println("resume");
    return;
  }

  // C: ボタン押下時点のカメラ画像をサーバーに送って賞味期限を取り出す
  if (M5.BtnC.wasReleased()) {
    Serial.println("Pressed C Button: Sending ExpirationDate Image");
    Serial2.println("pause");
    lastPressedButtonMS = millis();
    beepOK();
    _detectExpirationDate();
    Serial2.println("resume");
    return;
  }

  if (millis() - lastPressedButtonMS > SHUTDOWN_MS) {
    // 一定時間ボタン押下がされなかったら節電のため自動的に電源を切る (ただし実態はディープスリープ)
    Serial.println(String(SHUTDOWN_MS) + " ms. have passed. Shutdown now...");
    Serial2.println("pause");
    delay(500);
    M5.Power.powerOFF();
  }
}
