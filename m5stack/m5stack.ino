#include <M5Stack.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>

// Wi-Fi 接続、通信設定
#include "settings.h"
const char* ssid = SSID;
const char* password = PASSWORD;
const char* host = HOSTNAME;
const int port = PORT;

#if PORT == 443
  WiFiClientSecure client;
#else
  WiFiClient client;
#endif

// 受け取る画像の仕様とバッファを確保
const int x = 160;
const int y = 120;
uint8_t imageBuffer8bits[x * y * 2];
uint16_t imageBuffer16bits[x * y];

int getImageLength() {
  int length = 0;
  String temp;
  temp = String("{ \"width\": ") + String(x) + ", \"height\": " + String(y) + ", \"image\": [";
  length += temp.length();

  for (int i = 0; i < x * y; i++) {
    temp = String(imageBuffer16bits[i]);
    length += temp.length() + 1;
  }

  length--;
  temp = String("] }");
  length += temp.length();

  return length;
}

void setup() {
  M5.begin();
  Serial.begin(115200);

  // M5Stack Groveポート
  Serial2.begin(1152000, SERIAL_8N1, 21, 22);
  
  // Wi-Fi 接続
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
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

//  // ここまでの処理の途中にカメラから送られてきたデータをすべて破棄
//  while (Serial2.available()) {
//    Serial2.readBytes(imageBuffer8bits, x * y * 2);
//  }
}

void loop() {
  M5.update();

  if (Serial2.available()) {
    // カメラから画像が送られてきたらLCDに表示する
    Serial.println(String("Received by UnitV.") + Serial2.available() + " bytes.");
    Serial2.readBytes(imageBuffer8bits, x * y * 2);
 
    for (int i = 0; i < x * y; i++) {
      imageBuffer16bits[i] = (imageBuffer8bits[2 * i] << 8) + imageBuffer8bits[2 * i + 1];
    }

    M5.Lcd.drawBitmap(0, 0, x, y, imageBuffer16bits);
  }

  if (M5.BtnC.wasReleased()) {
    // ボタン押下時点のカメラ画像をサーバーに送る
    Serial.println("Pressed C Button.");

    // カメラからの受信を停止する
    Serial2.println("pause");

    // サーバーに接続
    Serial.println("Connecting to Server...");
    if (!client.connect(host, port)) {
      Serial.println("Connection Failed.");
      return;
    }

    // リクエスト生成
    String url = "/detect";
    String request = 
      String("POST ") + url + " HTTP/1.1\r\n" +
      "Host: " + host + "\r\n" +
      "Accept: */*\r\n" +
      "Connection: close\r\n" +
      "Content-Type: application/json\r\n" +
      "Content-Length: " + getImageLength() + "\r\n" +
      "\r\n";
    Serial.println(request);
    client.print(request);

    // リクエストボディ生成しながら随時送信
    client.print(
      String("{ \"width\": ") + String(x) +
      ", \"height\": " + String(y) +
      ", \"image\": ["
    );

    String temp;
    for (int i = 0; i < x * y; i++) {
      temp = String(imageBuffer16bits[i]);
      if (i + 1 < x * y) {
        temp += ",";
      }
      client.print(temp);
    }

    client.print(String("] }"));

    delay(100);
    Serial.println("Closing connection.");
  
    // レスポンス受信
    Serial.print("Response: ");
    while(client.available()) {
      String line = client.readStringUntil('\r');
      Serial.print(line);
    }
    Serial.println();

    // カメラからの受信を再開する
    Serial2.println("resume");
  }
}
