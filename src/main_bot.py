import itertools

from warnings import filterwarnings

from pydantic import ValidationError
from telegram.warnings import PTBUserWarning
from telegram.ext import CallbackQueryHandler

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    CallbackContext,
    ApplicationBuilder,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from bot.utility import validate_phone_number, validate_date
from db.db import get_db
from parser.auth_api import AuthApi
from parser.auth_fr import Auth
from bot.logger import WBLogger
from parser.api import ParserWB, OfficeRates
from parser.column_names import (
    sale_data_column_names_mapping,
    operations_data_column_names_mapping,
    office_rates_column_names_mapping,
)
from parser.constants import field_names
from parser.schemas import OfficeModel, OfficeRatesModel
from utils.env import TELEGRAM_TOKEN, TELEGRAM_TOKEN2
from telegram import ReplyKeyboardMarkup
from bot.utility import restricted
import sys
import os

from parser.service import (
    get_all_offices,
    get_office_info,
    delete_office,
    update_office_field,
    add_office,
    create_or_update_ratings,
)

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

# set up logging
logger = WBLogger(__name__).get_logger()

# remove warning
filterwarnings(
    action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning
)

GREET, GET_PHONE, GET_CODE, GET_START_DATE, GET_END_DATE, GET_OFFICE_RATINGS_REPORT = (
    range(6)
)


OFFICES_MENU, VIEW_OFFICES, ADD_OFFICE, SELECT_OFFICE, EDIT_OFFICE, DELETE_OFFICE = (
    range(7, 13)
)


# Shortcut for ConversationHandler.END
END = ConversationHandler.END

# Pagination
current_page = 0
items_per_page = 10

# Constants for bot


@restricted
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send a message when the command /start is issued.


    :param update: Update
    :param context: Context
    :return: int"""
    logger.info("Start begin")
    user = update.message.from_user
    await update.message.reply_text(
        f"Приветствую тебя {user.first_name} "
        f"для продолжения необходимо авторизоваться в ЛК. "
        f"Введите номер телефона привязанный к ЛК WB"
    )
    return GET_PHONE


@restricted
async def offices(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Команда для работы с офисами"""

    context.user_data.clear()
    text = (
        "Вы можете просмотреть, изменить данные по офисам или удалить офис или завершить диалог"
        "\nДля отмены просто введите команду /cancel."
    )
    buttons = [
        [
            InlineKeyboardButton(
                text="Просмотреть офисы", callback_data=str(VIEW_OFFICES)
            ),
            InlineKeyboardButton(text="Добавить офис", callback_data=str(ADD_OFFICE)),
        ]
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    query = update.callback_query
    if query:
        # Если да, то редактируем сообщение
        await query.edit_message_text(text=text, reply_markup=keyboard)
    else:
        # Если нет, то отправляем новое сообщение
        await update.message.reply_text(text=text, reply_markup=keyboard)

    return OFFICES_MENU


# Просмотр офисов
async def view_offices(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("View offices")
    query = update.callback_query
    if query:
        await query.answer()
    current_page = context.user_data.get("current_page", 0)
    with get_db() as db:
        office_list = get_all_offices(db_session=db)
        total_offices = len(office_list)
        pages = total_offices // items_per_page + (total_offices % items_per_page > 0)
        offices = office_list[
            current_page * items_per_page : (current_page + 1) * items_per_page
        ]

    if not offices:
        text = "Список офисов пуст"
        if query:
            await query.answer(text, show_alert=True)
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=text)
        return OFFICES_MENU

    keyboard_buttons = []
    for office in offices:
        button_text = office["name"]
        callback_data = f"office_{office['office_id']}"
        keyboard_buttons.append(
            [InlineKeyboardButton(text=button_text, callback_data=callback_data)]
        )

    # Добавляем кнопки пагинации в отдельный ряд
    pagination_buttons = []
    if current_page > 0:
        pagination_buttons.append(
            InlineKeyboardButton("Назад", callback_data="prev_page")
        )
    if current_page < pages - 1:
        pagination_buttons.append(
            InlineKeyboardButton("Вперед", callback_data="next_page")
        )
    if pagination_buttons:
        keyboard_buttons.append(pagination_buttons)

    keyboard_buttons.append(
        [InlineKeyboardButton("В начальное меню", callback_data="return_to_start")]
    )

    reply_markup = InlineKeyboardMarkup(keyboard_buttons)
    message_text = "Список офисов:"
    if query:
        await query.edit_message_text(text=message_text, reply_markup=reply_markup)
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message_text,
            reply_markup=reply_markup,
        )

    return VIEW_OFFICES


