#include <M5Stack.h>

const int x = 160;
const int y = 120;
uint8_t rx_buffer[x * y * 2];
uint16_t rx_buffer2[x * y];

void setup() {
  M5.begin();
  Serial.begin(115200);

  // M5Stack Groveポート
  Serial2.begin(921600, SERIAL_8N1, 21, 22);
}

void loop() {
  if (Serial2.available()) {
    int rx_size = Serial2.readBytes(rx_buffer, x * y * 2);
    // Serial.print(rx_size);
    // Serial.println(" bytes Received.");
 
    for(int i = 0; i < x * y; i++) {
      rx_buffer2[i] = (rx_buffer[2 * i] << 8) + rx_buffer[2 * i + 1];
    }

    M5.Lcd.drawBitmap(0, 0, x, y, rx_buffer2);
  }
}
