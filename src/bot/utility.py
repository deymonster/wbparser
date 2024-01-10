import re
from dateutil.parser import parse
from .logger import WBLogger
from functools import wraps
from telegram import Update
from utils.env import ADMINS
from telegram.ext import ConversationHandler

logger = WBLogger(__name__).get_logger()


def validate_phone_number(phone_input):
    """
    Validate phone number

    :param phone_input:
    :return:
    """
    # get only digits from phone number
    digits = re.sub(r'\D', '', phone_input)
    # if length phone number 10 add 7 to the beginning
    if len(digits) == 10 and digits[0] == '9':
        digits = '7' + digits

    # if length phone number 11 and first digit is 8 replace 8 with 7
    if len(digits) == 11 and digits[0] == '8':
        digits = '7' + digits[1:]

    # final check length phone number is 11 and first digit is 7
    if len(digits) == 11 and digits[0] == '7':
        return digits
    else:
        return None


def validate_code(code):
    pass


def validate_date(date_string):
    try:
        date = parse(date_string)
        logger.info(f"Date parsed: {date}")
        return date
    except ValueError:
        logger.error(f"Failed to parse date: {date_string}")
        return None


def restricted(func):
    @wraps(func)
    async def wrapped(update: Update, context, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in ADMINS:
            await update.message.reply_text("Извините, у вас нет прав на выполнение этой команды")
            return ConversationHandler.END
        return await func(update, context, *args, **kwargs)
    return wrapped