# Обработчики для кнопок пагинации


async def previous_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["current_page"] = max(
        context.user_data.get("current_page", 0) - 1, 0
    )
    await view_offices(update, context)
    return VIEW_OFFICES


async def next_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["current_page"] = context.user_data.get("current_page", 0) + 1
    await view_offices(update, context)
    return VIEW_OFFICES


async def return_to_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["current_page"] = 0
    await offices(update, context)
    return OFFICES_MENU


async def edit_office_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    callback_data = query.data
    _, *field_parts, office_id = callback_data.split("_")
    field = "_".join(field_parts)
    # Сохраняем информацию о том, какое поле и офис нужно обновить, в context.user_data
    context.user_data["edit_office"] = {"office_id": office_id, "field": field}
    # Запрашиваем у пользователя новое значение для поля
    field = field_names.get(field, field)
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text=f"Введите новое значение для {field}:"
    )
    return EDIT_OFFICE


async def save_office_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    office_id = context.user_data["edit_office"]["office_id"]
    field = context.user_data["edit_office"]["field"]

    # Обновляем поле в базе данных
    with get_db() as db:
        success = update_office_field(db, office_id, field, text)
    if success:
        field_name = field_names.get(field, field)
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text=f"Поле {field_name} было обновлено."
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Произошла ошибка при обновлении поля.",
        )
    await select_office(update, context, office_id)
    return SELECT_OFFICE


# Просмотр информации по офису
async def select_office(
    update: Update, context: ContextTypes.DEFAULT_TYPE, office_id=None
):
    query = update.callback_query
    logger.info("Begin select office ")
    if query:
        callback_data = query.data
        if not office_id and callback_data.startswith("office_"):
            office_id = callback_data.split("_")[1]
        await query.answer()
    else:
        if not office_id:
            logger.error("No office_id provided to select_office function.")
            return
    with get_db() as db:
        office_info = get_office_info(db, office_id)

        if office_info:
            message_texts = [
                f"Информация по офису {office_id} - {office_info['name']}:\n"
            ]

            for field, value in office_info.items():
                if field == "id":
                    continue
                field_name = field_names.get(field, field)
                message_texts.append(f"{field_name}: {value}")
            edit_buttons = []
            for field in office_info.keys():
                if field == "id":
                    continue
                button_text = f"Изменить {field_names.get(field, field)}"
                edit_buttons.append(
                    InlineKeyboardButton(
                        button_text, callback_data=f"edit_{field}_{office_id}"
                    )
                )

            keyboard = [edit_buttons[i : i + 2] for i in range(0, len(edit_buttons), 2)]
            keyboard.append(
                [
                    InlineKeyboardButton(
                        "Назад", callback_data=f"back_to_view_offices"
                    ),
                    InlineKeyboardButton(
                        "Удалить офис", callback_data=f"delete_{office_id}"
                    ),
                ]
            )
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="\n".join(message_texts),
                reply_markup=reply_markup,
            )

        else:
            message_text = ["Неизвестный запрос"]
            await context.bot.send_message(
                chat_id=update.effective_chat.id, text=message_text
            )
    return SELECT_OFFICE


