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
Offset = 0
def main():
    try:
        global Offset
        while True:
            updates = get_updates(Offset)
            if updates:
                for update in updates:
                    process_update(update)
                # Установите новое значение смещения, чтобы избежать повторной обработки одних и тех же обновлений
                Offset = updates[-1]['update_id'] + 1
    except Exception as Ex: 
        print("Я упал")
        
        bot.send_message(chat_id=695308592,text=f"Я словил ошибку и перезапустился")
        bot.send_message(chat_id=754492597,text=f"Я словил ошибку и перезапустился, ошибка = {Ex}")
        main()


def get_updates(offset):
    response = requests.get(update_url, params={'offset': offset})
    data = response.json()
    return data.get('result', [])


days_in_russian = ['понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота', 'воскресенье']
# Функция для обработки обновления
def process_update(update):
    print(update)
    try:
        if (update['message']['chat']['type'] == 'group' or update['message']['chat']['type'] == 'supergroup') and update['message']['new_chat_member']['id'] == 6487553292:
            bot.send_message(chat_id=754492597,text=f"Меня добавили в группу {update['message']['chat']['title']}")
            bot.send_message(chat_id=695308592,text=f"Меня добавили в группу {update['message']['chat']['title']}")
            #Бот добавлен в новую группу
            with sqlite3.connect('ScheduleBot.db') as conn:
                insert_query = "INSERT OR IGNORE INTO GroupChats (GroupId, GroupTitle) VALUES (?, ?)"
                conn.execute(insert_query, (update['message']['chat']['id'], update['message']['chat']['title']))
            return
    except KeyError:
        pass
    try:
        if update['message']['chat']['type'] == 'private':
            #Первое сообщение боту
            bot.send_message(update['message']['chat']['id'], 'Я работаю!')
            return
    except KeyError:
        pass
    try:
        if (update['my_chat_member']['chat']['type'] == 'group' or update['my_chat_member']['chat']['type'] == 'supergroup') and update['my_chat_member']['old_chat_member']['user']['id'] == 6487553292:
            bot.send_message(chat_id=754492597,text=f"Меня удалили из группы {update['my_chat_member']['chat']['title']}")
            bot.send_message(chat_id=695308592,text=f"Меня удалили из группы {update['my_chat_member']['chat']['title']}")
            with sqlite3.connect('ScheduleBot.db') as conn:
                query = "DELETE FROM Notifications WHERE GroupId = ?"
                conn.execute(query,(update['my_chat_member']['chat']['id'],))
            with sqlite3.connect('ScheduleBot.db') as conn:
                query = "DELETE FROM GroupChats WHERE GroupId = ?"
                conn.execute(query,(update['my_chat_member']['chat']['id'],))
                
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

            bot.send_message(update['message']['chat']['id'], text='```\n'+formatted_message+'\n```')
            return
    except KeyError:
        pass


def DeleteNotificationById(NotificationId):
    with sqlite3.connect('ScheduleBot.db') as conn:
        cursor = conn.cursor()
        delete_query = "DELETE FROM Notifications WHERE NotificationId = ?"
        cursor.execute(delete_query, (NotificationId,))
        conn.commit()


def schedule_monitor():
    while True:
        with sqlite3.connect('ScheduleBot.db') as conn:
            print("Проверяю!")
            cursor = conn.execute("SELECT * FROM Notifications")
            result = cursor.fetchall()
            current_time = datetime.datetime.now().strftime("%H:%M")
            current_weekday = datetime.datetime.now().weekday()
            
            for i in result:
                if i[2] == current_time and i[4] == current_weekday:
                    print(i[1], i[5])
                    bot.send_message(i[1], i[5])
                elif i[3] == current_time and i[4] == current_weekday:
                    print(i[1], i[5])
                    bot.send_message(i[1], i[6])

        time.sleep(60) 

StartDatabase()
monitor_thread = threading.Thread(target=schedule_monitor)
monitor_thread.start()
main()




