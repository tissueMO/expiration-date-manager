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
uint8_t rx_buffer[x * y * 2];
uint16_t rx_buffer2[x * y];

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
}

void loop() {
  M5.update();

  if (Serial2.available()) {
    // カメラから画像が送られてきたらLCDに表示する
    Serial2.readBytes(rx_buffer, x * y * 2);
    Serial.println("Received by UnitV.");
 
    for (int i = 0; i < x * y; i++) {
      rx_buffer2[i] = (rx_buffer[2 * i] << 8) + rx_buffer[2 * i + 1];
    }

    M5.Lcd.drawBitmap(0, 0, x, y, rx_buffer2);
  }

  if (M5.BtnC.wasReleased()) {
    // ボタン押下時点のカメラ画像をサーバーに送る
    Serial.println("Pressed C Button.");

    // サーバーに接続
    Serial.println("Connecting to Server...");
    if (!client.connect(host, port)) {
      Serial.println("Connection Failed.");
      return;
    }

    // リクエスト生成
    String body = String("{ \"width\": ");
    body += String(x);
    body += ", \"height\": ";
    body += String(y);
    body += ", \"image\": [";
    for (int i = 0; i < x * y; i++) {
      body += String(rx_buffer[i]);
      if (i + 1 < x * y) {
        body += ",";
      }
    }
    body += "] }";

    String url = "/detect";
    String request = 
      String("POST ") + url + " HTTP/1.1\r\n" +
      "Connection: close\r\n" +
      "Content-Type: application/json\r\n" +
      "Content-Length: " + body.length() + "\r\n" +
      "\r\n";

    // リクエスト送信
    Serial.println(request);
    client.print(request);
    client.print(body);
    delay(10);
    Serial.println("Closing connection.");
  
    // レスポンス受信
    Serial.print("Response: ");
    while(client.available()) {
      String line = client.readStringUntil('\r');
      Serial.print(line);
    }
    Serial.println();
  }
}
