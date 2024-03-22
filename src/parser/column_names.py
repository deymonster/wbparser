
sale_data_column_names_mapping = {
    'office_id': 'ID офиса',
    'name': 'Название офиса',
    'date': 'Дата',
    'sale_count': 'Кол-во продаж',
    'return_count': 'Кол-во возвратов',
    'sale_sum': 'Продажи РУБ',
    'return_sum': 'Возвраты РУБ',
    'proceeds': 'Объем продаж РУБ',
    'amount': 'Вознаграждение РУБ',
    'bags_sum': 'Пакеты РУБ',
    'office_rating': 'Рейтинг ПВЗ',
    'percent': 'Тариф (ставка грейда)',
    'office_rating_sum': 'Сумма рейтинга',
    'supplier_return_sum': 'Сумма возвратов поставщика',
    'office_speed_sum': 'Скорость'

}


operations_data_column_names_mapping = {
    'date': 'Дата',
    'oper_type': 'Тип операции',
    'oper_amount': 'Сумма операции',
    'comment': 'ШК',
}

shortages_data_column_names_mapping = {
    "office_id": "Office ID",
    "office_name": "Название офиса",
    "office_amount": "Общая недостача офиса",
    "shortage_id": "ID недостачи",
    "create_dt": "Дата недостачи",
    "guilty_employee_id": "ID сотрудника",
    "guilty_employee_name": "Ф.И.О сотрудника",
    "amount": "Сумма недостачи",
    "comment": "Причина недостачи",
    "status_id": "Status ID",
    "is_history_exist": "is history exists - история?"
}



oper_type_mapping= {
    1: 'Недостача',
    2: 'Премирование',
    3: 'Депремирование',
    4: 'Брак ШК/Коллективная ответственность',
    5: 'Вывод средств на реквизиты',
    6: 'Вознаграждения по продажам'
}
