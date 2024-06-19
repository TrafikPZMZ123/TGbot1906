from ping3 import ping
import config
from  config import server, database, username, password, TOKEN
import telebot
import time
import threading
import os
import subprocess
import sqlite3
import pyodbc
from pythonping import ping
import threading
import requests

bot = telebot.TeleBot(config.token)  # Создание бота с указанным токеном

is_running = False # отслеживания состояния


def check_ping(chat_id, ip_address): # Функция для проверки пинга по указанному IP-адресу
    time.sleep(3)
    global is_running
    is_running = True # Устанавливает флаг запуска проверки
    while is_running:  # Цикл проверки состояния пинга (пока флаг установлен в True)
        if ping(ip_address) is None:   # Проверка пинга по адресу
            bot.send_message(chat_id, f'Сервер {ip_address} Офлайн') # Отправка сообщения о статусе сервера
        else:
            bot.send_message(chat_id, f'Сервер {ip_address} Онлайн') # Отправка сообщения о статусе сервера

        time.sleep(2)


def check_ping_2(chat_id, ip_address):  # Функция для проверки пинга по указанному IP-адресу
    time.sleep(3)
    global is_running
    is_running = True  # Устанавливает флаг запуска проверки
    counter = 0  # Переменная для подсчета количества итераций
    while is_running and counter < 4:  # Цикл проверки состояния пинга (пока флаг установлен в True и не достигнуто 4 итерации)
        if ping(ip_address) is None:  # Проверка пинга по адресу
            bot.send_message(chat_id, f'Сервер {ip_address} Офлайн')  # Отправка сообщения о статусе сервера
        else:
            bot.send_message(chat_id, f'Сервер {ip_address} Онлайн')  # Отправка сообщения о статусе сервера

        counter += 1  # Увеличение счетчика итераций
        time.sleep(2)

    bot.send_message(chat_id, 'Проверка завершена')  # Оповещение о завершении проверки
def trace_route(chat_id, ip_address):
    global is_running

    if is_running:
        bot.send_message(chat_id, "Трассировка уже запущена. Пожалуйста, дождитесь ее завершения.")
        return

    is_running = True  # Устанавливаем флаг, что трассировка запущена

    try:
        if config.operating_system == 'Windows':
            result = subprocess.run(['tracert', '-d', ip_address], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    text=True, encoding='cp866')
        elif config.operating_system == 'Linux':
            result = subprocess.run(['traceroute', '-d', ip_address], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    text=True)

        trace_result = result.stdout
        bot.send_message(chat_id, f'Результат трассировки маршрута для {ip_address}:\n{trace_result}')  # Отправка результатов трассировки
    except Exception as e:
        bot.send_message(chat_id, f'An error occurred during traceroute: {e}')
    finally:
        is_running = False  # Устанавливаем флаг, что трассировка завершена

    time.sleep(1)  # Небольшая задержка перед возможным повторным запуском






bot = telebot.TeleBot(TOKEN)

ping_processes = {}  # Словарь для хранения процессов пинга

def ping_ip_by_id(message):
    conn = pyodbc.connect('DRIVER={SQL Server};SERVER=' + server + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + password)
    cursor = conn.cursor()
    cursor.execute("SELECT ID, IP FROM Ping3")
    ip_data = {row.ID: row.IP for row in cursor.fetchall()}
    conn.close()

    keyboard = telebot.types.InlineKeyboardMarkup()
    for id, ip in ip_data.items():
        keyboard.add(telebot.types.InlineKeyboardButton(text=f"ID: {id} - IP: {ip}", callback_data=str(id)))
    bot.send_message(message.chat.id, "Выберите ID для пинга связанного с IP:", reply_markup=keyboard)

# Обработчик нажатия на кнопку выбора ID для пинга
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    id_to_ping = int(call.data)
    conn = pyodbc.connect('DRIVER={SQL Server};SERVER=' + server + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + password)
    cursor = conn.cursor()
    cursor.execute("SELECT IP FROM Ping3 WHERE ID = ?", id_to_ping)
    ip = cursor.fetchone().IP
    conn.close()

    bot.send_message(call.message.chat.id, f"Пинг ID: {id_to_ping}, IP: {ip}")
    # Создание и запуск потока для пингования
    ping_processes[id_to_ping] = threading.Thread(target=ping_worker, args=(call.message.chat.id, id_to_ping, ip))
    ping_processes[id_to_ping].start()

# Обработчик команды "ping"
@bot.message_handler(commands=['ping'])
def ping_start(message):
    ping_ip_by_id(message)

