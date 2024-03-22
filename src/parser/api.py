import csv
from typing import Dict, Any, Callable, Union, IO
import io

from parser.service import safe_sale_object_to_db
from utils.env import base_url_v2, base_url_v1, refresh_url, operations_url, shortages_url, shks_url
from datetime import datetime, timedelta
import pandas as pd
from typing import List, Optional
from dataclasses import dataclass, asdict, field
from parser.column_names import oper_type_mapping
from bot.logger import WBLogger

logger = WBLogger(__name__).get_logger()


@dataclass
class FoundInfo:
    """Датакласс для foundinfo"""
    found_in_office_id: int
    found_at: datetime
    found_by_employee_id: int
    operation: str

    @classmethod
    def from_dict(cls, data: Dict) -> 'FoundInfo':
        """Создание объекта FoundInfo из словаря"""
        return cls(
            found_in_office_id=data['found_in_office_id'],
            found_at=datetime.fromisoformat(data['found_at']),
            found_by_employee_id=data['found_by_employee_id'],
            operation=data['operation']
        )


@dataclass
class Shk:
    """Датакласс для хранения ШК"""
    amount: int
    found_info: Optional[FoundInfo]
    item_name: str
    item_photo_url: str
    item_site_url: str
    new_shk_id: int
    shk_id: int

    @classmethod
    def from_dict(cls, data: Dict) -> 'Shk':
        """Создание объекта Shk из словаря"""
        return cls(
            amount=data['amount'],
            found_info=FoundInfo.from_dict(data['found_info']) if data.get('found_info') else None,
            item_name=data['item_name'],
            item_photo_url=data['item_photo_url'],
            item_site_url=data['item_site_url'],
            new_shk_id=data['new_shk_id'] if data.get('new_shk_id') else None,
            shk_id=data['shk_id']
        )


@dataclass
class ResponseShk:
    """Дата класс для ответа по shortage_id"""
    shks: List[Shk] = field(default_factory=list)

    @staticmethod
    def from_dict(cls, data: Dict):
        """Создание объекта ResponseShk из словаря"""
        shks_list = data.get("shks", [])
        if shks_list and isinstance(shks_list, list):
            shks_list = [Shk.from_dict(item) for item in shks_list]
        return cls(
            shks=shks_list
        )


@dataclass
class Shortage:
    """Дата класс для хранения недостач"""
    shortage_id: int
    create_dt: datetime
    guilty_employee_id: int
    guilty_employee_name: str
    amount: float
    comment: str
    status_id: int
    is_history_exist: bool
    shks_data: Optional[ResponseShk] = None

    @classmethod
    def from_dict(cls, data: Dict) -> 'Shortage':
        """Создание объекта из словаря"""
        shks_data = data.get('shks_data')
        return cls(
            shortage_id=data['shortage_id'],
            create_dt=datetime.fromisoformat(data['create_dt']),
            guilty_employee_id=data['guilty_employee_id'],
            guilty_employee_name=data['guilty_employee_name'],
            amount=data['amount'],
            comment=data['comment'],
            status_id=data['status_id'],
            is_history_exist=data['is_history_exist'],
            shks_data=ResponseShk.from_dict(shks_data) if shks_data else None
        )


@dataclass
class OfficeShortage:
    """ Дата класс для хранения офиса с недостачами"""
    office_id: int
    office_name: str
    office_amount: float
    shortages: List[Shortage] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict) -> 'OfficeShortage':
        """Создание объекта из словаря"""
        shortages_list = data.get("shortages", [])
        if shortages_list and isinstance(shortages_list, list):
            shortages_list = [Shortage.from_dict(item) for item in shortages_list]
        return cls(
            office_id=data["office_id"],
            office_name=data["office_name"],
            office_amount=data["office_amount"],
            shortages=shortages_list,
        )


@dataclass
class Employee:
    """Класс для хранения данных о сотруднике"""
    employee_id: int
    last_name: str
    first_name: str
    middle_name: str
    phone: str
    create_date: datetime
    rating: float

    @classmethod
    def from_dict(cls, data: Dict) -> 'Employee':
        """Создание объекта из словаря"""
        if not data.get('is_deleted'):
            return cls(
                employee_id=data['employee_id'],
                last_name=data['last_name'],
                first_name=data['first_name'],
                middle_name=data['middle_name'],
                phone=data['phones'][0] if data.get('phones') else None,
                create_date=datetime.fromisoformat(data['create_date']),
                rating=data['rating']
            )
        else:
            return None


