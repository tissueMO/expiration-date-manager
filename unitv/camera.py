########################################################################
#   Groveポートを通して、カメラの画像をM5Stackにシリアル転送します。
########################################################################
from machine import UART
from fpioa_manager import fm
import sensor, lcd, time

WIDTH = 320
HEIGHT = 240

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

uart = UART(UART.UART1, 1152000, 8, 0, 0, timeout=2000, read_buf_len=4096)
enabled = False

print("---- Camera Started ---------------------------------------")
while True:
    if enabled:
        # Grove ポートを通して M5Stack へ転送
        try:
            # 無圧縮ビットマップ画像を送信
            img = sensor.snapshot()
            img_shrinked = img.mean_pooled(2, 2)
            uart.write(img_shrinked)

            # MaixPy IDE で表示する
            lcd.display(img_shrinked)

            # JPEG圧縮 (サイズ可変)
            img_buf = img.compress(quality=50)

            # 10 bytes の開始データを添えてJPEG画像を送信
            img_size1 = (img_buf.size() & 0xFF0000) >> 16
            img_size2 = (img_buf.size() & 0x00FF00) >> 8
            img_size3 = (img_buf.size() & 0x0000FF) >> 0
            data_packet = bytearray([0xFF, 0xD8, 0xEA, 0x01, img_size1, img_size2, img_size3, 0x00, 0x00, 0x00])
            uart.write(data_packet)
            uart.write(img_buf)
        except:
            pass

        print("Sending Image Completed.")

    # M5Stack からの命令を取得
    line =  uart.readline()
    if line is not None:
        try:
            statement = line.decode("utf-8")
        except:
            statement = ""

        # 改行コードを除去
        statement = statement[:(len(statement) - 2)]
        if statement == "pause":
            enabled = False
            print("Pausing...")
        elif statement == "resume":
            enabled = True
            print("Resumed.")

    time.sleep(2.0)