# Функция для выполнения пинга в отдельном потоке
def ping_worker(chat_id, id_to_ping, ip):
    while id_to_ping in ping_processes:  # Запуск пинга, пока процесс не остановлен
        result = subprocess.call(["ping", "-c", "1", ip])
        if result == 0:
            bot.send_message(chat_id, f"ID: {id_to_ping}, IP: {ip} Онлайн")
        else:
            bot.send_message(chat_id, f"ID: {id_to_ping}, IP: {ip} Офлайн")
        time.sleep(3)

# Обработчик команды "stop_ping"
@bot.message_handler(commands=['stop_ping'])
def stop_ping(message):
    for id, process in list(ping_processes.items()):  # Проходим по копии словаря для безопасного удаления элементов во время итерации
        del ping_processes[id]  # Удаляем процесс из словаря, чтобы остановить его
        bot.send_message(message.chat.id, f"Пинг остановлен")




@bot.message_handler(commands=['ping_2']) # Обработчик команды /ping для запуска проверки пинга
def start_ping(message):
    global is_running # Объявление глобальной переменной
    if not is_running:
        try:
            ip_address = message.text.split()[1]  # Получение IP-адреса из сообщения
            threading.Thread(target=check_ping_2, args=(message.chat.id, ip_address)).start()  # Запуск проверки пинга в отдельном потоке
            bot.send_message(message.chat.id, f"Начата проверка пинга для {ip_address}")  # Отправка сообщения о начале проверки
        except IndexError:
            bot.send_message(message.chat.id, "Не указан IP-адрес для проверки")   # Отправка сообщения об ошибке
    else:
        bot.send_message(message.chat.id, "Проверка пинга уже запущена") # Отправка сообщения о том, что проверка уже запущена

@bot.message_handler(commands=['trace'])
def start_trace(message):
    global is_running
    if not is_running:
        try:
            ip_address = message.text.split()[1]
            threading.Thread(target=trace_route, args=(message.chat.id, ip_address)).start()
            bot.send_message(message.chat.id, f"Начата трассировка маршрута для {ip_address}, Ожидайте")
        except IndexError:
            bot.send_message(message.chat.id, "Не указан IP-адрес для трассировки")
    else:
        bot.send_message(message.chat.id, "Трассировка маршрута уже запущена")

@bot.message_handler(commands=['stop_trace'])
def stop_trace(message):
    global is_running
    is_running = False
    bot.send_message(message.chat.id, "Остановка трассировки маршрута")



@bot.message_handler(commands=['staff'])
def get_staff_table(message):
    conn = pyodbc.connect(
        'DRIVER={SQL Server};SERVER=' + server + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + password)
    cursor = conn.cursor()

    # Выполнение запроса к базе данных для таблицы сотрудников
    cursor.execute("select Tab1.ID_sot, Tab1.ФИО,job_title1.Должность AS Должность_Сотрудника, Otdel.Отдел AS OTDEL from Tab1 JOIN job_title1 on Tab1.ID_dol = job_title1.ID JOIN Otdel on Tab1.ID_otdel = Otdel.ID")
    rows = cursor.fetchall()

    staff_table = "Tab1:\n"
    for row in rows:
        staff_table += "ID№: {}, ФИО: {}, Дол-ть: {}, Отдел: {}\n".format(row[0], row[1], row[2], row[3])

    conn.close()

    # Отправка таблицы сотрудников в чат Telegram
    bot.reply_to(message, staff_table)

# Обработчик команды "start"
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_message = """
    Привет! Я бот для пингования IP адресов😎
    Вот все команды которые я умею выполнять💪
    /ping - Пинг
    /ping_2 - Отправка 4 пакетов
    /trace - Трассировка
    /stop_ping - Остановить проверку пинга
    /stop_trace - Остановка трассировки маршрута
    /staff - Сотрудники
    /add_staff - Добавление данных в таблицу сотрудники
    /delete_staff - Удаление данных в таблице сотрудники
    /update_staff - Изменение данных в таблице сотрудники
    """
    bot.reply_to(message, welcome_message)


@bot.message_handler(commands=['add_staff'])
def add_staff_message(message):
    sent = bot.send_message(message.chat.id, "Введите ID:")
    bot.register_next_step_handler(sent, add_staff_id)

def add_staff_id(message):
    id = message.text
    conn = pyodbc.connect('DRIVER={SQL Server};SERVER=' + server + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + password)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Tab1 WHERE ID_sot = ?", id)
    if cursor.fetchone():
        bot.reply_to(message, "Ошибка: Пользователь с таким ID уже существует")
        conn.close()
    else:
        sent = bot.send_message(message.chat.id, "Введите ФИО:")
        bot.register_next_step_handler(sent, lambda message: add_staff_name(message, id))

