from parser.api import ParserWB
from parser.auth_fr import Auth
from parser.column_names import sale_data_column_names_mapping
import argparse
import logging
import schedule
import time
import threading


logging.basicConfig(level=logging.INFO)

# date_from="2023-06-01"
# date_to="2023-06-30"

args_parser = argparse.ArgumentParser(description='WB parser')
# args_parser.add_argument('--auth', action='store_true', help='Auth in WB LK')
# args_parser.add_argument('--report', action='store_true', help='Parse report')
args_parser.add_argument('--phone', type=str, help='Phone number for auth in Franchise LK')
args_parser.add_argument('--managers_operations', action='store_true', help='Parse manager operations')
args_parser.add_argument('--operations', action='store_true', help='Parse operations data')
args_parser.add_argument('--date_from', type=str, help='Date from in format YYYY-MM-DD')
args_parser.add_argument('--date_to', type=str, help='Date to in format YYYY-MM-DD')



def main():
    """ Main function
    В зависимости от переданных аргументов запускает разные функции
    ожидает следующие обязательные аргументы:
    --phone - номер телефона для авторизации в ЛК ВБ
    --sales - запуск парсинга данных по продажам
    --operations - запуск парсинга данных по операциям
    --date_from - дата начала периода в формате YYYY-MM-DD
    --date_to - дата окончания периода в формате YYYY-MM-DD
    данные сохраняются в csv файлы в корне проекта
    """
    args = args_parser.parse_args()

    if not args.date_from or not args.date_to:
        print('Please specify date_from and date_to')
        return
    all_sales_data = []
    auth = Auth()
    session = auth.get_franchise_session(args.phone)
    if session is None:
        logging.error(f"Failed to get franchise session")
        return
    parser = ParserWB(session=session)
    # if args.sales:
    #     run_sales_report(args)
    #     pass
        # logging.info(f"Fetching sales data")
        # try:
        #     parser.fetch_offices()
        #     logging.info(f"Got offices: {parser.offices}")
        #     for office in parser.offices:
        #         logging.info(f"Fetching data for office: Name - {office.name}, ID-  {office.id}")
        #         try:
        #             sales_data = parser.fetch_sales_data(office_id=office.id, date_from=args.date_from, date_to=args.date_to)
        #             if sales_data is not None:
        #                 logging.info(f"Got sales data for office: Name - {office.name}, ID-  {office.id}")
        #                 all_sales_data.extend(sales_data)
        #             else:
        #                 logging.error(f"Failed to get sales data for office: Name - {office.name}, ID-  {office.id}")
        #         except Exception as e:
        #             logging.error(f"Failed to get sales data for office: Name - {office.name}, ID-  {office.id}: {e}")
        #     parser.save_to_csv(data=all_sales_data,
        #                        filename=f"sales_data_{args.date_from} - {args.date_to}.csv",
        #                        column_names_mapings=sale_data_column_names_mapping)
        #
        # except Exception as e:
        #     logging.error(f"Failed to get sales data: {e}")

    if args.operations:
        run_operations_report(args, session)
        # logging.info(f"Fetching operations data")
        # try:
        #     operations_data = parser.fetch_operations_data(date_from=args.date_from, date_to=args.date_to)
        #     parser.safe_to_csv_operations(data=operations_data,
        #                                   filename=f"operations_data_{datetime.now().strftime('%Y-%m-%d')}.csv",
        #                                   )
        # except Exception as e:
        #     logging.error(f"Failed to get operations data: {e}")
    if args.managers_operations:
        logging.info(f'Begin to fetch managers data')
        eployees = parser.fetch_eployees()
        logging.info(f'Got employees: {eployees}')


def run_sales_report(args):
    all_sales_data = []
    auth = Auth()
    session = auth.get_franchise_session(args.phone)
    if session is None:
        logging.error(f"Failed to get franchise session")
        return
    parser = ParserWB(session=session)
    if args.sales:
        logging.info(f"Fetching sales data")
        try:
            parser.fetch_offices()
            logging.info(f"Got offices: {parser.offices}")
            for office in parser.offices:
                logging.info(f"Fetching data for office: Name - {office.name}, ID-  {office.id}")
                try:
                    sales_data = parser.fetch_sales_data(office_id=office.id, date_from=args.date_from,
                                                         date_to=args.date_to)
                    if sales_data is not None:
                        logging.info(f"Got sales data for office: Name - {office.name}, ID-  {office.id}")
                        all_sales_data.extend(sales_data)
                    else:
                        logging.error(f"Failed to get sales data for office: Name - {office.name}, ID-  {office.id}")
                except Exception as e:
                    logging.error(f"Failed to get sales data for office: Name - {office.name}, ID-  {office.id}: {e}")
            parser.save_to_csv(data=all_sales_data,
                               filename=f"sales_data_{args.date_from} - {args.date_to} - {args.phone}.csv",
                               column_names_mapings=sale_data_column_names_mapping)

        except Exception as e:
            logging.error(f"Failed to get sales data: {e}")


def run_operations_report(args, session):
    if session is None:
        logging.error(f"Failed to get franchise session")
        return
    parser = ParserWB(session=session)
    logging.info(f"Fetching operations data")
    try:
        operations_data = parser.fetch_operations_data(date_from=args.date_from, date_to=args.date_to)
        parser.safe_to_csv_operations(data=operations_data,
                                      filename=f"operations_data_{args.date_from} - {args.date_to} - {args.phone}.csv",
                                      )
    except Exception as e:
        logging.error(f"Failed to get operations data: {e}")


if __name__ == '__main__':
    main()


