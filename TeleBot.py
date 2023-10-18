import telebot
from telebot import types
import datetime
import sqlite3
import threading
import time
import requests
import json


bot_token = '6487553292:AAF3j37hEFVv4IXSbjGiKzrze8qrkZyiqI4'
bot = telebot.TeleBot(bot_token)
bot_id = bot.get_me().id
update_url = f'https://api.telegram.org/bot{bot_token}/getUpdates'


def get_chat_list():
    updates = bot.get_updates()
    chat_list = []

    for update in updates:
        chat = update.message.chat
        if chat not in chat_list:
            chat_list.append(chat)

    return chat_list

def StartDatabase():
    with sqlite3.connect('ScheduleBot.db') as conn:
                conn.execute('''CREATE TABLE IF NOT EXISTS GroupChats (
                             GroupId TEXT NOT NULL PRIMARY KEY,
                             GroupTitle TEXT
                             )''')
                conn.execute('''CREATE TABLE IF NOT EXISTS Notifications (
                             ID INTEGER NOT NULL PRIMARY KEY,
                             GroupId TEXT NOT NULL,
                             LessonStartTime TIME NOT NULL,
                             LessonEndTime TIME NOT NULL,
                             LessonDay INTEGER NOT NULL,
                             LessonStartNotificationText TEXT,
                             LessonEndNotificationText TEXT
                             )''')

def main():
    offset = None  # Начальное значение смещения
    while True:
        updates = get_updates(offset)
        
        if updates:
            for update in updates:
                process_update(update)
            # Установите новое значение смещения, чтобы избежать повторной обработки одних и тех же обновлений
            offset = updates[-1]['update_id'] + 1



def get_updates(offset):
    response = requests.get(update_url, params={'offset': offset})
    data = response.json()
    return data.get('result', [])


days_in_russian = ['понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота', 'воскресенье']
# Функция для обработки обновления
def process_update(update):
    print(update)
    try:
        if update['message']['chat']['type'] == 'group' and update['message']['new_chat_member']['first_name'] == "NotificationBot":
            #Бот добавлен в новую группу
            with sqlite3.connect('ScheduleBot.db') as conn:
                insert_query = "INSERT OR IGNORE INTO GroupChats (GroupId, GroupTitle) VALUES (?, ?)"
                conn.execute(insert_query, (update['message']['chat']['id'], update['message']['chat']['title']))
            return
    except KeyError:
        pass
    try:
        if update['message']['chat']['type'] == 'private' and update['message']['text'] == "/start":
            #Первое сообщение боту
            bot.send_message(update['message']['chat']['id'], 'Жду пароль')
            return
    except KeyError:
        pass

    try:
        if update['message']['chat']['type'] == 'private' and update['message']['text'] == "QWERTYQWERTY":
            #Бот получил пароль
            bot.send_message(update['message']['chat']['id'], text='Выберите действие',reply_markup=GetMenuKeyboard())
            return
    except KeyError:
        pass
    try:
        if update['message']['chat']['type'] == 'private' and update['message']['text'] == "Посмотреть все группы для которых есть расписание":
            with sqlite3.connect('ScheduleBot.db') as conn:
                cursor = conn.execute('''
                SELECT
                    G.GroupTitle,
                    N.LessonStartTime,
                    N.LessonEndTime,
                    N.LessonDay,
                    N.LessonStartNotificationText,
                    N.LessonEndNotificationText
                FROM Notifications N
                JOIN GroupChats G ON N.GroupId = G.GroupId
                ''')
                result = cursor.fetchall()
            formatted_message = ''
            for row in result:
                group_title, lesson_start_time, lesson_end_time, lesson_day, lessonStartMessage, lessonEndMessage = row
                formatted_message += f"Группа: {group_title}\n" \
                                   f"Начало урока: {lesson_start_time}\n" \
                                   f"Окончание урока: {lesson_end_time}\n" \
                                   f"День урока: {days_in_russian[lesson_day]}\n" \
                                   f"Сообщение о начале урока: {lessonStartMessage}\n" \
                                   f"Сообщение о конце урока: {lessonEndMessage}"

            bot.send_message(update['message']['chat']['id'], text='\n'+formatted_message+'\n')
            return
    except KeyError:
        pass


def DeleteNotificationById(NotificationId):
    with sqlite3.connect('ScheduleBot.db') as conn:
        cursor = conn.cursor()
        delete_query = "DELETE FROM Notifications WHERE NotificationId = ?"
        cursor.execute(delete_query, (NotificationId,))
        conn.commit()

def GetMenuKeyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    ScheduleButton = types.KeyboardButton(text="Посмотреть все группы для которых есть расписание")
    keyboard.add(ScheduleButton)
    return keyboard

def GetGroupScheduleKeyboard(GroupId):
    keyboard = types.InlineKeyboardMarkup()
    with sqlite3.connect('ScheduleBot.db') as conn:
        cursor = conn.execute('''
        SELECT
            G.GroupTitle,
            N.LessonStartTime,
            N.LessonEndTime,
            N.LessonDay,
            N.ID
        FROM Notifications N
        JOIN GroupChats G ON N.GroupId = G.GroupId
        ''')
        result = cursor.fetchall()
        for row in result:
            keyboard.add(types.InlineKeyboardButton(text=f'''{row[1]} - {row[2]}, {days_in_russian[row[3]]}''', callback_data=row[4]))
    keyboard.add(types.InlineKeyboardButton(text=f'''Добавить новый урок''', callback_data='Add*'+GroupId))
    return keyboard

def GetGroupsKeyboard():
    keyboard = types.InlineKeyboardMarkup()
    with sqlite3.connect('ScheduleBot.db') as conn:
                cursor = conn.execute('''Select * FROM GroupChats''')
                result = cursor.fetchall()
                for row in result:
                    keyboard.add(types.InlineKeyboardButton(text=row[1], callback_data=row[0]))
    return keyboard


def schedule_monitor():
    while True:
        with sqlite3.connect('ScheduleBot.db') as conn:
            cursor = conn.execute("SELECT * FROM Notifications")
            result = cursor.fetchall()
            current_time = (datetime.datetime.now() - datetime.timedelta(hours=2)).strftime("%H:%M")
            current_weekday = datetime.datetime.now().weekday()
            
            for i in result:
                if i[2] == current_time and i[4] == current_weekday:
                    print(3)
                    bot.send_message(i[1], i[5])
                elif i[3] == current_time and i[4] == current_weekday:
                    bot.send_message(i[1], i[6])

        time.sleep(60) 

StartDatabase()
monitor_thread = threading.Thread(target=schedule_monitor)
monitor_thread.start()
main()




