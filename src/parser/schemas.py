from datetime import datetime

from pydantic import BaseModel, constr, Field


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
    rate_by_region: float
    percent: float
    office_rating_sum: int
    supplier_return_sum: int
    office_speed_sum: float


class OfficeModel(BaseModel):
    office_id: constr(strip_whitespace=True, min_length=1)
    name: constr(strip_whitespace=True, min_length=1)
    company: constr(strip_whitespace=True, min_length=1)
    manager: constr(strip_whitespace=True, min_length=1)
    office_area: constr(strip_whitespace=True, min_length=1)
    rent: constr(strip_whitespace=True, min_length=1)
    salary_rate: constr(strip_whitespace=True, min_length=1)
    min_wage: constr(strip_whitespace=True, min_length=1)
    internet: constr(strip_whitespace=True, min_length=1)
    administration: constr(strip_whitespace=True, min_length=1)


class OfficeRatesModel(BaseModel):
    """Model for OfficeRates in DB"""

    office_id: int
    office_name: str | None
    avg_hours: float | None
    avg_hours_by_region: float | None
    avg_rate: float | None
    avg_region_rate: float | None
    inbox_count: int | None
    limit_delivery: int | None
    total_count: int | None
    workload: int | None
