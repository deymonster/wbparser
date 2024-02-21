from typing import List

from pydantic import ValidationError

from db.db import get_db

from parser.schemas import SaleObjectIn
from parser.models import SaleObject
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import NoResultFound
from bot.logger import WBLogger

logger = WBLogger(__name__).get_logger()


def convert_sale_data_to_sale_object_in(office_id, date, name, sale_count, return_count, sale_sum, return_sum,
                                        proceeds, amount, bags_sum, office_rating, percent, office_rating_sum,
                                        supplier_return_sum):
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
    )


def get_or_none(session: Session, model, **kwargs):
    """ Функция для проверки наличие данных в БД"""
    try:
        return session.query(model).filter_by(**kwargs).first()
    except NoResultFound:
        return None


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
                db_data = SaleObject(**sale_object_in.model_dump())
                db.add(db_data)
                logger.info(f"Данные записаны - {db_data}")
            except ValidationError as e:
                logger.error(f"Ошибка валидации данных: {e}")
                continue