# Удаление офиса
async def confirm_delete_office(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик  подтверждения удаления офиса"""

    query = update.callback_query
    await query.answer()
    logger.info("Confirm delete office called")
    office_id = query.data.split("_")[1]
    confirm_text = f"Вы уверены, что хотите удалить офис с ID {office_id}?"
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "Да, удалить", callback_data=f"perform_delete_{office_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    "Отмена", callback_data=f"cancel_delete_{office_id}"
                )
            ],
        ]
    )
    await query.edit_message_text(text=confirm_text, reply_markup=keyboard)

    return DELETE_OFFICE


async def perform_delete_office(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатия кнопки Да, удалить"""

    logger.info("Perform Delete Office")
    query = update.callback_query
    callback_data = update.callback_query.data
    await query.answer()
    with get_db() as db:
        if callback_data.startswith("perform_delete_"):
            office_id = callback_data.split("_")[2]
            success = delete_office(db, office_id)
            if success:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"Офис с ID {office_id} был удален.",
                )
                await view_offices(update, context)
                return VIEW_OFFICES
            else:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"Произошла ошибка при удалении офиса с ID {office_id}.",
                )
                return SELECT_OFFICE
        else:
            message_text = ["Неизвестный запрос"]
            await context.bot.send_message(
                chat_id=update.effective_chat.id, text=message_text
            )
            return SELECT_OFFICE