def add_staff_name(message, id):
    name = message.text
    sent = bot.send_message(message.chat.id, """
    Введите новую должность:
    0-Студент
    1-Программист
    2-Связист
    3-Сисадмин
    4-Секретарь
    5-Директор
    6-Менеджер
    """)
    bot.register_next_step_handler(sent, lambda message: add_staff_position(message, id, name))

def add_staff_position(message, id, name):
    position = message.text
    sent = bot.send_message(message.chat.id, """
    Введите отдел:
    0-IT отдел
    1-Отдел по продажам 
    2-Сетевой отдел 
    3-Отдел закупок 
    4-Корпоративный отдел
    5-Инженерный отдел 
    6-Отдел безопасности
    """)
    bot.register_next_step_handler(sent, lambda message: add_staff_department(message, id, name, position))

def add_staff_department(message, id, name, position):
    department = message.text

    conn = pyodbc.connect('DRIVER={SQL Server};SERVER=' + server + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + password)
    cursor = conn.cursor()

    # Включение параметра IDENTITY_INSERT
    cursor.execute("SET IDENTITY_INSERT Tab1 ON")

    # Вставка данных
    cursor.execute("INSERT INTO Tab1 (ID_sot, ФИО, ID_dol, ID_otdel) VALUES (?, ?, ?, ?)", id, name, position, department)

    # Выключение параметра IDENTITY_INSERT
    cursor.execute("SET IDENTITY_INSERT Tab1 OFF")

    conn.commit()

    bot.reply_to(message, "Данные добавлены успешно в таблицу")

    conn.close()





@bot.message_handler(commands=['delete_staff'])
def delete_staff_message(message):
    sent = bot.send_message(message.chat.id, "Введите ID пользователя, которого вы хотите удалить:")
    bot.register_next_step_handler(sent, delete_staff_by_id)

def delete_staff_by_id(message):
    id = message.text

    conn = pyodbc.connect('DRIVER={SQL Server};SERVER=' + server + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + password)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Tab1 WHERE ID_sot = ?", id)
    if cursor.fetchone():
        cursor.execute("DELETE FROM Tab1 WHERE ID_sot = ?", id)
        conn.commit()
        bot.reply_to(message, f"Данные с ID {id} успешно удалены из таблицы")
    else:
        bot.reply_to(message, f"Ошибка: Пользователь с ID {id} не найден в таблице")

    conn.close()


@bot.message_handler(commands=['update_staff'])
def update_staff_start(message):
    update_staff_message(message)

def update_staff_message(message):
    sent = bot.send_message(message.chat.id, "Введите ID пользователя, данные которого вы хотите изменить:")
    bot.register_next_step_handler(sent, update_staff_get_id)

def update_staff_get_id(message):
    id = message.text
    conn = pyodbc.connect('DRIVER={SQL Server};SERVER=' + server + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + password)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Tab1 WHERE ID_sot = ?", id)
    if cursor.fetchone():
        sent = bot.send_message(message.chat.id, "Введите новое ФИО:")
        bot.register_next_step_handler(sent, lambda message: update_staff_name(message, id))
    else:
        bot.reply_to(message, f"Ошибка: Пользователь с ID {id} не найден в таблице")
        conn.close()

def update_staff_name(message, id):
    name = message.text
    sent = bot.send_message(message.chat.id, """
    Введите новую должность:
    0-Студент
    1-Программист
    2-Связист
    3-Сисадмин
    4-Секретарь
    5-Директор
    6-Менеджер
    """)
    bot.register_next_step_handler(sent, lambda message: update_staff_position(message, id, name))

def update_staff_position(message, id, name):
    position = message.text
    sent = bot.send_message(message.chat.id, """
    Введите новый отдел:
    0-IT отдел
    1-Отдел по продажам 
    2-Сетевой отдел 
    3-Отдел закупок 
    4-Корпоративный отдел
    5-Инженерный отдел 
    6-Отдел безопасности 
    """)
    bot.register_next_step_handler(sent, lambda message: update_staff_department(message, id, name, position))

def update_staff_department(message, id, name, position):
    department = message.text

    conn = pyodbc.connect('DRIVER={SQL Server};SERVER=' + server + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + password)
    cursor = conn.cursor()

    cursor.execute("UPDATE Tab1 SET ФИО = ?, ID_dol = ?, ID_otdel = ? WHERE ID_sot = ?", name, position, department, id)
    conn.commit()

    if cursor.rowcount > 0:
        bot.reply_to(message, f"Данные с ID {id} успешно обновлены в таблице")
    else:
        bot.reply_to(message, f"ID {id} не найден в таблице")

    conn.close()



bot.polling() # Запуск постоянного опроса
