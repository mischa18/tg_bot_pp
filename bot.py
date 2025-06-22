import telebot
from datetime import datetime
import time
import threading

# === CONFIGURATION ===
BOT_TOKEN = '8024454492:AAEwsY2oNFwk4K3ScOhNnas83QMqei-NVV4'
bot = telebot.TeleBot(BOT_TOKEN)

# === ЗАГЛУШКИ ДАННЫХ ===
TEACHERS = {
    "usernames": {"@geb_mi", "@geb_m"}
}

STUDENTS = {
    "@Herman_Gebel": {"name": "Маша ", "group_id": 1, "chat_id": 11111111},
    "@amaro_nonino": {"name": "Саша ", "group_id": 1, "chat_id": 997855184},
    "@owhrg": {"name": "Даша ", "group_id": 2, "chat_id": 1111111112},
    "@gands404": {"name": "Каша ", "group_id": 1, "chat_id": 33333333},
    "@goordeev": {"name": "Карина ", "group_id": 2, "chat_id": 34444444},
    "@vlaniiik": {"name": "Артем ", "group_id": 2, "chat_id": 55555555},
}

GROUPS = {
    1: {"name": "Группа 1"},
    2: {"name": "Группа 2"}
}

LESSONS = [
    {
        "id": 1,
        "teacher_username": 1749719980,
        "year_month_day": "2025-06-23",
        "start_time": "00:20",
        "end_time": "00:44"
    },
    {
        "id": 2,
        "teacher_username": 1749719980,
        "year_month_day": "2025-06-23",
        "start_time": "00:44",
        "end_time": "03:00"
    }
]

SCHEDULE = [
    {
        "schedule_id": 1,
        "lesson_id": 1,
        "group_id": 1
    },
    {
        "schedule_id": 2,
        "lesson_id": 1,
        "group_id": 2
    },
    {
        "schedule_id": 3,
        "lesson_id": 2,
        "group_id": 1
    },
    {
        "schedule_id": 4,
        "lesson_id": 2,
        "group_id": 2
    }
]

# === ЗАГЛУШКА ПОСЕЩАЕМОСТИ ===
ATTENDANCE_LIST = []

# === ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ДЛЯ УВЕДОМЛЕНИЙ ===
notified_lessons = set()         # ID уроков, по которым уже были уведомления
notified_students = set()        # (username, lesson_id) — студенты, которые уже получили уведомление об оценке

# === ОБРАБОТЧИК СТАРТА ===
@bot.message_handler(commands=['start'])
def handle_start(message):
    user = message.from_user
    username = f"@{user.username}" if user.username else None
    user_nick = message.from_user.username
    name = message.from_user.full_name or message.from_user.first_name
    chat_id = message.chat.id
    print(f"[+] Получен chat_id: {chat_id}, имя: {name}, username: @{user_nick}")
    if not username:
        bot.reply_to(message, "Пожалуйста, установите username в настройках Telegram.")
        return
    if username in STUDENTS:
        group_id = STUDENTS[username]["group_id"]
        bot.reply_to(message, f"Привет ! Ты студент из группы {GROUPS[group_id]['name']}.")
    elif username in TEACHERS["usernames"]:
        bot.reply_to(message, "Здравствуйте! Вы преподаватель.")
    else:
        bot.reply_to(message, "Я тебя не знаю.")

# === ФУНКЦИЯ ДЛЯ ВЫВОДА ГРУПП С ОДНОЙ И ТОЙ ЖЕ ПАРОЙ ===
def get_groups_with_same_lesson(current_lesson_id):
    groups = []
    for schedule in SCHEDULE:
        if schedule["lesson_id"] == current_lesson_id:
            groups.append(schedule["group_id"])
    return groups

# === ОБРАБОТЧИК КНОПОК ===
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    data = call.data.split(":")
    if data[0] == "group":
        lesson_id = int(data[1])
        group_id = int(data[2])
        show_students_list(chat_id=call.message.chat.id,
                           lesson_id=lesson_id,
                           group_id=group_id,
                           message_id=call.message.message_id)
    elif data[0] == "student":
        lesson_id = int(data[1])
        student_username = data[2]
        toggle_attendance(lesson_id=lesson_id,
                          student_username=student_username,
                          message=call.message)
    elif data[0] == "group_list":
        lesson_id = int(data[1])
        show_groups_for_lesson(chat_id=call.message.chat.id, lesson_id=lesson_id)
    elif data[0] == "rating":
        lesson_id = int(data[1])
        student_username = data[2]
        rating = int(data[3])
        update_rating(lesson_id=lesson_id,
                      student_username=student_username,
                      rating=rating)