@dataclass
class EmployeeOperations:
    """Класс для хранения операций сотрудника"""
    date: str
    on_place_cnt: int
    return_count: int
    return_sum: int
    sale_count: int
    sale_sum: int
    barcode: str

    def set_barcode(self, barcode: str):
        self.barcode = barcode

    @classmethod
    def from_dict(cls, data: Dict) -> 'EmployeeOperations':
        """Создание объекта класса из словаря"""
        return cls(
            date=data['date'],
            on_place_cnt=data['on_place_cnt'],
            return_count=data['return_count'],
            return_sum=data['return_sum'],
            sale_count=data['sale_count'],
            sale_sum=data['sale_sum'],
            barcode=None)


# класс для хранения  операций
@dataclass
class Operation:
    """Класс для хранения операций"""
    # dt: datetime # поле для хранения даты операции
    oper_type: str  # тип операции
    oper_amount: float  # cумма операции
    comment: Optional[str] = None  # комментарий - тут обычно ШК товара
    grouped: List['Operation'] = field(default_factory=list)  # дополнительный вложенный список операций

    @classmethod
    def from_dict(cls, data: Dict) -> 'Operation':
        """Создание объекта из словаря"""""
        oper_type = oper_type_mapping.get(data.get('oper_type', ''), '')
        grouped = []
        grouped_data = data.get('grouped', [])
        if grouped_data and isinstance(grouped_data, list):
            grouped = [cls.from_dict(item) for item in grouped_data]
        return cls(
            # dt=datetime.fromisoformat(data.get('dt', '')),
            oper_type=oper_type,
            oper_amount=data.get('oper_amount', 0),
            comment=data.get('comment', None),
            grouped=grouped
        )

    def to_dict(self):
        """Преобразование объекта в словарь"""
        return asdict(self)


#  Класс для хранения операция по дате
@dataclass
class OperationsByDate:
    """Класс для хранения операций по дате"""
    date: datetime
    operations: List[Operation]

    @classmethod
    def from_dict(cls, data: Dict) -> 'OperationsByDate':
        """Создание объекта из словаря"""

        return cls(
            date=datetime.fromisoformat(data.get('date', '')),
            operations=[Operation.from_dict(item) for item in data.get('operations', [])]
        )

    def to_dict(self):
        """Преобразование объекта в словарь"""
        return asdict(self)


# класс для хранения офисов
class Office:
    """Класс для хранения офисов"""

    def __init__(self, id: int, name: str, office_shk: str):
        self.id = id
        self.name = name
        self.office_shk = office_shk


# класс для хранения данных о продажах
class SaleData:
    """Класс для хранения данных о продажах"""

    def __init__(self,
                 office_id: int,  # id офиса
                 name: str,  # наименование офиса
                 date: datetime,  # дата
                 sale_sum: int,  # продажи
                 sale_count: int, # количество продаж
                 return_sum: int, # возвраты
                 return_count: int,  # количество возвратов
                 proceeds: int,  # вознаграждения
                 amount: int,  # объем продаж
                 bags_sum: int,  # пакеты
                 office_rating: float,  # рейтинг ПВЗ
                 percent: int,  # тариф ставка грейд
                 office_rating_sum: int,  # сумма рейтинга
                 supplier_return_sum: int,  # сумма возвратов
                 office_speed_sum: float  # скорость
                 ):
        self.office_id = office_id
        self.name = name
        self.date = date
        self.sale_count = sale_count
        self.return_count = return_count
        self.sale_sum = sale_sum
        self.return_sum = return_sum
        self.proceeds = proceeds
        self.amount = amount
        self.bags_sum = bags_sum
        self.office_rating = office_rating
        self.percent = percent
        self.office_rating_sum = office_rating_sum
        self.supplier_return_sum = supplier_return_sum
        self.office_speed_sum = office_speed_sum

    def to_dict(self):
        return self.__dict__


