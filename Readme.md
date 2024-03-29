# WB parser bot

Бот для парсинга данных из личного кабинета franchise.wildberries.ru
в формате csv и выгрузки отчета в телеграм боте.

## Описание проекта

Бот создан на python-telegram-bot. Позволяет авторизоваться в личном кабинете франшизы WB.
После авторизации пользователь указывает дату начала и дату окончания отчета, указывает какой тип отчета ему нужен:
 - Отчет по продажам
 - Отчет по операциям
 - Отчет по менеджерам

Отчет по менеджерам работает отдельно от кабинета франшизы WB.
В отчете по менеджерам фиксируется дата начала работы менеджера с системой https://npos.wildberries.ru/
Для этого необходимо установить плагин из Chrome Web Store.
Плагин фиксирует начало работы пользователя с кабинетом при этом он отправляет данные на сервис работающий на FastAPI.
Данные о входе - личный код сотрудника и дата входа записываются в БД.
{здесь будет ссылка на проект с FastAPI + плагин и инструкции для запуска}

После сбора данных бот отправляет файл в формате csv пользователю.

## Пример отчета по операциям сотрудников в csv файле:

```csv
ID сотрудника,Фамилия,Имя,Отчество,Телефон,Дата трудоустройства,Рейтинг,Дата операции,Принято вещей,Возвраты,Возвраты (сумма),Продажи,Продажи (сумма),ШК офиса
10049521,Суркова,Ангелина,Александровна,79221111111,2023-09-29 00:00:00,4.9265,2023-10-04,408,8,13903,303,220046,
10049521,Суркова,Ангелина,Александровна,79221111112,2023-09-29 00:00:00,4.9265,2023-10-05,332,5,7756,390,265523,
```

## Инструкция по установке и настройки

1. Необходимо заполнить env файл используя шаблон .env.tmpl:
- токен TELEGRAM_TOKEN
- строка с TG ID админом - пользователей имеющих доступ к боту
- данные для подключения к БД - опционально - если  нужен учет работы сотрудников
- данные FastAPI сервера, доменное имя

2. Сборка и запуск бота используя Makefile: 

```
Make build
Make run log
Make shell 
```
