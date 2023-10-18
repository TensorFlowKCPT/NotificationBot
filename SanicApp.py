from sanic import Sanic, response, HTTPResponse, json, redirect, html, file
from sanic import Sanic
from sanic.response import text, html
from jinja2 import Environment, FileSystemLoader, select_autoescape
import sqlite3
import datetime
import threading

app = Sanic("KCPTApi")

env = Environment(
    loader=FileSystemLoader('templates'),  # Папка с шаблонами
    autoescape=select_autoescape(['html', 'xml'])
)

def run_another_file():
    import subprocess
    python_file_path = "TeleBot.py"
    subprocess.run(["python", python_file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
days_in_russian = ['понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота', 'воскресенье']
@app.route("/")
async def index(request):
    Data = {}
    Data['Groups'] = []
    Data['Notifications'] = []
    with sqlite3.connect('ScheduleBot.db') as conn:
        cursor = conn.execute('''Select GroupTitle FROM GroupChats''')
        result = cursor.fetchall()
        for row in result:
            Data['Groups'].append(row[0])
    Data['Groups'] = sorted(Data['Groups'])
    with sqlite3.connect('ScheduleBot.db') as conn:
        cursor = conn.execute('''
        SELECT
            G.GroupTitle,
            N.LessonStartTime,
            N.LessonEndTime,
            N.LessonDay,
            N.LessonStartNotificationText,
            N.LessonEndNotificationText,
            N.ID
        FROM Notifications N
        JOIN GroupChats G ON N.GroupId = G.GroupId
        ''')
        result = cursor.fetchall()
        for row in result:
            Data['Notifications'].append({
                'Group' : row[0],
                'LessonStart' : row[1],
                'LessonEnd' : row[2],
                'Day' : days_in_russian[row[3]],
                'LessonStartMsg': row[4],
                'LessonEndMsg': row[5],
                'ID' : row[6]
            })
            
   
    Data['Notifications'] = sorted(Data['Notifications'], key=lambda x: x['Group'])

    template = env.get_template('index.html')
    return response.html(template.render(data = Data))

@app.route('/delete_notification')
async def delete_notification(request):
    id = request.args.get('id')
    with sqlite3.connect('ScheduleBot.db') as conn:
        conn.execute('''DELETE FROM Notifications WHERE ID = ?''',(id, ))
    return response.redirect('/')
    
@app.route('/add_notification', methods=['POST'])
async def add_notification(request):
    group_title = request.form.get('group_title')
    lesson_start_time = request.form.get('lesson_start_time')
    if len(lesson_start_time) == 4:
        lesson_start_time = '0'+lesson_start_time
    lesson_end_time = request.form.get('lesson_end_time')
    if len(lesson_end_time) == 4:
        lesson_end_time = '0'+lesson_end_time
    lesson_day = request.form.get('lesson_day')
    with sqlite3.connect('ScheduleBot.db') as conn:
        group_id = conn.execute('''SELECT GroupId FROM GroupChats WHERE GroupTitle = ?''',(group_title,)).fetchone()[0]
    lesson_day = days_in_russian.index(lesson_day.lower())
    lessonStartMessage = request.form.get('lesson_start_message')
    lessonEndMessage = request.form.get('lesson_end_message')
    
    with sqlite3.connect('ScheduleBot.db') as conn:
        conn.execute('''INSERT INTO Notifications(GroupId, LessonStartTime, LessonEndTime, LessonDay,LessonStartNotificationText,LessonEndNotificationText) VALUES (?, ?, ?, ?, ?, ?)''',(group_id, lesson_start_time, lesson_end_time, lesson_day, lessonStartMessage, lessonEndMessage))
    

    return response.redirect('/')


if __name__ == "__main__":
    print("Запуск")
    thread = threading.Thread(target=run_another_file)
    thread.start()
    app.run(host="0.0.0.0", port=8000)
