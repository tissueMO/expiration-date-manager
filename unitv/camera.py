########################################################################
#   Groveポートを通して、カメラの画像をM5Stackにシリアル転送します。
########################################################################
from machine import UART
from fpioa_manager import fm
import sensor, lcd, time

WIDTH = 160
HEIGHT = 120

lcd.init(freq=15000000)

sensor.reset()
# sensor.set_pixformat(sensor.GRAYSCALE)
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)
sensor.set_windowing((WIDTH, HEIGHT))
sensor.set_vflip(True)
sensor.set_hmirror(True)
sensor.run(True)
sensor.skip_frames()

# UnitV の Grove ポートを通してシリアル通信する
fm.register(35, fm.fpioa.UART1_TX, force=True)
fm.register(34, fm.fpioa.UART1_RX, force=True)

uart = UART(UART.UART1, 1152000, 8, 0, 0, timeout=1000, read_buf_len=4096)
enabled = True

while True:
    if enabled:
        img = sensor.snapshot()

        # Grove ポートを通して M5Stack へ転送
        uart.write(img)

        # MaixPy IDE で表示できるようにする
        lcd.display(img)

    # M5Stack からの命令を取得
    line =  uart.readline()
    if line is not None:
        statement = line.decode("utf-8")
        # 改行コードを除去
        statement = statement[:(len(statement) - 2)]
        if statement == "pause":
            enabled = False
        elif statement == "resume":
            enabled = True
