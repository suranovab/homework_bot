class InvalidHttpStatus(Exception):
    """Ответа от API ЯYandex.Practicum не 200."""

    pass


class UnknownHomeworkStatus(Exception):
    """Неизвестный статус домашнего задания."""

    pass
