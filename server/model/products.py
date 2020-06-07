###############################################################################
#    本登録済みの商品を表すテーブルの定義
###############################################################################
from model import Base
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql.schema import Column
from sqlalchemy.sql.sqltypes import Integer, Text, Boolean, DateTime


"""本登録商品トランザクションテーブル
"""
class Product(Base):
    __tablename__ = "products"
    __table_args__ = {"extend_existing": True}

    # 固有のID
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 商品画像のパス
    image_path = Column(Text, nullable=False)

    # 賞味期限
    expiration_date = Column(DateTime, nullable=False)

    # 実際に消費済みかどうか
    consumed = Column(Integer, nullable=False)

    # 買い物リストに追記済みかどうか
    added_shopping_list = Column(Integer, nullable=False)

    # レコード作成日時
    created_time = Column(DateTime, nullable=False)
