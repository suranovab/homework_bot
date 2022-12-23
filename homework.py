import logging
import os
import sys
import time
import requests
from http import HTTPStatus
from dotenv import load_dotenv
import telegram

import exceptions

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

MISSING_TOKENS = 'Отсутствуют обязательные переменные окружения'

logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    format='%(asctime)s, %(levelname)s, %(message)s'
)


def check_tokens():
    """Функция проверки наличия переменных окружения."""
    tokens = (PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    return all(tokens)


def send_message(bot, message):
    """Фукция отправляет сообщение в Telegram чат."""
    try:
        logging.debug('Отправка сообщения в Telegram.')
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('Сообщение в Telegram успешно отправлено.')
    except Exception as error:
        logging.error(f'Ошибка при отправке сообщения: {error}')


def get_api_answer(timestamp):
    """Запрос к API-Yandex.Practicum."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=payload
        )
        response_content = response.json()
        if response.status_code == HTTPStatus.OK:
            return response_content
        else:
            raise exceptions.InvalidHttpStatus(
                'Ошибка запроса к API Yandex.Practicum: ',
                f'Код ответа: {response_content.get("code")}',
                f'Ответ сервера: {response_content.get("message")}'
            )
    except requests.exceptions.RequestException as error:
        logging.error(
            f'Сбой при запросе к сервису API: {error}.'
        )


def check_response(response):
    """Проверка ответа API Yandex.Practicum."""
    if not isinstance(response, dict):
        raise TypeError(
            'Ответ сервиса API не является словарем.'
        )
    if not response.get('current_date'):
        raise KeyError(
            'Ключ сurrent_date в ответе API отсутствует'
        )
    if not response.get('homeworks'):
        raise KeyError(
            'Ключ homeworks в ответе API отсутствует'
        )
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError(
            'В ответе API под ключом homeworks данные не являются списком'
        )
    return homeworks


def parse_status(homework):
    """Проверка статуса домашнего задания."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if not homework_name:
        raise KeyError(
            'Ключ homework_name в ответе API отсутствует'
        )
    if homework_status not in HOMEWORK_VERDICTS:
        raise exceptions.UnknownHomeworkStatus
    verdict = HOMEWORK_VERDICTS.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical(MISSING_TOKENS)
        sys.exit(MISSING_TOKENS)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time()) - 604800

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            for homework in homeworks:
                message = parse_status(homework)
                send_message(bot, message)
            timestamp = int(time.time())
            time.sleep(RETRY_PERIOD)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
