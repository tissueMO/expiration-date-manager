###############################################################################
#    暫定登録済みの商品を表すテーブルの定義
###############################################################################
from model import Base
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql.schema import Column
from sqlalchemy.sql.sqltypes import Integer, Text, Boolean, DateTime


"""暫定登録商品トランザクションテーブル
"""
class TemporaryProduct(Base):
    __tablename__ = "temporary_products"
    __table_args__ = {"extend_existing": True}

    # 固有のID
    id = Column(Integer, primary_key=True, autoincrement=True)

    # セッションID
    session_id = Column(Text, nullable=False)

    # 賞味期限
    expiration_date = Column(DateTime, nullable=False)

    # レコード作成日時
    created_time = Column(DateTime, nullable=False)
