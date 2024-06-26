from typing import List, Set
from datetime import date

from pydantic import ValidationError
from sqlalchemy import inspect, exc
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.dialects.postgresql import insert as pg_insert


from db.db import get_db

from parser.schemas import SaleObjectIn, OfficeRatesModel
from parser.models import SaleObject, OfficeObject, OfficeRatingObject
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import NoResultFound
from bot.logger import WBLogger

import csv

logger = WBLogger(__name__).get_logger()


def convert_sale_data_to_sale_object_in(
    office_id,
    date,
    name,
    sale_count,
    return_count,
    sale_sum,
    return_sum,
    proceeds,
    amount,
    bags_sum,
    office_rating,
    percent,
    office_rating_sum,
    supplier_return_sum,
    office_speed_sum,
):
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
        office_speed_sum=round(float(office_speed_sum), 2),
    )


def get_or_none(session: Session, model, **kwargs):
    """Функция для проверки наличие данных в БД"""
    try:
        return session.query(model).filter_by(**kwargs).first()
    except NoResultFound:
        return None


def get_all_offices(db_session):
    """Функция для получения всех офисов"""

    try:
        offices = db_session.query(OfficeObject).all()
        office_list = [
            {"office_id": office.office_id, "name": office.name} for office in offices
        ]
        return office_list
    except Exception as e:
        logger.error(f"Error in get_all_offices: {e}")
        return []


def get_office_info(db_session, office_id):
    """Получение офиса констант по office_id"""

    try:
        office_data = (
            db_session.query(OfficeObject).filter_by(office_id=office_id).first()
        )
        if office_data:
            return {
                c.key: getattr(office_data, c.key)
                for c in inspect(office_data).mapper.column_attrs
            }
        return None
    except Exception as e:
        logger.error(f"Error in get_office_info: {e}")
        return []


def update_office_field(db_session, office_id, field, new_value):
    """Обновление полей офиса"""
    try:
        office_data = (
            db_session.query(OfficeObject).filter_by(office_id=office_id).first()
        )
        if office_data:
            setattr(office_data, field, new_value)
            db_session.commit()
            return True
        else:
            logger.error(f"Office with ID {office_id} not found.")
            return False
    except SQLAlchemyError as e:
        db_session.rollback()
        logger.error(f"Error in update_office_field: {e}")
        return False


def add_office(db_session, office_data):
    """Добавление нового офиса в базу данных"""
    try:
        new_office = OfficeObject(**office_data)
        db_session.add(new_office)
        db_session.commit()
        return True
    except SQLAlchemyError as e:
        db_session.rollback()
        logger.error(f"Error in add_office: {e}")
        return False


def delete_office(db_session, office_id):
    """Удаление офиса по ID"""

    try:
        office_to_delete = (
            db_session.query(OfficeObject).filter_by(office_id=office_id).first()
        )
        if office_to_delete:
            db_session.delete(office_to_delete)
            db_session.commit()
            return True
        else:
            logger.error(f"Office with ID {office_id} not found.")
            return False
    except SQLAlchemyError as e:
        db_session.rollback()
        logger.error(f"Error in delete_office: {e}")
        return False


def safe_sale_object_to_db(sale_objects: List[dict]):
    """Сервис функция для валидации входных данных - списка SaleObjectIn и запись их в БД"""
    for sale_object in sale_objects:
        with get_db() as db:
            try:
                logger.info(f"sale_object is  - {sale_object}")
                sale_object_in = convert_sale_data_to_sale_object_in(
                    **sale_object.to_dict()
                )
                existing_data = get_or_none(
                    db,
                    SaleObject,
                    date=sale_object_in.date,
                    office_id=sale_object_in.office_id,
                )
                if existing_data:
                    logger.info(
                        f"Данные для даты {sale_object_in.date} "
                        f"и офиса {sale_object_in.office_id} уже существуют. Пропускаем."
                    )
                    continue
                # office_data = get_office_info(db, sale_object_in.office_id)
                office_data = get_or_none(
                    db, OfficeObject, office_id=sale_object_in.office_id
                )
                if not office_data:
                    logger.warning(
                        f"Отсутствуют данные для офиса {sale_object_in.office_id}. Пропускаем."
                    )
                    continue
                logger.info(f"Office data - {office_data}")
                # Вычисление дополнительных полей
                reward_plan = round(
                    float(sale_object_in.proceeds * sale_object_in.percent / 100), 2
                )
                salary_fund_plan = round(
                    float(sale_object_in.proceeds * office_data.salary_rate / 100), 2
                )
                actual_salary_fund = round(
                    float(max(salary_fund_plan, office_data.min_wage)), 2
                )
                difference_salary_fund = (
                    round(float(actual_salary_fund - salary_fund_plan), 2),
                )
                daily_rent = round(float(office_data.rent / 30), 2)
                daily_administration = round(float(office_data.administration / 30), 2)
                daily_internet = round(float(office_data.internet / 30), 2)

                maintenance = round(float(sale_object_in.proceeds / 1000000 * 630), 2)
                profitability = round(
                    float(
                        reward_plan
                        - actual_salary_fund
                        - daily_administration
                        - daily_internet
                        - maintenance
                        - daily_rent
                    ),
                    2,
                )

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
                    profitability=profitability,
                )
                db.add(db_data)
                logger.info(f"Данные записаны - {db_data}")
            except ValidationError as e:
                logger.error(f"Ошибка валидации данных: {e}")
                continue


def read_csv_to_dict(file_name):
    """Читаем существующий CSV-файл и возвращаем содержимое в виде списка словарей."""

    data = []
    with open(file_name, "r", newline="", encoding="utf-8") as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            data.append(row)
    return data


def update_csv_with_db_data(csv_file_name="processed_data.csv"):
    existing_data = read_csv_to_dict(csv_file_name)
    existing_data_indexed = {int(item["office_id"]): item for item in existing_data}


def create_or_update_ratings(
    list_in: List[OfficeRatesModel],
    index_elements: List[str],
    on_conflict_set: Set[str],
    db: Session,
):
    """Добавление рейтинга офиса в базу данных если дата существует в базе данных
    то происходит обновление рейтинга,  если даты нет то создается новая запись

    :param list_in: Список объектов
    :param index_elements: Индексы элементов для проверки уникальности
    :param on_conflict_set: Список полей, которые будут обновляться при конфликтах
    :param db: База данных
    """
    objs = []
    for obj_in in list_in:
        obj_dict = obj_in.dict(exclude_unset=True)
        obj_dict["created_at"] = date.today()
        objs.append(obj_dict)

    insert_query = pg_insert(OfficeRatingObject).values(objs)
    insert_query = insert_query.on_conflict_do_update(
        index_elements=index_elements,
        set_={key: getattr(insert_query.excluded, key) for key in on_conflict_set},
    ).returning(OfficeRatingObject)

    try:
        db.execute(insert_query)
        db.commit()
    except exc.IntegrityError as e:
        db.rollback()
        print(e)
