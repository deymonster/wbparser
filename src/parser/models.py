from db.base_class import Base
from sqlalchemy import Column, Integer, String, Date, DateTime, Float


class OfficeObject(Base):
    """Office object"""

    id = Column(Integer, primary_key=True, index=True)
    office_id = Column(Integer, unique=True)
    company = Column(String)
    manager = Column(String)
    office_area = Column(Integer, default=0)
    rent = Column(Float)
    salary_rate = Column(Float)
    min_wage = Column(Integer)
    internet = Column(Integer)
    administration = Column(Integer)


class SaleObject(Base):
    """Model poll"""

    id = Column(Integer, primary_key=True, index=True)
    office_id = Column(Integer)
    company = Column(String)
    manager = Column(String)
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
    percent = Column(Float)
    office_rating_sum = Column(Integer)
    supplier_return_sum = Column(Integer)
    office_speed_sum = Column(Float)

    reward_plan = Column(Float)
    salary_fund_plan = Column(Float)
    actual_salary_fund = Column(Float)
    difference_salary_fund = Column(Float)
    rent = Column(Float)
    administration = Column(Float)
    internet = Column(Float)

    maintenance = Column(Float)
    profitability = Column(Float)