async def cancel_delete_office(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    office_id = query.data.split("_")[2]
    await select_office(update, context, office_id)
    return SELECT_OFFICE


async def add_office_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик для добавления нового офиса"""
    query = update.callback_query
    await query.answer()
    logger.info("ADD office handler begin")
    instructions = (
        "Введите данные о новом офисе. Каждый параметр должен быть на новой строке.\n\n"
        "Формат:\n"
        "Office ID\n"
        "Название ПВЗ\n"
        "Компания\n"
        "РФ\n"
        "Площадь\n"
        "Аренда\n"
        "Ставка оплаты\n"
        "Минимальная оплата\n"
        "Интернет\n"
        "Администрация\n"
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=instructions)
    logger.info("ADD office handler end")
    return ADD_OFFICE


async def save_new_office(update: Update, context: ContextTypes.DEFAULT_TYPE):

    logger.info("Save new office begin")
    # Получаем данные от пользователя
    office_data_text = update.message.text.strip()
    logger.info(f"office_data_text - {office_data_text}")
    office_data_lines = office_data_text.split("\n")
    logger.info(f"office_data_lines - {office_data_lines}")
    if len(office_data_lines) < 10:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Вы ввели недостаточно данных. Пожалуйста, введите информацию по каждому параметру на новой строке.",
        )
        return ADD_OFFICE
    try:
        # Создаем экземпляр модели OfficeModel из введенных данных
        office_data = OfficeModel(
            office_id=office_data_lines[0],
            name=office_data_lines[1],
            company=office_data_lines[2],
            manager=office_data_lines[3],
            office_area=office_data_lines[4],
            rent=office_data_lines[5],
            salary_rate=office_data_lines[6],
            min_wage=office_data_lines[7],
            internet=office_data_lines[8],
            administration=office_data_lines[9],
        )
    except ValidationError as e:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text=f"Ошибка в введенных данных: {e}"
        )
        return ADD_OFFICE
    with get_db() as db:
        success = add_office(db, office_data.dict())
    if success:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text="Новый офис успешно добавлен."
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Произошла ошибка при добавлении офиса.",
        )
    await view_offices(update, context)
    return VIEW_OFFICES


#################################
### Работа с API WB
async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Состояние для получения номера телефона
    для авторизации, проверка наличия  токена,
     если токен валидный то получаем сессию для работы,
     если токена нет или просрочен то
     ожидаем от пользователя код из ЛК
    """
    phone_number = update.message.text
    phone = validate_phone_number(phone_number)
    if phone_number == "Отмена":
        await update.message.reply_text(
            "Выберите действие или начните заново командой /start"
        )
        return GREET
    if phone is None:
        await update.message.reply_text("Неверный номер телефона. Попробуйте еще раз")
        return GET_PHONE
    context.user_data["auth"] = Auth()
    context.user_data["phone"] = phone
    session = context.user_data["auth"].get_franchise_session(phone)
    auth_status = context.user_data["auth"].get_auth_status()
    if auth_status == "NEED_CODE":
        await update.message.reply_text(
            f"Отлично! Вы ввели номер {phone}, теперь введите код из ЛК"
        )
        return GET_CODE
    elif auth_status == "ERROR":
        await update.message.reply_text(
            "Слишком много запросов кода. Повторите запрос позднее"
        )
        return ConversationHandler.END
    else:
        await update.message.reply_text(f"Вы уже авторизованы с номером {phone}!")
        context.user_data["session"] = session
        return await show_menu(update)


async def get_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Состояние для получения кода из ЛК от пользователя,
    далее отправка телефона и кода для получения
    новой сессии"""
    code = update.message.text
    if code == "Отмена":
        await update.message.reply_text(
            "Выберите действие или начните заново командой /start"
        )
        return GREET
    context.user_data["code"] = code
    phone = context.user_data["phone"]
    session = context.user_data["auth"].connect_with_code(phone, code)
    if session:
        context.user_data["session"] = session
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
    """Состояние для получения от пользователя даты начала отчета"""
    start_date = update.message.text
    if start_date == "Отмена":
        await update.message.reply_text(
            "Выберите действие или начните заново командой /start"
        )
        return GREET
    start_date = validate_date(start_date)
    if start_date is None:
        await update.message.reply_text("Неверный формат даты. Попробуйте еще раз")
        return GET_START_DATE
    context.user_data["start_date"] = start_date
    await update.message.reply_text(
        f"Отлично! Дата начала отчета: {start_date}. "
        f"Теперь введите дату окончания отчета в формате YYYY-MM-DD)"
    )
    return GET_END_DATE


async def get_end_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Состояние для получения даты окончания отчета"""
    end_date = update.message.text
    if end_date == "Отмена":
        await update.message.reply_text(
            "Выберите действие или начните заново командой /start"
        )
        return GREET
    end_date = validate_date(end_date)
    if end_date is None:
        await update.message.reply_text("Неверный формат даты. Попробуйте еще раз")
        return GET_END_DATE
    context.user_data["end_date"] = end_date
    await update.message.reply_text("Отчет готовится. Пожалуйста, подождите")
    await send_report(update, context)
    return await show_menu(update)


async def send_report(update: Update, context: CallbackContext):
    """Отправка отчета"""
    logger.info("Begin to send report")
    session = context.user_data["session"]
    logger.info(f"Session: {session}")
    parser = ParserWB(session)
    logger.info(" Begin to fetch offices")
    parser.fetch_offices()
    logger.info(" End of fetch offices")
    logger.info(" Begin to fetch employees")
    parser.fetch_employees()
    logger.info(" End of fetch employees")
    date_from_str = context.user_data["start_date"].strftime("%Y-%m-%d")
    logger.info(f"Type of date from - {type(date_from_str)}")
    date_to_str = context.user_data["end_date"].strftime("%Y-%m-%d")
    report_type = context.user_data.get("report_type")
    file: bytes = b""
    filename = ""
    if report_type == "sales":
        logger.info("Begin to fetch sales data")
        data = parser.fetch_sales_data(date_from=date_from_str, date_to=date_to_str)
        logger.info(f"Get data - {data}")
        filename = f"sales_data/sales_data_{date_from_str} - {date_to_str} - {context.user_data['phone']}.csv"
        file = parser.save_csv_memory(
            data=data,
            filename=filename,
            column_names_mapping=sale_data_column_names_mapping,
        )

    elif report_type == "shortages":
        logger.info("Begin to fetch shortages")
        data = parser.fetch_shortages_data(date_from=date_from_str, date_to=date_to_str)
        logger.info(f"Get data - {data}")
        filename = f"shortages_{date_from_str} - {date_to_str} - {context.user_data['phone']}.csv"
        file = parser.generate_csv_io(data=data, filename=filename)

    elif report_type == "operations":
        logger.info("Begin to fetch operations data")
        operations_data = parser.fetch_operations_data(
            date_from=date_from_str, date_to=date_to_str
        )
        filename = (
            f"operations_data/operations_data_{date_from_str} "
            f"- {date_to_str} - {context.user_data['phone']}.csv"
        )
        file = parser.save_csv_memory(
            data=operations_data,
            filename=filename,
            column_names_mapping=operations_data_column_names_mapping,
        )
        # parser.safe_to_csv_operations(data=operations_data, filename=filename)
    elif report_type == "managers":
        logger.info(f"Begin to fetch managers data")
        managers_data = parser.fetch_employee_data(
            date_from=date_from_str, date_to=date_to_str
        )
        api_parser = AuthApi()
        api_parser.get_token()
        for employee in managers_data:
            phone_number = employee.get("phone")
            logger.info(f"Phone number - {phone_number}")
            api_data = api_parser.get_employee_data(phone_number)
            logger.info(f"API data - {api_data}")
            if api_data:
                for day in api_data:
                    # дата записи входа
                    api_date = day.get("date_created").split("T")[0]
                    # получаем ШК офиса
                    api_barcode = day.get("barcode")
                    for operation in employee.get("operations"):
                        operation_date = operation.date
                        if api_date == operation_date:
                            operation.barcode = api_barcode
        filename = (
            f"operations_data/manager_operations_data_{date_from_str} "
            f"- {date_to_str} - {context.user_data['phone']}.csv"
        )
        parser.save_to_csv_mananagers_operations(data=managers_data, filename=filename)
    await update.message.reply_text("Отчет сформирован")
    # with open(filename, 'rb') as file:
    #     await context.bot.send_document(chat_id=update.effective_chat.id, document=file, filename=filename)
    await context.bot.send_document(
        chat_id=update.effective_chat.id, document=file, filename=filename
    )
    await update.message.reply_text("Отчет отправлен")
    return GREET


async def show_menu(update: Update) -> int:
    keyboard = [
        ["Отчет по продажам"],
        ["Отчет по недостачам"],
        ["Отчет по операциям"],
        ["Отчет по менеджерам"],
        ["Отчет по показателям офисов"],
        ["Отмена"],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Выберите действие", reply_markup=reply_markup)
    return GREET


async def choose_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_choice = update.message.text
    if user_choice == "Отчет по продажам":
        context.user_data["report_type"] = "sales"
    elif user_choice == "Отчет по недостачам":
        context.user_data["report_type"] = "shortages"
    elif user_choice == "Отчет по операциям":
        context.user_data["report_type"] = "operations"
    elif user_choice == "Отчет по менеджерам":
        context.user_data["report_type"] = "managers"
    elif user_choice == "Отчет по показателям офисов":
        await update.message.reply_text(
            "Отчет по показателям офисов готовится. Пожалуйста, подождите."
        )
        await send_office_ratings_report(update, context)
        return GREET
    elif user_choice == "Отмена":
        await update.message.reply_text(
            "Выберите действие или начните заново командой /start"
        )
        return GREET
    else:
        await update.message.reply_text(
            "Неизвестный выбор. Пожалуйста, попробуйте снова"
        )
        return GREET

    await update.message.reply_text("Введите дату начала отчета (в формате YYYY-MM-DD)")
    return GET_START_DATE


async def send_office_ratings_report(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Отчет по показателям офисов"""
    logger.info("Begin to send office ratings report")
    session = context.user_data["session"]
    parser = ParserWB(session)
    logger.info("Begin to fetch office ratings data")
    parser.fetch_offices()
    office_ids = parser.get_offices_ids()
    parser.fetch_offices_rates(office_ids)
    updated_office_rate_instances = []
    for office_rate in parser.offices_rates:
        office_id = office_rate.office_id
        office = next(
            (office for office in parser.offices if office.id == office_id), None
        )
        if office:
            office_name = office.name
            updated_office_rate_instance = OfficeRatesModel(
                office_id=office_id,
                office_name=office_name,
                avg_rate=office_rate.avg_rate,
                avg_region_rate=office_rate.avg_region_rate,
                avg_hours=office_rate.avg_hours,
                avg_hours_by_region=office_rate.avg_hours_by_region,
                inbox_count=office_rate.inbox_count,
                limit_delivery=office_rate.limit_delivery,
                total_count=office_rate.total_count,
                workload=office_rate.workload,
            )
            updated_office_rate_instances.append(updated_office_rate_instance)
        else:
            logger.warning(f"Офис с ID {office_id} не найден")
    filename = "Office_Ratings.csv"
    file = parser.save_csv_memory(
        data=updated_office_rate_instances,
        filename=filename,
        column_names_mapping=office_rates_column_names_mapping,
    )

    with get_db() as db:
        create_or_update_ratings(
            list_in=updated_office_rate_instances,
            index_elements=["office_id"],
            on_conflict_set={
                "avg_rate",
                "avg_region_rate",
                "avg_hours",
                "avg_hours_by_region",
                "inbox_count",
                "limit_delivery",
                "total_count",
                "workload",
            },
            db=db,
        )
    await update.message.reply_text("Отчет сформирован")
    await context.bot.send_document(
        chat_id=update.effective_chat.id, document=file, filename=filename
    )
    await update.message.reply_text("Отчет отправлен и записан в БД")

    return await show_menu(update)


async def get_plugin_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pass


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена и окончание диалога"""

    await update.message.reply_text(
        "Вы отменили выбор, для повтора можете выбрать команду /start или /offices",
        reply_markup=ReplyKeyboardRemove(),
    )

    return ConversationHandler.END


def main() -> None:
    application = ApplicationBuilder().token(TELEGRAM_TOKEN2).build()
    logger.info("Main function")
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            GET_PHONE: [
                MessageHandler(
                    filters=filters.TEXT & ~filters.COMMAND, callback=get_phone
                )
            ],
            GET_CODE: [
                MessageHandler(
                    filters=filters.TEXT & ~filters.COMMAND, callback=get_code
                )
            ],
            GREET: [
                MessageHandler(
                    filters=filters.TEXT & ~filters.COMMAND, callback=choose_report
                )
            ],
            GET_START_DATE: [
                MessageHandler(
                    filters=filters.TEXT & ~filters.COMMAND, callback=get_start_date
                )
            ],
            GET_END_DATE: [
                MessageHandler(
                    filters=filters.TEXT & ~filters.COMMAND, callback=get_end_date
                )
            ],
            GET_OFFICE_RATINGS_REPORT: [
                MessageHandler(
                    filters=filters.TEXT & ~filters.COMMAND,
                    callback=send_office_ratings_report,
                )
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
        per_user=True,
    )
    application.add_handler(conv_handler)
    # Обработчик команды /offices
    conv_handler_office = ConversationHandler(
        entry_points=[CommandHandler("offices", offices)],
        states={
            OFFICES_MENU: [
                CallbackQueryHandler(
                    view_offices, pattern="^" + str(VIEW_OFFICES) + "$"
                ),
                CallbackQueryHandler(
                    add_office_handler, pattern="^" + str(ADD_OFFICE) + "$"
                ),
            ],
            VIEW_OFFICES: [
                CallbackQueryHandler(select_office, pattern="^office_"),
                CallbackQueryHandler(previous_page, pattern="^prev_page$"),
                CallbackQueryHandler(next_page, pattern="^next_page$"),
                CallbackQueryHandler(return_to_start, pattern="^return_to_start$"),
            ],
            ADD_OFFICE: [
                MessageHandler(
                    filters=filters.TEXT & ~filters.COMMAND, callback=save_new_office
                ),
            ],
            SELECT_OFFICE: [
                CallbackQueryHandler(view_offices, pattern="^back_to_view_offices$"),
                CallbackQueryHandler(confirm_delete_office, pattern="^delete_"),
                CallbackQueryHandler(edit_office_field, pattern="^edit_"),
                CallbackQueryHandler(return_to_start, pattern="^return_to_start$"),
            ],
            EDIT_OFFICE: [
                MessageHandler(
                    filters=filters.TEXT & ~filters.COMMAND, callback=save_office_field
                ),
            ],
            DELETE_OFFICE: [
                CallbackQueryHandler(perform_delete_office, pattern="^perform_delete_"),
                CallbackQueryHandler(cancel_delete_office, pattern="^cancel_delete_"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
        per_user=True,
    )

    application.add_handler(conv_handler_office)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
