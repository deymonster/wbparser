from dotenv import load_dotenv
import os

# load env file
load_dotenv()

#login_url = os.getenv('LOGIN_URL')
base_url_v1 = os.getenv('BASE_URL_V1')
base_url_v2 = os.getenv('BASE_URL_V2')
refresh_url = os.getenv('REFRESH_URL')
token = os.getenv('token')
refresh_token = os.getenv('refresh_token')
basic = os.getenv('BASIC')
operations_url = os.getenv('OPERATIONS_URL')
shortages_url = os.getenv('SHORTAGES_URL')
shks_url = os.getenv("SHKS_URL")
date_from = os.getenv('DATE_FROM')
date_to = os.getenv('DATE_TO')
GET_EVENTS_LK_URL = os.getenv('GET_EVENTS_LK_URL')
LOGIN_FR_URL = os.getenv('LOGIN_FR_URL')
TOKEN_URL = os.getenv('TOKEN_URL')

# FastAPI
API_URL = os.getenv('API_URL')
BASIC_API = os.getenv('BASIC_API')
TOKEN_URL_FASTAPI = os.getenv('TOKEN_URL_FASTAPI')
EMPLOYEE_URL = os.getenv('EMPLOYEE_URL')



# Telegram
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

# ADMINS
ADMINS_STRING = os.getenv('ADMINS')
ADMINS = [int(admin_id.strip()) for admin_id in ADMINS_STRING.split(",")]

# DB
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
POSTGRES_SERVER = os.getenv('POSTGRES_HOST', 'employee-db')
POSTGRES_PORT = os.getenv('POSTGRES_PORT', 5432)
POSTGRES_DB = os.getenv('POSTGRES_DB')
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}"



