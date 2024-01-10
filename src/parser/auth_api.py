import requests
from bot.logger import WBLogger
from utils.env import API_URL, BASIC_API, TOKEN_URL_FASTAPI, EMPLOYEE_URL
import os
from datetime import datetime
import glob

# set up logging
logger = WBLogger(__name__).get_logger()


class AuthApi:
    headers = {
        "Accept": "application/json.txt, text/plain, */*",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Connection": "keep-alive",
        "Authorization": f"Bearer {BASIC_API}",
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:91.0) Gecko/20100101 Firefox/91.0",
        "Referer": "chrome-extension"
    }

    def __init__(self):
        self.token = None
        self.token_url = TOKEN_URL_FASTAPI
        self.employee_url = EMPLOYEE_URL
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def get_token(self):
        try:
            response = self.session.get(url=self.token_url, headers=self.headers)
            if response.status_code == 200:
                self.token = response.json()['token']
                self.session.headers.update({"employee-api": f'{self.token}'})
                logger.info(f"Token is {self.token}")
                return self.session
            else:
                logger.error(f"Response for connect with key is {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error while connect with key: {e}")
            return None

    def get_employee_data(self, phone_number: str):
        try:
            enpoint_url = f'{self.employee_url}/{phone_number}'
            response = self.session.get(url=enpoint_url)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.error(f"Response for get employee data is {response.status_code}")
                return None
            elif response.status_code == 401:
                logger.error(f"Response for get employee data is {response.status_code}")
                self.get_token()
                return None
        except Exception as e:
            logger.error(f"Error while get employee data: {e}")
            return None







