import requests
from datetime import datetime, timedelta
from parser.api import ParserWB
from parser.auth_fr import Auth
from parser.auth_api import AuthApi


def main():
    auth = Auth()
    # Авторизация по телефону
    phone_number = input("Введите номер телефона для авторизации: ")
    session = auth.get_franchise_session(phone_number)

    # Если требуется код доступа
    if auth.get_auth_status() == "NEED_CODE":
        access_code = input("Введите полученный код доступа: ")
        session = auth.connect_with_code(phone_number, access_code)
        print(session)

    # Создаем экземпляр парсера с авторизованной сессией
    parser = ParserWB(session)

    # Получаем всех сотрудников
    parser.fetch_employees()

    # Получаем операции сотрудников за последние 30 дней
    date_from = datetime.now() - timedelta(days=5)
    date_to = datetime.now()
    parser.fetch_employees()
    operations_data = parser.fetch_employee_data(date_from, date_to)
    api_parser = AuthApi()
    api_parser.get_token()
    for employee in operations_data:
        phone_number = employee.get('phone')
        api_data = api_parser.get_employee_data(phone_number)
        if api_data:
            for day in api_data:
                print('API is not None')
                api_date = day.get('date_created').split('T')[0]  # получаем только дату записи входа
                api_barcode = day.get('barcode')  # получаем ШК офиса
                # перебираем все операции сотрудника по датам
                for operation in employee.get('operations'):
                    operation_date = operation.date
                    if api_date == operation_date:
                        operation.barcode = api_barcode
                # employee['operations'] = [
                #     operation.set_barcode(api_barcode)
                #     if operation and operation.date == api_date
                #     else operation
                #     for operation in employee.get('operations')
                # ]

    print('Begin to save to csv')
    parser.save_to_csv_mananagers_operations(data=operations_data, filename=f"operations_data_{date_from} - {date_to} - {phone_number}.csv",)


if __name__ == '__main__':
    main()