# === ПОКАЗ СТУДЕНТОВ ГРУППЫ ===
def show_students_list(chat_id, lesson_id, group_id, message_id):
    students = [s for s in STUDENTS.values() if s["group_id"] == group_id]
    usernames = [k for k, v in STUDENTS.items() if v["group_id"] == group_id]
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    buttons = []
    existing_entries = [e for e in ATTENDANCE_LIST if e["lesson_id"] == lesson_id]
    existing_users = set(e["student_username"] for e in existing_entries)

    for i in range(len(students)):
        student_name = students[i]["name"]
        student_username = usernames[i]

        # Если студента ещё нет в списке посещаемости, добавляем его
        if student_username not in existing_users:
            ATTENDANCE_LIST.append({
                "student_username": student_username,
                "lesson_id": lesson_id,
                "present": False,
                "rating": None
            })

        # Получаем статус присутствия студента
        present = next((e["present"] for e in ATTENDANCE_LIST if
                        e["student_username"] == student_username and e["lesson_id"] == lesson_id), False)

        # Формируем текст кнопки: имя студента + статус посещаемости
        btn_text = f"{student_name}{'❌ Отсутствует' if not present else ''}"
        callback_data = f"student:{lesson_id}:{student_username}"

        btn = telebot.types.InlineKeyboardButton(text=btn_text, callback_data=callback_data)
        buttons.append(btn)

    back_btn = telebot.types.InlineKeyboardButton(text="⬅️ Назад", callback_data=f"group_list:{lesson_id}")
    buttons.append(back_btn)
    markup.add(*buttons)

    bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=f"Студенты группы {GROUPS[group_id]['name']} на уроке ID {lesson_id}:",
        reply_markup=markup
    )

# === ПОКАЗ СПИСКА ГРУПП ДЛЯ ТЕКУЩЕГО УРОКА ===
def show_groups_for_lesson(chat_id, lesson_id):
    groups = get_groups_with_same_lesson(lesson_id)
    if not groups:
        return  # Нет групп
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    buttons = []
    for group_id in groups:
        btn = telebot.types.InlineKeyboardButton(
            GROUPS.get(group_id, {}).get("name", f"Группа {group_id}"),
            callback_data=f"group:{lesson_id}:{group_id}"
        )
        buttons.append(btn)
    markup.add(*buttons)
    bot.send_message(chat_id, "Выберите группу:", reply_markup=markup)

# === ИЗМЕНЕНИЕ СТАТУСА НАЛИЧИЯ СТУДЕНТА ===
def toggle_attendance(lesson_id, student_username, message):
    now = datetime.now()
    current_time_str = now.strftime("%H:%M")

    for lesson in LESSONS:
        if lesson["id"] == lesson_id:
            end_time_str = lesson["end_time"]
            break
    else:
        bot.answer_callback_query(callback_query_id=message.id, text="Не найден урок.")
        return

    if current_time_str >= end_time_str:
        bot.answer_callback_query(callback_query_id=message.id,
                                  text="Пара уже окончена. Нельзя редактировать посещаемость.")
        return

    for entry in ATTENDANCE_LIST:
        if str(entry["student_username"]) == str(student_username) and entry["lesson_id"] == lesson_id:
            entry["present"] = not entry["present"]
            break
    else:
        ATTENDANCE_LIST.append({
            "student_username": student_username,
            "lesson_id": lesson_id,
            "present": True,
            "rating": None
        })

    student_name = next((info["name"] for key, info in STUDENTS.items() if key == student_username or (isinstance(key, int) and isinstance(student_username, int) and key == student_username)), "Неизвестный")
    new_status = next((e["present"] for e in ATTENDANCE_LIST if str(e["student_username"]) == str(student_username) and e["lesson_id"] == lesson_id), False)

    updated_text = f"{student_name} - {'❌ Отсутствует' if not new_status else ''}"

    for row in message.reply_markup.keyboard:
        for j, button in enumerate(row):
            if button.callback_data.endswith(str(student_username)):
                row[j].text = updated_text
                break

    bot.edit_message_reply_markup(
        chat_id=message.chat.id,
        message_id=message.message_id,
        reply_markup=message.reply_markup
    )

    print(f"[+] Статус студента '{student_username}' изменён на: {new_status}")

# === ОБНОВЛЕНИЕ ОЦЕНКИ ===
def update_rating(lesson_id, student_username, rating):
    for entry in ATTENDANCE_LIST:
        if str(entry["student_username"]) == str(student_username) and entry["lesson_id"] == lesson_id:
            if entry["rating"] is not None:
                print(f"[-] Студент {student_username} уже поставил оценку. Дублирование запрещено.")
                return
            entry["rating"] = rating
            print(f"[+] Студент {student_username} поставил оценку {rating} для урока ID {lesson_id}")
            break

