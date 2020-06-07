###############################################################################
#    初期データを流し込みます。
#    マイグレーション実行後に手動で呼び出して下さい。
#    ただし、起動ディレクトリーは /server/ 直下にしておく必要があります。
###############################################################################
import sys
sys.path.insert(0, ".")
from model.products import Product
from model.temporary_products import TemporaryProduct
from datetime import datetime as dt
from datetime import timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

if __name__ == "__main__":
    # セッション作成
    engine = create_engine("sqlite:///db/datastore.db")
    session = sessionmaker(bind=engine)()

    # テーブル内レコード全削除
    session.query(Product).delete()
    session.query(TemporaryProduct).delete()

    # 初期状態で挿入するレコードの定義 ここから >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    # now = dt.now()
    # 初期状態で挿入するレコードの定義 ここまで >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

    # 変更をコミット
    session.commit()
