from typing import List

from pydantic import ValidationError

from db.db import get_db

from parser.schemas import SaleObjectIn
from parser.models import SaleObject, OfficeObject
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import NoResultFound
from bot.logger import WBLogger

logger = WBLogger(__name__).get_logger()


def convert_sale_data_to_sale_object_in(office_id, date, name, sale_count, return_count, sale_sum, return_sum,
                                        proceeds, amount, bags_sum, office_rating, percent, office_rating_sum,
                                        supplier_return_sum, office_speed_sum):
    return SaleObjectIn(
        office_id=office_id,
        date=date,
        name=name,
        sale_count=sale_count,
        return_count=return_count,
        sale_sum=int(sale_sum),
        return_sum=int(return_sum),
        proceeds=int(proceeds),
        amount=int(amount),
        bags_sum=bags_sum,
        office_rating=round(float(office_rating), 3),
        percent=round(float(percent), 2),
        office_rating_sum=int(office_rating_sum),
        supplier_return_sum=supplier_return_sum,
        office_speed_sum=round(float(office_speed_sum), 2)
    )


def get_or_none(session: Session, model, **kwargs):
    """ Функция для проверки наличие данных в БД"""
    try:
        return session.query(model).filter_by(**kwargs).first()
    except NoResultFound:
        return None


def get_office_info(session: Session, office_id):
    """Получение офиса констант по office_id"""

    office_data = session.query(OfficeObject).filter_by(office_id=office_id).first()
    return office_data if office_data else None


def safe_sale_object_to_db(sale_objects: List[dict]):
    """ Сервис функция для валидации входных данных - списка SaleObjectIn и запись их в БД"""
    for sale_object in sale_objects:
        with get_db() as db:
            try:
                logger.info(f'sale_object is  - {sale_object}')
                sale_object_in = convert_sale_data_to_sale_object_in(**sale_object.to_dict())
                existing_data = get_or_none(db, SaleObject, date=sale_object_in.date,
                                            office_id=sale_object_in.office_id)
                if existing_data:
                    logger.info(
                        f"Данные для даты {sale_object_in.date} "
                        f"и офиса {sale_object_in.office_id} уже существуют. Пропускаем.")
                    continue
                # office_data = get_office_info(db, sale_object_in.office_id)
                office_data = get_or_none(db, OfficeObject, office_id=sale_object_in.office_id)
                if not office_data:
                    logger.warning(f"Отсутствуют данные для офиса {sale_object_in.office_id}. Пропускаем.")
                    continue
                logger.info(f'Office data - {office_data}')
                # Вычисление дополнительных полей
                reward_plan = round(float(sale_object_in.proceeds * sale_object_in.percent / 100), 2)
                salary_fund_plan = round(float(sale_object_in.proceeds * office_data.salary_rate / 100), 2)
                actual_salary_fund = round(float(max(salary_fund_plan, office_data.min_wage)), 2)
                difference_salary_fund = round(float(actual_salary_fund - salary_fund_plan), 2),
                daily_rent = round(float(office_data.rent / 30), 2)
                daily_administration = round(float(office_data.administration / 30), 2)
                daily_internet = round(float(office_data.internet / 30), 2)

                maintenance = round(float(sale_object_in.proceeds / 1000000 * 630), 2)
                profitability = round(
                    float(reward_plan - actual_salary_fund -
                          daily_administration - daily_internet - maintenance - daily_rent), 2)

                db_data = SaleObject(
                    **sale_object_in.model_dump(),
                    company=office_data.company,
                    manager=office_data.manager,
                    reward_plan=reward_plan,
                    salary_fund_plan=salary_fund_plan,
                    actual_salary_fund=actual_salary_fund,
                    difference_salary_fund=difference_salary_fund,
                    rent=daily_rent,
                    administration=daily_administration,
                    internet=daily_internet,
                    maintenance=maintenance,
                    profitability=profitability
                )
                db.add(db_data)
                logger.info(f"Данные записаны - {db_data}")
            except ValidationError as e:
                logger.error(f"Ошибка валидации данных: {e}")
                continue
