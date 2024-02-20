from db.base_class import Base
from sqlalchemy import Column, Integer, String, Date, DateTime, Float


class SaleObject(Base):
    """Model poll"""

    id = Column(Integer, primary_key=True, index=True)
    office_id = Column(Integer)
    name = Column(String)
    date = Column(Date)
    sale_count = Column(Integer)
    return_count = Column(Integer)
    sale_sum = Column(Integer)
    return_sum = Column(Integer)
    proceeds = Column(Integer)
    amount = Column(Integer)
    bags_sum = Column(Integer)
    office_rating = Column(Float)
    percent = Column(Integer)
    office_rating_sum = Column(Integer)
    supplier_return_sum = Column(Integer)