# === ФУНКЦИЯ ПРОВЕРКИ И УВЕДОМЛЕНИЙ ===
def check_lessons():
    while True:
        now = datetime.now()
        current_date_str = now.strftime("%Y-%m-%d")
        current_time_str = now.strftime("%H:%M")

        for lesson in LESSONS:
            if lesson["year_month_day"] != current_date_str:
                continue

            # Проверка начала пары
            if current_time_str >= lesson["start_time"] and current_time_str <= lesson["end_time"]:
                if lesson["id"] not in notified_lessons:
                    try:
                        teacher_username = lesson["teacher_username"]
                        bot.send_message(teacher_username, f"Началась пара ID {lesson['id']}.")
                        print(f"[+] Уведомление о начале пары отправлено преподавателю {teacher_username}")

                        groups = get_groups_with_same_lesson(lesson["id"])
                        if len(groups) > 0:
                            markup = telebot.types.InlineKeyboardMarkup(row_width=1)
                            buttons = []
                            for group_id in groups:
                                btn = telebot.types.InlineKeyboardButton(
                                    GROUPS.get(group_id, {}).get("name", f"Группа {group_id}"),
                                    callback_data=f"group:{lesson['id']}:{group_id}"
                                )
                                buttons.append(btn)
                            markup.add(*buttons)
                            bot.send_message(teacher_username, "Выберите группу:", reply_markup=markup)
                            print(f"[+] Отправлено сообщение с выбором групп для урока {lesson['id']}")
                    except Exception as e:
                        print(f"[-] Не удалось отправить уведомление преподавателю: {e}")
                    finally:
                        notified_lessons.add(lesson["id"])

            # Проверка окончания пары
            if current_time_str >= lesson["end_time"]:
                present_students = [e for e in ATTENDANCE_LIST if e["lesson_id"] == lesson["id"] and e["present"]]
                for student in present_students:
                    if student["rating"] is None and (str(student["student_username"]), lesson["id"]) not in notified_students:
                        try:
                            markup = telebot.types.InlineKeyboardMarkup(row_width=5)
                            buttons = []
                            for r in range(1, 6):
                                btn = telebot.types.InlineKeyboardButton(
                                    str(r),
                                    callback_data=f"rating:{lesson['id']}:{student['student_username']}:{r}"
                                )
                                buttons.append(btn)
                            markup.add(*buttons)
                            bot.send_message(int(STUDENTS.get(str(student["student_username"]), {}).get("chat_id")), "Оцените занятие (1-5):", reply_markup=markup)
                            print(f"[+] Отправлено уведомление об оценке студенту {student['student_username']}")
                            notified_students.add((str(student["student_username"]), lesson["id"]))
                        except Exception as e:
                            print(f"[-] Не удалось отправить уведомление студенту {student['student_username']}: {e}")

        time.sleep(60)  # Проверяем каждую минуту

# === КОМАНДА ДЛЯ ПРОСМОТРА ПОСЕЩАЕМОСТИ ===
@bot.message_handler(commands=['attendance'])
def show_attendance(message):
    if f"@{message.from_user.username}" not in TEACHERS["usernames"]:
        bot.reply_to(message, "У вас нет прав.")
        return

    lessons_attendance = {}
    for entry in ATTENDANCE_LIST:
        lesson_id = entry['lesson_id']
        student_username = entry['student_username']
        present = entry['present']

        if lesson_id not in lessons_attendance:
            lessons_attendance[lesson_id] = {
                "total_students": 0,
                "present_count": 0,
                "students": []
            }

        lessons_attendance[lesson_id]["students"].append({
            "username": student_username,
            "present": present,
            "rating": entry.get("rating", None)
        })

    if not lessons_attendance:
        bot.reply_to(message, "Нет данных о посещаемости.")
        return

    text = "📊 Отчет о посещаемости:\n\n"
    for lesson_id, data in lessons_attendance.items():
        total = len(data["students"])
        present = sum(1 for s in data["students"] if s["present"])
        absent = total - present
        data["total_students"] = total
        data["present_count"] = present

        text += f"🔹 Урок ID {lesson_id}:\n"
        text += f"   ➤ Всего студентов: {total}\n"
        text += f"   ➤ Присутствовало: {present}\n"
        text += f"   ➤ Не присутствовало: {absent}\n"
        text += "   Список студентов:\n"

        for student in sorted(data["students"], key=lambda x: x["username"]):
            status = "✅ Присутствовал" if student["present"] else "❌ Не присутствовал"
            rating = f" | 📈 Оценка: {student['rating']}" if student["rating"] is not None else ""
            text += f"     - {student['username']} | {status}{rating}\n"

        text += "\n"

    bot.reply_to(message, text)

# === ЗАПУСК БОТА ===
if __name__ == "__main__":
    print("Бот запущен...")
    thread = threading.Thread(target=check_lessons)
    thread.daemon = True
    thread.start()
    bot.polling(none_stop=True)