class ParserWB:
    """Parser for WB API"""

    def __init__(self, session):
        self.base_url_v1 = base_url_v1
        self.base_url_v2 = base_url_v2
        self.refresh_url = refresh_url
        # self.login_url = login_url
        self.session = session
        self.access_token = None
        self.offices = []
        self.employees = []
        self.supplier_id = None
        self.headers = {
            "Accept": "application/json.txt, text/plain, */*",
            "Referer": "https://franchise.wildberries.ru/",
            "sec-ch-ua-mobile": "?0",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            "sec-ch-ua-platform": "Windows",
        }
        self.session.headers.update(self.headers)

    def _get_response_data_wb(self, *, url: str, params: dict = None, prefix: str):
        """
        Get response data from wb api

        :param url: url for request
        :param params: params for request
        :param prefix: prefix for logging

        """
        response = self.session.get(url=url, params=params)
        ERROR_STATUS = {
            "auth": f"Ошибка авторизации {response.status_code}",
            "office": f"Ошибка получения данных по офисам {response.status_code}",
            "sales": f"Ошибка получения данных по продажам {response.status_code}",
            "reward": f"Ошибка получения данных по вознаграждениям {response.status_code}",
            "shortages": f"Ошибка получения данных по недостачам {response.status_code}",
            "shks": f"Ошибка получения данных по ШК в недостаче {response.status_code}",
            "operations": f"Ошибка получения данных по операциям {response.status_code}",
            "employees": f"Ошибка получения данных по сотрудникам {response.status_code}",
            "employees_operations": f"Ошибка получения данных по операциям сотрудников {response.status_code}",
        }
        if response.status_code != 200:
            logger.error(f"{ERROR_STATUS.get(prefix, '')} Response: {response.text}")
        return response.json() if response.status_code == 200 else None

    def _get_supplier_id(self):
        """Get supplier id from wb api - получение ID - supplier_id работника"""
        url = f"{self.base_url_v1}/account"
        params = {'in_short': 'false'}
        try:
            if response := self._get_response_data_wb(url=url, params=params, prefix='auth'):
                self.supplier_id = response['supplier_id']
        except Exception as e:
            logger.error(e)

    def fetch_employees(self):
        """Get list of employees from wb api - Получение списка сотрудников и запись экземпляр класса"""
        url = f"{self.base_url_v1}/account"
        params = {'in_short': 'false'}
        try:
            if response := self._get_response_data_wb(url=url, params=params, prefix='employees'):
                for employee_data in response['employees']:
                    employee = Employee.from_dict(employee_data)
                    # check if employee is not deleted
                    if employee:
                        self.employees.append(employee)
        except Exception as e:
            logger.error(e)

    def fetch_employee_data(self, date_from: datetime, date_to: datetime) -> List[Dict]:
        """
        Get employee operations by date - Получение операций пользователя по диапазону дат

        :param date_from: date from
        :param date_to: date to
        :return: List of dict with employee operations
        """
        url = f"{self.base_url_v2}/employees/proceeds"
        logger.info(f'Url - {url}')
        # get employee list ids from self.employees - получаем список id всех пользователей
        employee_ids = [employee.employee_id for employee in self.employees]
        logger.info(f'Employee ids - {employee_ids}')
        params = {
            'employee_ids': ','.join(map(str, employee_ids)),
            'from': date_from,
            'to': date_to,
            'employee_type': 0
        }
        all_operations = []
        try:
            if response := self._get_response_data_wb(url=url, params=params, prefix='employees_operations'):
                for employee_data in response:
                    operations_employee = []
                    for data in (employee_data.get('by_date') or []):
                        operation = EmployeeOperations.from_dict(data)
                        if operation:
                            operations_employee.append(operation)
                    employee_info = next((e for e in self.employees if e.employee_id == employee_data['employee_id']),
                                         None)
                    all_operations.append({
                        'employee_id': employee_data['employee_id'],
                        'last_name': employee_info.last_name if employee_info else None,
                        'first_name': employee_info.first_name if employee_info else None,
                        'middle_name': employee_info.middle_name if employee_info else None,
                        'phone': employee_info.phone if employee_info else None,
                        'create_date': employee_info.create_date if employee_info else None,
                        'rating': employee_info.rating if employee_info else None,
                        'operations': operations_employee
                    })

        except Exception as e:
            logger.error(e)
        return all_operations

    def fetch_shortages_data(self, date_from: str = None, date_to: str = None):
        """Fetch all shortages from all offices """
        result = []
        date_from = datetime.strptime(date_from, '%Y-%m-%d')
        date_to = datetime.strptime(date_to, '%Y-%m-%d')
        if shortages_response := self._get_response_data_wb(url=shortages_url, prefix='shortages'):

            for data in (shortages_response.get('offices') or []):
                # Преобразование JSON в объект OfficeShortage
                shortages_office_data = OfficeShortage.from_dict(data)
                # Применение фильтрации по датам, если они были переданы
                if date_from and date_to:
                    filtered_shortages = [
                        shortage for shortage in shortages_office_data.shortages
                        if date_from <= shortage.create_dt.replace(tzinfo=None) <= date_to
                    ]
                    for shortage in filtered_shortages:
                        if shks_response := self._get_response_data_wb(url=shks_url,
                                                                       params={'shortage_id': shortage.shortage_id},
                                                                       prefix='shks'):
                            shks_list = shks_response.get('shks', [])
                            shks_objects = [Shk.from_dict(item) for item in shks_list]
                            shks_data = ResponseShk(
                                shks=shks_objects
                            )

                            shortage.shks_data = shks_data

                    if filtered_shortages:
                        result.append(
                            OfficeShortage(
                                office_id=shortages_office_data.office_id,
                                office_name=shortages_office_data.office_name,
                                office_amount=shortages_office_data.office_amount,
                                shortages=filtered_shortages
                            )
                        )
                else:
                    result.append(shortages_office_data)
            return result

    def fetch_offices(self):
        """Get offices from wb api - Получение всех офисов из API WB"""
        url = f"{self.base_url_v1}/account"
        params = {'in_short': 'false'}
        try:
            if response := self._get_response_data_wb(url=url, params=params, prefix='office'):
                self._get_supplier_id()
                for office in response['offices']:
                    logger.info(f"Office ID: {office['id']}, Office name: {office['name']}")
                    if office['is_site_active'] is False:
                        continue
                    self.offices.append(Office(id=office['id'], name=office['name'], office_shk=office['office_shk']))

        except Exception as e:
            logger.error(e)

    def fetch_sales_data(self, date_from=None, date_to=None) -> Union[
        list[Any], list[SaleData]]:
        """Get sales data from wb api - Получение данных по продажам """
        result = []
        date_from = date_from or (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        date_to = date_to or datetime.now().strftime('%Y-%m-%d')
        params = {
            # 'office_ids': office_id,
            'from': date_from,
            'to': date_to
        }
        for office in self.offices:
            office_id = office.id
            params['office_ids'] = office_id
            url_sales = f"{self.base_url_v2}/proceeds"
            url_reward = f"{self.base_url_v1}/accruals"

            # запрос данных по продажам
            sales_data_dict = {}
            sales_data = []
            if sale_response := self._get_response_data_wb(url=url_sales, params=params, prefix='sales'):
                try:
                    sales_data = sale_response[0]
                    if sales_data['by_office'] is None:
                        continue
                    sales_data_dict = {sale['date']: sale for sale in sales_data['by_office']}
                except Exception as e:
                    logger.error(f'Ошибка при обработке данных для офиса {office_id}: {e}')
                    return []

            # запрос данных по вознаграждениям
            rewards_data_dict = {}
            if reward_response := self._get_response_data_wb(url=url_reward, params=params, prefix='reward'):
                rewards_data_dict = {reward['date']: reward for reward in reward_response}

            for date, sale in sales_data_dict.items():
                reward_data = rewards_data_dict.get(date, None)
                amount = reward_data['amount'] if reward_data else 0
                bags_sum = reward_data['ext_data']['bags_sum'] if reward_data else 0
                office_rating = reward_data['ext_data']['office_rating'] if reward_data else 0
                percent = reward_data['ext_data']['percent'][0] if reward_data else 0
                office_rating_sum = reward_data['ext_data']['office_rating_sum'] if reward_data else 0
                supplier_return_sum = reward_data['ext_data']['supplier_return_sum'] if reward_data else 0
                office_speed_sum = reward_data['ext_data']['office_speed_sum'] if reward_data else 0
                if office_speed_sum is None:
                    office_speed_sum = 0
                sale_object = SaleData(
                    office_id=office_id,
                    name=sales_data['office_name'],
                    date=datetime.strptime(date, '%Y-%m-%d'),
                    sale_count=sale['sale_count'],
                    return_count=sale['return_count'],
                    sale_sum=sale['sale_sum'],
                    return_sum=sale['return_sum'],
                    proceeds=sale['proceeds'],
                    amount=amount,
                    bags_sum=bags_sum,
                    office_rating=office_rating,
                    percent=percent,
                    office_rating_sum=office_rating_sum,
                    supplier_return_sum=supplier_return_sum,
                    office_speed_sum=office_speed_sum

                )

                logger.info(f'Обработана дата {date} для офиса {office_id} -- {sale_object.name}')
                result.append(sale_object)
        logger.info('Begin to write data to DB')
        safe_sale_object_to_db(sale_objects=result)
        return result

    def fetch_operations_data(self, date_from: datetime = None, date_to: datetime = None):
        self._get_supplier_id()
        params = {
            'supplier_id': self.supplier_id,
            'all': 'true',
        }
        if operations_response := self._get_response_data_wb(url=operations_url, params=params, prefix='operations'):
            details_data = operations_response['details']
            all_operations = [OperationsByDate.from_dict(item) for item in details_data]

            # Фильтрация операций по датам, если они были переданы

            if date_from and date_to:
                date_from = datetime.strptime(date_from, '%Y-%m-%d')
                date_to = datetime.strptime(date_to, '%Y-%m-%d')
                filtered_operations = [op for op in all_operations if date_from <= op.date <= date_to]
                return filtered_operations
            else:
                return all_operations

    def generate_csv_io(self, data: List[OfficeShortage], filename: str):
        # Объект в памяти для записи CSV
        csv_buffer = io.StringIO()

        # Создаем объект writer для записи в CSV
        csv_writer = csv.DictWriter(csv_buffer,
                                    fieldnames=[
                                        "Office ID",
                                        "Название офиса",
                                        "Общая недостача офиса",
                                        "ID недостачи",
                                        "Дата недостачи",
                                        "ID сотрудника",
                                        "Ф.И.О сотрудника",
                                        "Сумма недостачи",
                                        "Причина недостачи",
                                        "Status ID",
                                        "is history exists",
                                        "Стоимость недостачи по ШК",
                                        "Наименование товара",
                                        "URL на фото товара",
                                        "URL товара в каталоге",
                                        "Новый ШК",
                                        "Основной ШК",
                                        "Найдено в офисе ID",
                                        "Дата находки",
                                        "Кем найдено ID сотрудника",
                                        "Наименование операции"

                                    ])
        csv_writer.writeheader()
        for office in data:
            for shortage in office.shortages:
                for shks_data in shortage.shks_data.shks:
                    found_info = shks_data.found_info
                    csv_writer.writerow({
                        "Office ID": office.office_id,
                        "Название офиса": office.office_name,
                        "Общая недостача офиса": office.office_amount,
                        "ID недостачи": shortage.shortage_id,
                        "Дата недостачи": shortage.create_dt,
                        "ID сотрудника": shortage.guilty_employee_id,
                        "Ф.И.О сотрудника": shortage.guilty_employee_name,
                        "Сумма недостачи": shortage.amount,
                        "Причина недостачи": shortage.comment,
                        "Status ID": shortage.status_id,
                        "is history exists": shortage.is_history_exist,
                        "Стоимость недостачи по ШК": shks_data.amount,
                        "Наименование товара": shks_data.item_name,
                        "URL на фото товара": shks_data.item_photo_url,
                        "URL товара в каталоге": shks_data.item_site_url,
                        "Новый ШК": shks_data.new_shk_id,
                        "Основной ШК": shks_data.shk_id,
                        "Найдено в офисе ID": found_info.found_in_office_id if found_info else None,
                        "Дата находки": found_info.found_at if found_info else None,
                        "Кем найдено ID сотрудника": found_info.found_by_employee_id if found_info else None,
                        "Наименование операции": found_info.operation if found_info else None
                    })

        csv_buffer.seek(0)
        buf = io.BytesIO()
        # extract csv-string, convert it to bytes and write to buffer
        buf.write(csv_buffer.getvalue().encode())
        buf.seek(0)
        # set a filename with file's extension
        buf.name = filename
        bytes_data = buf.getvalue()

        return bytes_data

    def save_csv_memory(self,
                        data: List[object],
                        filename: str,
                        column_names_mapping: Dict[str, str]
                        ):
        def process_operations(operations, date):
            for operation in operations:
                if isinstance(operation, Operation):
                    op_dict = operation.to_dict()
                else:
                    op_dict = operation
                op_dict['date'] = date
                filtered_item_dict = {csv_key: op_dict[obj_key] for obj_key, csv_key in column_names_mapping.items() if
                                      obj_key in op_dict}

                csv_writer.writerow(filtered_item_dict)
                logger.info(f'Записаны данные в строку файла - {filtered_item_dict}')
                # Рекурсивно обрабатываем вложенные операции, если они есть
                if 'grouped' in op_dict and op_dict['grouped']:
                    process_operations(op_dict['grouped'], date)

        # Получаем имена столбцов из словаря column_names_mapping
        column_names = list(column_names_mapping.values())
        # Объект в памяти для записи CSV
        csv_buffer = io.StringIO()
        # Создаем объект writer для записи в CSV
        csv_writer = csv.DictWriter(csv_buffer,
                                    fieldnames=column_names)
        csv_writer.writeheader()
        for item in data:
            item_dict = item.__dict__
            # обработка операций
            if 'operations' in item_dict and item_dict['operations']:
                process_operations(item_dict['operations'], item_dict['date'])

            else:

                filtered_item_dict = {csv_key: item_dict[obj_key] for obj_key, csv_key in column_names_mapping.items()
                                      if obj_key in item_dict}
                csv_writer.writerow(filtered_item_dict)
                logger.info(f'Записаны данные в строку файла - {filtered_item_dict}')

        csv_buffer.seek(0)
        buf = io.BytesIO()
        # extract csv-string, convert it to bytes and write to buffer
        buf.write(csv_buffer.getvalue().encode())
        buf.seek(0)

        # Устанавливаем имя файла с расширением
        buf.name = filename
        bytes_data = buf.getvalue()
        return bytes_data

    def save_to_csv(self,
                    data: List[object],
                    filename: str,
                    column_names_mapings: Dict[str, str],
                    oper_type_mapings: Dict[int, str] = None):
        data_to_save = [item.to_dict() for item in data]
        df = pd.DataFrame(data_to_save)
        # Проверка на наличие колонки operations
        if 'operations' in df.columns:
            df = df.explode('operations')
            # Разбиваем операции на отдельные колонки
            operations_df = pd.DataFrame(df['operations'].to_list())
            df = pd.concat(
                [df.drop(['operations'], axis=1).reset_index(drop=True), operations_df.reset_index(drop=True)], axis=1)

            if oper_type_mapings:
                df['oper_type'] = df['oper_type'].map(oper_type_mapings)

        if 'grouped' in df.columns:
            df = df.explode('grouped')
            grouped_df = pd.DataFrame(df['grouped'].dropna().to_list())
            df = pd.concat([df.drop(['grouped'], axis=1).reset_index(drop=True), grouped_df.reset_index(drop=True)],
                           axis=1)
        df.rename(columns=column_names_mapings, inplace=True)
        df.to_csv(filename, index=False)
        return None

    def safe_to_csv_operations(self,
                               data: List[OperationsByDate],
                               filename: str):
        data_to_save = []
        for item in data:
            for operation in item.operations:
                operations = [operation]
                operations.extend(operation.grouped)
                for op in operations:
                    data_to_save.append({
                        'date': item.date,
                        'oper_type': op.oper_type,
                        'oper_amount': op.oper_amount,
                        'comment': op.comment,
                        'grouped': None
                    })
        df = pd.DataFrame(data_to_save)

        df['comment'] = df['comment'].str.replace('\D+', '', regex=True)
        # rename

        "" ""
        df.rename(columns={
            'date': 'Дата',
            'oper_type': 'Тип операции',
            'oper_amount': 'Сумма',
            'comment': 'Комментарий',
        }, inplace=True)
        df.to_csv(filename, index=False)

    def save_to_csv_mananagers_operations(self, data: List[Dict], filename: str):
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = ['ID сотрудника', 'Фамилия', 'Имя', 'Отчество', 'Телефон', 'Дата трудоустройства', 'Рейтинг',
                          'Дата операции', 'Принято вещей', 'Возвраты', 'Возвраты (сумма)', 'Продажи',
                          'Продажи (сумма)',
                          'ШК офиса']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for employee in data:
                for operation in employee['operations']:
                    if operation and operation.date:
                        writer.writerow({
                            'ID сотрудника': employee['employee_id'],
                            'Фамилия': employee['last_name'],
                            'Имя': employee['first_name'],
                            'Отчество': employee['middle_name'],
                            'Телефон': employee['phone'],
                            'Дата трудоустройства': employee['create_date'],
                            'Рейтинг': employee['rating'],
                            'Дата операции': operation.date,
                            'Принято вещей': operation.on_place_cnt,
                            'Возвраты': operation.return_count,
                            'Возвраты (сумма)': operation.return_sum,
                            'Продажи': operation.sale_count,
                            'Продажи (сумма)': operation.sale_sum,
                            'ШК офиса': operation.barcode
                        })
                    else:
                        logger.info(f'Нет данных по операциям для сотрудника {employee["employee_id"]}')
