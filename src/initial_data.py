from bot.logger import WBLogger
from db.session import SessionLocal
import csv

from parser.models import OfficeObject

# set up logging
logger = WBLogger(__name__).get_logger()


with open('data.csv', 'r', encoding='utf-8-sig') as file:
    csv_reader = csv.DictReader(file, fieldnames=['office_id', 'company', 'manager', 'office_area', 'rent',
                                                  'salary_rate', 'min_wage', 'internet', 'administration'],
                                )
    next(csv_reader)
    for row in csv_reader:
        logger.info(f'row - {row}')
        office_id = int(row.get('office_id', 0))
        company = row.get('company', '')
        manager = row.get('manager', '')
        office_area = int(row['office_area']) if row['office_area'] else 0
        rent = float(row.get('rent', 0.0))
        salary_rate = float(row.get('salary_rate', 0.0))
        min_wage = int(row.get('min_wage', 0))
        internet = int(row.get('internet', 0))
        administration = int(row.get('administration', 0))

        office_object = OfficeObject(
            office_id=office_id,
            company=company,
            manager=manager,
            office_area=office_area,
            rent=rent,
            salary_rate=salary_rate,
            min_wage=min_wage,
            internet=internet,
            administration=administration
        )
        db = SessionLocal()
        db.merge(office_object)
        logger.info(f'Office ID {office_object.office_id} was  added')
        db.commit()
logger.info('Applied initial office data')
