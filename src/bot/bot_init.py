from telegram.ext import Updater
from tg_bot.utils.env import TELEGRAM_TOKEN
from telegram import Bot

# Creating updater and dispatcher for bot
bot = Bot(token=TELEGRAM_TOKEN)
updater = Updater(bot=bot)
dp = updater.dispatcher