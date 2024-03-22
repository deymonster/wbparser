from bot.logger import WBLogger
from db.session import SessionLocal
import csv

from parser.models import OfficeObject

# set up logging
logger = WBLogger(__name__).get_logger()

with SessionLocal() as db:
    with open('processed_data.csv', 'r', encoding='utf-8-sig') as file:
        csv_reader = csv.reader(file)
        headers = next(csv_reader)

        for row in csv_reader:
            office_id = int(row[0])
            name = row[1].strip('"')
            company = row[2]
            manager = row[3]
            office_area = int(row[4]) if row[4] else 0
            rent = float(row[5])
            salary_rate = float(row[6])
            min_wage = int(row[7])
            internet = int(row[8])
            administration = int(row[9])

            existing_office = db.query(OfficeObject).filter_by(office_id=office_id).first()
            if not existing_office:
                logger.info('Initial new data to OfficeObject')
                office_object = OfficeObject(
                    office_id=office_id,
                    name=name,
                    company=company,
                    manager=manager,
                    office_area=office_area,
                    rent=rent,
                    salary_rate=salary_rate,
                    min_wage=min_wage,
                    internet=internet,
                    administration=administration
                )
                db.add(office_object)
                logger.info(f'Office ID {office_object.office_id} with name {office_object.name} was  added')
            else:
                logger.info('Trying to update office data...')
                existing_office.name = name
                existing_office.company = company
                existing_office.manager = manager
                existing_office.office_area = office_area
                existing_office.rent = rent
                existing_office.salary_rate = salary_rate
                existing_office.min_wage = min_wage
                existing_office.internet = internet
                existing_office.administration = administration

    db.commit()

