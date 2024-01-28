from telegram import Update
from telegram.ext import (CommandHandler, ContextTypes, ConversationHandler,
                          CallbackContext, ApplicationBuilder, MessageHandler, filters)
from bot.utility import validate_phone_number, validate_date
from parser.auth_api import AuthApi
from parser.auth_fr import Auth
from bot.logger import WBLogger
from parser.api import ParserWB
from parser.column_names import sale_data_column_names_mapping, operations_data_column_names_mapping, \
    shortages_data_column_names_mapping
from utils.env import TELEGRAM_TOKEN
from telegram import ReplyKeyboardMarkup
from bot.utility import restricted
import sys
import os


sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# set up logging
logger = WBLogger(__name__).get_logger()

GREET, GET_PHONE, GET_CODE, GET_START_DATE, GET_END_DATE = range(5)
SALES_REPORT, OPERATIONS_REPORT = range(6,8)


@restricted
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send a message when the command /start is issued.
    :param update: Update
    :param context: Context
    :return: int"""
    logger.info("Start begin")
    user = update.message.from_user
    await update.message.reply_text(f"Приветствую тебя {user.first_name} для продолжения необходимо авторизоваться в ЛК. Введите номер телефона привязанный к ЛК WB")
    return GET_PHONE


async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """ Состояние для получения номера телефона для авторизации, проверка наличия  токена,
     если токен валидный то получаем сессию для работы, если токена нет или просрочен то
     ожидаем от пользователя код из ЛК
     """
    phone_number = update.message.text
    phone = validate_phone_number(phone_number)
    if phone_number == "Отмена":
        await update.message.reply_text("Выберите действие или начните заново командой /start")
        return GREET
    if phone is None:
        await update.message.reply_text("Неверный номер телефона. Попробуйте еще раз")
        return GET_PHONE
    context.user_data['auth'] = Auth()
    context.user_data["phone"] = phone
    session = context.user_data['auth'].get_franchise_session(phone)
    auth_status = context.user_data['auth'].get_auth_status()
    if auth_status == "NEED_CODE":
        await update.message.reply_text(f"Отлично! Вы ввели номер {phone}, теперь введите код из ЛК")
        return GET_CODE
    elif auth_status == "ERROR":
        await update.message.reply_text("Слишком много запросов кода. Повторите запрос позднее")
        return ConversationHandler.END
    else:
        await update.message.reply_text(f"Вы уже авторизованы с номером {phone}!")
        context.user_data['session'] = session
        return await show_menu(update)


async def get_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """ Состояние для получения кода из ЛК от пользователя, далее отправка телефона и кода для получения
    новой сессии"""
    code = update.message.text
    if code == "Отмена":
        await update.message.reply_text("Выберите действие или начните заново командой /start")
        return GREET
    context.user_data['code'] = code
    phone = context.user_data['phone']
    session = context.user_data['auth'].connect_with_code(phone, code)
    logger.info(f'Session after connect with code  - {session}')
    if session:
        context.user_data['session'] = session
        await update.message.reply_text("Вы успешно авторизованы!")
        return await show_menu(update)
    else:
        await update.message.reply_text("Неверный код")
        return GET_PHONE


# async def sales_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     query = update.callback_query
#     await query.answer()
#     await query.edit_message_text("Введите дату начала отчета (в формате YYYY-MM-DD)")
#     return GET_START_DATE


async def get_start_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """ Состояние для получения от пользователя даты начала отчета"""
    start_date = update.message.text
    if start_date == "Отмена":
        await update.message.reply_text("Выберите действие или начните заново командой /start")
        return GREET
    start_date = validate_date(start_date)
    if start_date is None:
        await update.message.reply_text("Неверный формат даты. Попробуйте еще раз")
        return GET_START_DATE
    context.user_data['start_date'] = start_date
    await update.message.reply_text(f"Отлично! Дата начала отчета: {start_date}. "
                                    f"Теперь введите дату окончания отчета в формате YYYY-MM-DD)")
    return GET_END_DATE


async def get_end_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """ Состояние для получения даты окончания отчета """
    end_date = update.message.text
    if end_date == "Отмена":
        await update.message.reply_text("Выберите действие или начните заново командой /start")
        return GREET
    end_date = validate_date(end_date)
    if end_date is None:
        await update.message.reply_text("Неверный формат даты. Попробуйте еще раз")
        return GET_END_DATE
    context.user_data['end_date'] = end_date
    await update.message.reply_text("Отчет готовится. Пожалуйста, подождите")
    await send_report(update, context)
    return await show_menu(update)


async def send_report(update: Update, context: CallbackContext):
    """ Отправка отчета """
    logger.info("Begin to send report")
    session = context.user_data['session']
    logger.info(f"Session: {session}")
    parser = ParserWB(session)
    logger.info(" Begin to fetch offices")
    parser.fetch_offices()
    logger.info(" End of fetch offices")
    logger.info(" Begin to fetch employees")
    parser.fetch_employees()
    logger.info(" End of fetch employees")
    date_from_str = context.user_data['start_date'].strftime('%Y-%m-%d')
    logger.info(f'Type of date from - {type(date_from_str)}')
    date_to_str = context.user_data['end_date'].strftime('%Y-%m-%d')
    report_type = context.user_data.get('report_type')
    filename = ''
    if report_type == "sales":
        logger.info("Begin to fetch sales data")
        data = parser.fetch_sales_data(date_from=date_from_str, date_to=date_to_str)
        logger.info(f"Get data - {data}")
        filename = f"sales_data/sales_data_{date_from_str} - {date_to_str} - {context.user_data['phone']}.csv"
        file = parser.save_csv_memory(data=data, filename=filename, column_names_mapping=sale_data_column_names_mapping)

    elif report_type == "shortages":
        logger.info("Begin to fetch shortages")
        data = parser.fetch_shortages_data(date_from=date_from_str, date_to=date_to_str)
        logger.info(f"Get data - {data}")
        filename = f"shortages_{date_from_str} - {date_to_str} - {context.user_data['phone']}.csv"
        file = parser.generate_csv_io(data=data, filename=filename)

    elif report_type == "operations":
        logger.info("Begin to fetch operations data")
        operations_data = parser.fetch_operations_data(date_from=date_from_str, date_to=date_to_str)
        filename = f"operations_data/operations_data_{date_from_str} - {date_to_str} - {context.user_data['phone']}.csv"
        file = parser.save_csv_memory(data=operations_data,
                                      filename=filename,
                                      column_names_mapping=operations_data_column_names_mapping)
        # parser.safe_to_csv_operations(data=operations_data, filename=filename)
    elif report_type == "managers":
        logger.info(f'Begin to fetch managers data')
        managers_data = parser.fetch_employee_data(date_from=date_from_str, date_to=date_to_str)
        api_parser = AuthApi()
        api_parser.get_token()
        for employee in managers_data:
            phone_number = employee.get('phone')
            logger.info(f'Phone number - {phone_number}')
            api_data = api_parser.get_employee_data(phone_number)
            logger.info(f'API data - {api_data}')
            if api_data:
                for day in api_data:
                    api_date = day.get('date_created').split('T')[0]  # получаем дату записи входа
                    api_barcode = day.get('barcode') # получаем ШК офиса
                    for operation in employee.get('operations'):
                        operation_date = operation.date
                        if api_date == operation_date:
                            operation.barcode = api_barcode
        filename = f"operations_data/manager_operations_data_{date_from_str} - {date_to_str} - {context.user_data['phone']}.csv"
        parser.save_to_csv_mananagers_operations(data=managers_data, filename=filename)
    await update.message.reply_text("Отчет сформирован")
    # with open(filename, 'rb') as file:
    #     await context.bot.send_document(chat_id=update.effective_chat.id, document=file, filename=filename)
    await context.bot.send_document(chat_id=update.effective_chat.id, document=file, filename=filename)
    await update.message.reply_text("Отчет отправлен")
    return GREET


async def show_menu(update: Update) -> int:
    keyboard = [
        ["Отчет по продажам"],
        ["Отчет по недостачам"],
        ["Отчет по операциям"],
        ["Отчет по менеджерам"],
        ["Отмена"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Выберите действие", reply_markup=reply_markup)
    return GREET


async def choose_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_choice = update.message.text
    if user_choice == "Отчет по продажам":
        context.user_data['report_type'] = 'sales'
    elif user_choice == "Отчет по недостачам":
        context.user_data['report_type'] = 'shortages'
    elif user_choice == "Отчет по операциям":
        context.user_data['report_type'] = 'operations'
    elif user_choice == "Отчет по менеджерам":
        context.user_data['report_type'] = 'managers'
    elif user_choice == "Отмена":
        await update.message.reply_text("Выберите действие или начните заново командой /start")
        return GREET
    else:
        await update.message.reply_text("Неизвестный выбор. Пожалуйста, попробуйте снова")
        return GREET

    await update.message.reply_text("Введите дату начала отчета (в формате YYYY-MM-DD)")
    return GET_START_DATE


async def get_plugin_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pass


def main() -> None:
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            GET_PHONE: [MessageHandler(filters=filters.TEXT & ~filters.COMMAND, callback=get_phone)],
            GET_CODE: [MessageHandler(filters=filters.TEXT & ~filters.COMMAND, callback=get_code)],
            GREET: [MessageHandler(filters=filters.TEXT & ~filters.COMMAND, callback=choose_report)],
            GET_START_DATE: [MessageHandler(filters=filters.TEXT & ~filters.COMMAND, callback=get_start_date)],
            GET_END_DATE: [MessageHandler(filters=filters.TEXT & ~filters.COMMAND, callback=get_end_date)]
        },
        fallbacks=[CommandHandler("start", start)],
        per_user=True
    )

    application.add_handler(conv_handler)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()


