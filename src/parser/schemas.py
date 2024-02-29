from datetime import datetime

from pydantic import BaseModel, Field


class SaleObjectIn(BaseModel):
    """Schema for SaleObject in DB"""
    office_id: int
    name: str
    date: datetime
    sale_count: int
    return_count: int
    sale_sum: int
    return_sum: int
    proceeds: int
    amount: int
    bags_sum: int
    office_rating: float
    percent: float
    office_rating_sum: int
    supplier_return_sum: int
    office_speed_sum: float


