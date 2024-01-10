import json
import logging
import requests
import requests.utils
import os


# set up logging
logging.basicConfig(level=logging.INFO)


class WildberriesAuth:
    headers = {
        'authority': 'www.wildberries.ru',
        'accept': '*/*',
        'accept-language': 'ru-RU,ru;q=0.9',
        'cache-control': 'no-cache',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'cookie': 'BasketUID=0018207e-b9d2-4f4a-b14a-dc0191f64a29; _wbauid=8935793491690914581; __wba_s=1; ___wbu=aa6301f9-133c-4003-98a6-c672930c679e.1690914591; ___wbs=bf5a2756-14c0-405a-9303-f86533f85e80.1690914591; _wbSes=CfDJ8ApGFP6oJvJKl9OrXZh3OiN369EyDUx6xEI8%2B1lkUeeeiilU5KmYThKxI6Frb1%2BczZadADqrdfrT4Rs17YATrerEzPytSKME5SSFg9MCT27HvDUXNH301Gk8ammXYgUivpaxpJPO9zCqBA5DJT5mXw1wNeTnGILYDeeJWPyITOoG',
        'origin': 'https://www.wildberries.ru',
        'pragma': 'no-cache',
        'referer': 'https://www.wildberries.ru/security/login?returnUrl=https%3A%2F%2Fwww.wildberries.ru%2F',
        'sec-ch-ua': '"Chromium";v="112", "Google Chrome";v="112", "Not:A-Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36',
        'x-requested-with': 'XMLHttpRequest',
        'x-spa-version': '9.3.120.3'
    }

    def __init__(self, session_file='session.txt'):
        self.session_file = session_file
        self.session = requests.Session()
        self.session.headers = self.headers
        # if session file exists, load session from file
        # if os.path.exists(self.session_file):
        #     with open(self.session_file, 'r') as f:
        #         cookies = requests.utils.cookiejar_from_dict(json.txt.load(f))
        #         self.session.cookies = cookies

    def save_session(self):
        try:
            with open(self.session_file, 'w') as f:
                session_data = {
                    'cookies': requests.utils.dict_from_cookiejar(self.session.cookies),
                    'headers': dict(self.session.headers),
                }
                json.dump(session_data, f)
        except Exception as e:
            logging.error(f"Error while saving session: {e}")

    def easy_login(self, phone):
        if self._checkcatpcharequirements(phone):
            logging.info(f"Response for checkcatpcharequirements is OK")
            if self._requestconfirmcode(phone):
                logging.info(f"Response for requestconfirmcode is OK")
                code = input('Enter code: ')
                if self._checkconfirmcode(phone, code):
                    logging.info(f"Response for checkconfirmcode is OK")
                    logging.info(f"Trying to sign in")
                    self.signin(phone, code)
                    if self.signin:
                        logging.info(f"Response for signin is OK")
                        self.save_session()
                        logging.info(f"Session saved")
                        return True
                else:
                    logging.error(f"Response for checkconfirmcode is not OK")
            else:
                logging.error(f"Response for requestconfirmcode is not OK")
        else:
            logging.error(f"Response for checkcatpcharequirements is not OK")

    def _checkcatpcharequirements(self, phone):
        url = 'https://www.wildberries.ru/webapi/security/spa/checkcatpcharequirements'
        payload = f"phoneMobile={phone}"
        params = {
            'forAction': 'EasyLogin',
        }
        try:
            response = self.session.post(url, headers=self.headers, params=params, data=payload)
            if response.status_code == 200:
                logging.info(f'Response: {response.json()}')
                if not response.json()['value']['showCaptcha']:
                    logging.info('Captcha is not required')
                    return True
                else:
                    logging.info('Captcha is required')
                    return False
        except Exception as e:
            logging.error(f'Request to {url} failed with error {e}')
            return False

    def _requestconfirmcode(self, phone):
        url = 'https://www.wildberries.ru/webapi/lk/mobile/requestconfirmcode'
        params = {
            'forAction': 'EasyLogin',
        }
        payload = {
            'phoneInput.ConfirmCode': '',
            'phoneInput.FullPhoneMobile': phone,
            'returnUrl': 'https%3A%2F%2Fwww.wildberries.ru%2F',
            'phonemobile': phone,
            'shortSession': 'false',
            'period': 'ru'
        }
        try:
            response = self.session.post(url, headers=self.headers, params=params, data=payload)
            if response.status_code == 200:
                logging.info(f'Response: {response.json()}')
                if response.json()['ResultState'] == 0:
                    logging.info('Success')
                    return True
                else:
                    logging.info('ResultState is not 0')
                    return False
        except Exception as e:
            logging.error(f'Request to {url} failed with error {e}')
            return False

    def _checkconfirmcode(self, phone, code):
        url = 'https://www.wildberries.ru/webapi/lk/user/checkconfirmcode'
        params = {
            'forAction': 'EasyLogin',
        }
        payload = {
            'confirmCode': code,
            'phoneMobile': phone,
        }
        try:
            response = self.session.post(url, headers=self.headers, params=params, data=payload)
            if response.status_code == 200:
                logging.info(f'Response: {response.json()}')
                if response.json()['Value'] is None:
                    logging.info('Success')
                    # self.save_session()
                    return True
                else:
                    logging.info('Failed')
                    return False

        except Exception as e:
            logging.error(f'Request to {url} failed with error {e}')
            return False

    def signin(self, phone, code):
        params = {
            'forAction': 'EasyLogin',
        }
        url = 'https://www.wildberries.ru/webapi/security/spa/signinsignup'
        payload = {
            'phoneInput.ConfirmCode': code,
            'phoneInput.FullPhoneMobile': phone,
            'returnUrl': 'https://www.wildberries.ru/',
            'phonemobile': phone,
            'shortSession': 'false',
            'period': 'ru'
        }
        try:
            response = self.session.post(url, headers=self.headers, params=params, data=payload)
            if response.status_code == 200:
                logging.info(f'Response: {response.json()}')
                if response.json()['resultState'] == 3:
                    logging.info('Success')
                    self.save_session()
                    return True
                else:
                    logging.info('Failed')
                    return False
        except Exception as e:
            logging.error(f'Request to {url} failed with error {e}')
            return False





