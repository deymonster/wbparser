import requests
from bot.logger import WBLogger
from utils.env import basic, LOGIN_FR_URL, TOKEN_URL
import os
from datetime import datetime
import glob

# set up logging
logger = WBLogger(__name__).get_logger()


# клас для авторизации  получения токена в ЛК Франшизе
class Auth:
    headers = {
        "Accept": "application/json.txt, text/plain, */*",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Connection": "keep-alive",
        "Referer": "https://franchise.wildberries.ru/",
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {basic}",
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:91.0) Gecko/20100101 Firefox/91.0"
    }

    def __init__(self):
        self.token = None
        self.refresh_token = None
        self.login_url = LOGIN_FR_URL
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.token_url = TOKEN_URL
        self.auth_status = None

    def get_auth_status(self):
        return self.auth_status

    def get_franchise_session(self, phone: str):

        self.refresh_token = self._load_refresh_token(phone)
        logger.info(f"Refresh token is {self.refresh_token}")
        # Init status code
        status_code = None
        # If refresh token is not None then connect with refresh token
        if self.refresh_token:
            self.session, status_code = self.connect_with_token()
            logger.info(f"Status code after connect with refresh token is {status_code}")
            logger.info(f"Session after connect with refresh token is {self.session}")
            if self.session and status_code != 400:
                logger.info("Session is OK")
                return self.session
            else:
                self._remove_refresh_token_file(phone)
                logger.error(" Refresh token is expired. Trying to connect with phone and code")

        # If status code is 400 then refresh token is expired
        # else connect with phone and code
        params = {
            'phone': phone
        }
        try:
            response = self.session.get(url=LOGIN_FR_URL, headers=self.headers, params=params)
            logger.info(f"Response for login franchise is {response.json()}")
            if response.status_code == 200 and response.json()['isSuccess']:
                logger.info(f"Response for login franchise is OK")
                # send code from LK WB and pass it to _connect_with_code
                # code = input('Enter code from LK WB: ')
                # if code:
                #     self._connect_with_code(phone, code)
                # else:
                self.auth_status = "NEED_CODE"
            else:
                self.auth_status = response.json()['message']
        except Exception as e:
            logger.error(f"Error while login to franchise {e}")
            self.auth_status = "ERROR"
        return self.session

    def _remove_refresh_token_file(self, phone):
        try:
            files = glob.glob(f"refresh_token_{phone}_*.txt")
            for f in files:
                os.remove(f)
            logger.info(f"Refresh token file for {phone} is removed")
        except Exception as e:
            logger.error(f"Error while removing refresh token file {e}")

    def connect_with_code(self, phone, code):
        payload = {
            'grant_type': 'password',
            'username': phone,
            'password': code
        }
        try:
            response = self.session.post(url=TOKEN_URL, data=payload)
            if response.status_code == 200:
                self.token = response.json()['access_token']
                self.session.headers.update({'Authorization': f"Bearer {self.token}"})
                self.refresh_token = response.json()['refresh_token']
                self._save_refresh_token(self.refresh_token, phone)
                # os.environ['refresh_token'] = self.refresh_token
                logger.info(f"New Refresh token is taken {self.refresh_token}")
                return self.session
            else:
                logger.error(f"Error while connecting with code {response.json()}")
                return None
        except Exception as e:
            logger.error(f"Error while connecting with code {e}")
            return None

    def connect_with_token(self):
        payload = {
            'refresh_token': self.refresh_token,
            'grant_type': 'refresh_token'
        }
        logger.info(f"Payload for refresh token is {payload}")
        try:
            response = self.session.post(url=self.token_url, data=payload, headers=self.headers)
            if response.status_code == 200:
                self.token = response.json()['access_token']
                self.session.headers.update({'Authorization': f"Bearer {self.token}"})
                return self.session, response.status_code
            else:
                logger.error(f'Status code: {response.status_code}')
                return self.session, response.status_code
        except Exception as e:
            logger.error(f"Error while connecting with token {e}")
            return None, None

    def _save_refresh_token(self, refresh_token, phone):
        date_str = datetime.now().strftime("%d-%m-%Y_%H:%M:%S")
        filename = f'refresh_token_{phone}_{date_str}.txt'
        with open(filename, 'w') as f:
            f.write(refresh_token)

    def _load_refresh_token(self, phone):
        try:
            files = glob.glob(f'refresh_token_{phone}_*.txt')
            latest_file = max(files, key=os.path.getctime)
            with open(latest_file, 'r') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error while loading refresh token {e}")
            return None

