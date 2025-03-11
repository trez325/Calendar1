import telebot
from telebot import types
import xml.etree.ElementTree as ET
from datetime import datetime
import threading
import time
#РАБОЧИЙ БОТ
# Инициализация бота
bot = telebot.TeleBot('5198735526:AAHYngDdLU4ywk7bp1s6G7GB_CrOSF3o_Y0')

# Загрузка данных из XML
events = []
user_watchlist = {}
@bot.message_handler(func=lambda message: message.text == 'Просмотреть отслеживаемые 📌')
def handle_watchlist_request(message):
    show_watchlist(message)

def load_events():
    global events
    tree = ET.parse('./BOOKS/XML/output.xml')
    root = tree.getroot()
    for event in root.findall('Event'):
        events.append({
            "id": event.find('Column3').text if event.find('Column3') is not None else "Не указано",
            "sport": event.find('Column1').text if event.find('Column1') is not None else "Не указано",
            "name": event.find('Column2').text if event.find('Column2') is not None else "Не указано",
            "category": event.find('Column5').text if event.find('Column5') is not None else "Не указано",
            "dates": (
                event.find('Column6').text if event.find('Column6') is not None else "Не указано",
                event.find('Column7').text if event.find('Column7') is not None else "Не указано"
            ),
            "location": (
                event.find('Column8').text.strip()
                if event.find('Column8') is not None and event.find('Column8').text is not None
                else "Не указано"
            ),
            "participants": event.find('Column9').text if event.find('Column9') is not None else "Не указано"
        })

load_events()

# Хранение состояния пользователей
user_states = {}

# Пагинация
PAGE_SIZE = 5

def send_notifications():
    while True:
        current_date = datetime.now().date()
        for chat_id, state in user_states.items():
            watchlist = state.get("watchlist", [])
            for event in watchlist:
                event_start_date = datetime.strptime(event["dates"][0], "%d.%m.%Y").date()
                days_left = (event_start_date - current_date).days

                if 1 <= days_left <= 7:  # Если до мероприятия осталось 1–7 дней
                    bot.send_message(
                        chat_id,
                        (
                            f"📢 Напоминание о мероприятии!\n\n"
                            f"🎯 **Название:** {event['name']}\n"
                            f"📅 **Дата начала:** {event['dates'][0]}\n"
                            f"📍 **Место:** {event['location']}\n"
                            f"👥 **Количество участников:** {event['participants']}\n\n"
                            f"⏳ До начала осталось: {days_left} дней."
                        ),
                        parse_mode="Markdown"
                    )
        time.sleep(86400)  # Проверяем раз в сутки


# Отправка доступных фильтров
@bot.callback_query_handler(func=lambda call: call.data.startswith("remove_watchlist_"))
def remove_from_watchlist(call):
    event_id = call.data.split("_")[2]
    watchlist = user_states[call.message.chat.id].get("watchlist", [])

    # Удаляем мероприятие из списка
    updated_watchlist = [event for event in watchlist if event["id"] != event_id]
    user_states[call.message.chat.id]["watchlist"] = updated_watchlist

    # Обновляем сообщение со списком отслеживаемых
    bot.answer_callback_query(call.id, "Мероприятие удалено из списка отслеживаемых.")
    show_watchlist(call.message)

def send_filter_options(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    btn1 = types.KeyboardButton('Вид спорта')
    btn2 = types.KeyboardButton('Дисциплина')
    btn3 = types.KeyboardButton('Место проведения')
    btn4 = types.KeyboardButton('Количество участников')
    btn5 = types.KeyboardButton('Пол, возрастная группа')
    btn6 = types.KeyboardButton('Дата проведения')
    btn_reset = types.KeyboardButton('Сбросить фильтры')  # Кнопка сброса фильтров
    btn_watchlist = types.KeyboardButton('Просмотреть отслеживаемые 📌')  # Новая кнопка для просмотра отслеживаемых мероприятий
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6)
    markup.add(btn_watchlist, btn_reset)  # Добавляем кнопку отслеживаемых и сброса фильтров
    bot.send_message(message.chat.id, 'Выберите фильтр для мероприятий или воспользуйтесь дополнительными функциями:',reply_markup=markup)

# Отправка списка значений для выбранного фильтра
def send_filter_values(message, filter_name, values):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for value in values:
        markup.add(types.KeyboardButton(value))
    back_button = types.KeyboardButton("Назад")
    markup.add(back_button)
    bot.send_message(message.chat.id, f'Выберите {filter_name}:', reply_markup=markup)


# Сканирование всех столбцов для получения уникальных значений для фильтра
def get_filter_values(filter_name):
    if filter_name == 'Вид спорта':
        return list(set(event['sport'] for event in events))
    elif filter_name == 'Дисциплина':
        return list(set(event['name'] for event in events))
    elif filter_name == 'Программа':
        return []  # Вместо списка с вариантами программ возвращаем пустой список
    elif filter_name == 'Место проведения':
        return []  # Место проведения не имеет фиксированных значений, так что просто оставляем пустым
    elif filter_name == 'Количество участников':
        return []  # Здесь будет обработка ввода числа
    elif filter_name == 'Пол, возрастная группа':
        return ['Мужской', 'Женский']
    elif filter_name == 'Дата проведения':
        return ['Выбрать даты']


# Функция для фильтрации мероприятий по количеству участников
def filter_by_participants(events, min_participants):
    filtered_events = []
    for event in events:
        try:
            participants = int(event['participants'])
            if participants >= min_participants:
                filtered_events.append(event)
        except ValueError:
            # В случае если в данных не указано количество участников или оно не является числом
            continue
    return filtered_events


# Функция для фильтрации мероприятий по месту проведения
def filter_by_location(events, location):
    filtered_events = []
    for event in events:
        # Поиск места без учета регистра
        if location.lower() in event['location'].lower():
            filtered_events.append(event)
    return filtered_events


# Функция для фильтрации по полу (для сохранения совместимости с предыдущими фильтрами)
def filter_by_gender(events, gender):
    keywords = {
        "Мужской": ["мужчины", "юноши", "мальчики", "юниоры"],
        "Женский": ["женщины", "девушки", "девочки", "юниорки"]
    }
    filtered_events = []
    for event in events:
        category = event.get('category', '').lower()
        if any(keyword in category for keyword in keywords.get(gender, [])):
            filtered_events.append(event)
    return filtered_events


# Обработка команды /start
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    if user_id not in user_states:
        user_states[message.chat.id] = {"filters": {}, "page": 0}

    welcome_text = (
         "👋 **Добро пожаловать в бот для поиска спортивных мероприятий!** 🏅\n\n"
        "Этот бот создан, чтобы помочь вам **легко** находить информацию о предстоящих спортивных мероприятиях. "
        "Забудьте о громоздких документах на 2500+ страниц — теперь всё под рукой, с удобными фильтрами и функциями!\n\n"
        "✨ **Что может бот:**\n"
        "• 🏋️‍♂️ Искать мероприятия по фильтрам:\n"
        "  - Вид спорта\n"
        "  - Дисциплина\n"
        "  - 📍 Место проведения\n"
        "  - 👥 Количество участников\n"
        "  - 🧑‍🤝‍🧑 Пол и возрастная группа\n"
        "  - 📅 Дата проведения\n"
        "• 📌 **Добавлять мероприятия в список отслеживаемых**\n"
        "• 🗂️ Просматривать свой список отслеживаемых мероприятий\n"
        "• 🔔 Получать **уведомления о мероприятиях**, которые начинаются в ближайшие дни\n\n"
        "💡 **Как это работает:**\n"
        "1️⃣ Выберите нужные фильтры.\n"
        "2️⃣ Найдите подходящие мероприятия.\n"
        "3️⃣ Добавьте их в список отслеживаемых, чтобы не пропустить!\n\n"
        "📲 Чтобы начать, выберите фильтры или просто начните поиск.\n"
    )

    bot.send_message(message.chat.id, welcome_text, parse_mode='Markdown')
    send_filter_options(message)


# Обработка выбора фильтра
@bot.message_handler(func=lambda message: message.text in ['Вид спорта', 'Дисциплина', 'Программа', 'Место проведения', 'Количество участников', 'Пол, возрастная группа', 'Дата проведения', 'Сбросить фильтры'])
def handle_filter_selection(message):
    if message.text == 'Сбросить фильтры':  # Обработка сброса фильтров
        user_states[message.chat.id]["filters"] = {}
        user_states[message.chat.id]["page"] = 0
        send_filter_options(message)
        return

    filter_name = message.text
    user_states[message.chat.id]["selected_filter"] = filter_name

    # Для фильтра "Количество участников" просим ввести число
    if filter_name == 'Количество участников':
        bot.send_message(message.chat.id, "Введите минимальное количество участников:")
        user_states[message.chat.id]["waiting_for_participants"] = True
    elif filter_name == 'Место проведения':
        bot.send_message(message.chat.id, "Введите место проведения:")
        user_states[message.chat.id]["waiting_for_location"] = True
    elif filter_name == 'Дата проведения':
        bot.send_message(message.chat.id, "Введите дату через календарь (формат: ДД.ММ.ГГГГ):")
        user_states[message.chat.id]["waiting_for_dates"] = True
    else:
        values = get_filter_values(filter_name)
        send_filter_values(message, filter_name, values)


# Обработка ввода значения для фильтра
@bot.message_handler(func=lambda message: message.text not in ['Вид спорта', 'Дисциплина', 'Программа', 'Место проведения', 'Количество участников', 'Пол, возрастная группа', 'Дата проведения', 'Назад'])
def handle_value_selection(message):
    filter_name = user_states[message.chat.id].get('selected_filter', '')
    selected_value = message.text
    user_states[message.chat.id]["filters"][filter_name] = selected_value

    # Если пользователь вводит количество участников
    if user_states[message.chat.id].get("waiting_for_participants"):
        try:
            min_participants = int(selected_value)
            user_states[message.chat.id]["filters"]["Количество участников"] = min_participants
            user_states[message.chat.id]["waiting_for_participants"] = False
        except ValueError:
            bot.send_message(message.chat.id, "Пожалуйста, введите корректное число.")
            return

    # Если пользователь вводит место проведения
    if user_states[message.chat.id].get("waiting_for_location"):
        user_states[message.chat.id]["filters"]["Место проведения"] = selected_value
        user_states[message.chat.id]["waiting_for_location"] = False

    # Если пользователь вводит дату
    if user_states[message.chat.id].get("waiting_for_dates"):
        try:
            # Проверка правильности формата даты
            selected_date = datetime.strptime(selected_value, "%d.%m.%Y")
            user_states[message.chat.id]["filters"]["Дата проведения"] = selected_date
            user_states[message.chat.id]["waiting_for_dates"] = False
        except ValueError:
            bot.send_message(message.chat.id, "Пожалуйста, введите дату в формате ДД.ММ.ГГГГ.")
            return

    # Фильтрация мероприятий по введенному значению
    filtered_events = events
    for key, value in user_states[message.chat.id]["filters"].items():
        if key == 'Место проведения':
            filtered_events = filter_by_location(filtered_events, value)
        elif key == 'Количество участников':
            filtered_events = filter_by_participants(filtered_events, value)
        elif key == 'Пол, возрастная группа':
            filtered_events = filter_by_gender(filtered_events, value)
        elif key == 'Дата проведения':
            selected_date = user_states[message.chat.id]["filters"].get("Дата проведения")
            filtered_events = [event for event in filtered_events if selected_date >= datetime.strptime(event['dates'][0], "%d.%m.%Y") and selected_date <= datetime.strptime(event['dates'][1], "%d.%m.%Y")]
        else:
            filtered_events = [event for event in filtered_events if value.lower() in str(event).lower()]

    # Отправка отфильтрованных мероприятий
    send_event_list(message.chat.id, filtered_events)


# Отправка списка мероприятий с редактированием сообщений
def send_event_list(chat_id, filtered_events, page=0, message=None):
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_events = filtered_events[start:end]

    if not page_events:
        bot.send_message(chat_id, "❌ Мероприятий по заданным фильтрам не найдено.")
        return

    text = "📅 *Список мероприятий:*\n\n" + "\n".join([f"{i + 1}. *{event['name']}*\n{event['dates'][0]} - {event['dates'][1]}\n📍 {event['location']}\n👥 {event['participants']} участников"
                      for i, event in enumerate(page_events)])

    markup = types.InlineKeyboardMarkup()
    if page > 0:
        markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data=f"page_{page - 1}"))
    if end < len(filtered_events):
        markup.add(types.InlineKeyboardButton("Далее ▶️", callback_data=f"page_{page + 1}"))
    for event in page_events:
        markup.add(types.InlineKeyboardButton(f"Подробнее 📑: {event['name']}", callback_data=f"details_{event['id']}"))
    markup.add(types.InlineKeyboardButton("🔍 Главное меню", callback_data="add_filter"))

    if message:
        bot.edit_message_text(
            text,
            chat_id=chat_id,
            message_id=message.message_id,
            reply_markup=markup,
            parse_mode='Markdown'
        )
    else:
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith("details_"))
def event_details(call):
    event_id = call.data.split("_")[1]
    event = next((e for e in events if e["id"] == event_id), None)

    if event:
        text = (
            f"🎯 **Название:** {event['name']}\n"
            f"🏅 **Вид спорта:** {event['sport']}\n"
            f"📅 **Даты:** {event['dates'][0]} - {event['dates'][1]}\n"
            f"📍 **Место:** {event['location']}\n"
            f"👥 **Количество участников:** {event['participants']}\n"
            f"🔖 **Категория:** {event['category']}\n"
            f"🆔 **ID мероприятия:** {event['id']}\n"
        )

        # Получаем текущую страницу из callback-данных
        current_page = int(call.data.split("_")[2]) if "_" in call.data else 0

        # Кнопки для добавления в отслеживаемое и возврата к списку
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(
                "➕ Добавить в отслеживаемое", callback_data=f"watchlist_{event['id']}"
            )
        )
        markup.add(
            types.InlineKeyboardButton(
                "◀️ Назад", callback_data=f"back_to_list_{current_page}"
            )
        )

        # Редактируем текущее сообщение
        bot.edit_message_text(
            text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=markup,
            parse_mode="Markdown"
        )
    else:
        bot.answer_callback_query(call.id, "❌ Мероприятие не найдено.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("back_to_list_"))
def back_to_list(call):
    # Извлекаем номер страницы из callback-данных
    page = int(call.data.split("_")[3])

    # Получаем текущие фильтры пользователя
    filters = user_states[call.message.chat.id].get("filters", {})

    # Фильтруем мероприятия
    filtered_events = events
    for key, value in filters.items():
        if key == 'Место проведения':
            filtered_events = filter_by_location(filtered_events, value)
        elif key == 'Количество участников':
            filtered_events = filter_by_participants(filtered_events, value)
        elif key == 'Пол, возрастная группа':
            filtered_events = filter_by_gender(filtered_events, value)
        elif key == 'Дата проведения':
            selected_date = filters.get("Дата проведения")
            filtered_events = [event for event in filtered_events if selected_date >= datetime.strptime(event['dates'][0], "%d.%m.%Y") and selected_date <= datetime.strptime(event['dates'][1], "%d.%m.%Y")]
        else:
            filtered_events = [event for event in filtered_events if value.lower() in str(event).lower()]

    # Отправляем обновленный список мероприятий с сохранением страницы
    send_event_list(call.message.chat.id, filtered_events, page, call.message)

# В функции send_event_list добавляем передачу номера страницы в callback-данные
def send_event_list(chat_id, filtered_events, page=0, message=None):
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_events = filtered_events[start:end]

    if not page_events:
        bot.send_message(chat_id, "❌ Мероприятий по заданным фильтрам не найдено.")
        return

    text = "📅 *Список мероприятий:*\n\n" + "\n".join([f"{i + 1}. *{event['name']}*\n{event['dates'][0]} - {event['dates'][1]}\n📍 {event['location']}\n👥 {event['participants']} участников"
                      for i, event in enumerate(page_events)])

    markup = types.InlineKeyboardMarkup()
    if page > 0:
        markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data=f"page_{page - 1}"))
    if end < len(filtered_events):
        markup.add(types.InlineKeyboardButton("Далее ▶️", callback_data=f"page_{page + 1}"))
    for event in page_events:
        # Передаем номер страницы в callback-данные
        markup.add(types.InlineKeyboardButton(f"Подробнее 📑: {event['name']}", callback_data=f"details_{event['id']}_{page}"))
    markup.add(types.InlineKeyboardButton("🔍 Главное меню", callback_data="add_filter"))

    if message:
        bot.edit_message_text(
            text,
            chat_id=chat_id,
            message_id=message.message_id,
            reply_markup=markup,
            parse_mode='Markdown'
        )
    else:
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode='Markdown')

# Обработка кнопок пагинации
@bot.callback_query_handler(func=lambda call: call.data.startswith("page_"))
def page_navigation(call):
    page = int(call.data.split("_")[1])
    filters = user_states[call.message.chat.id].get("filters", {})

    # Фильтруем мероприятия
    filtered_events = events
    for key, value in filters.items():
        if key == 'Место проведения':
            filtered_events = filter_by_location(filtered_events, value)
        elif key == 'Количество участников':
            filtered_events = filter_by_participants(filtered_events, value)
        elif key == 'Пол, возрастная группа':
            filtered_events = filter_by_gender(filtered_events, value)
        elif key == 'Дата проведения':
            selected_date = filters.get("Дата проведения")
            filtered_events = [event for event in filtered_events if selected_date >= datetime.strptime(event['dates'][0], "%d.%m.%Y") and selected_date <= datetime.strptime(event['dates'][1], "%d.%m.%Y")]
        else:
            filtered_events = [event for event in filtered_events if value.lower() in str(event).lower()]

    # Отправляем обновленный список мероприятий
    send_event_list(call.message.chat.id, filtered_events, page, call.message)
@bot.callback_query_handler(func=lambda call: call.data.startswith("watchlist_"))
@bot.callback_query_handler(func=lambda call: call.data.startswith("watchlist_"))
def add_to_watchlist(call):
    event_id = call.data.split("_")[1]
    event = next((e for e in events if e["id"] == event_id), None)

    if event:
        watchlist = user_states[call.message.chat.id].get("watchlist", [])
        if event not in watchlist:
            watchlist.append(event)
            user_states[call.message.chat.id]["watchlist"] = watchlist
            bot.answer_callback_query(call.id, "✅ Добавлено в отслеживаемое!")
        else:
            bot.answer_callback_query(call.id, "⚠️ Это мероприятие уже в списке отслеживаемых.")
    else:
        bot.answer_callback_query(call.id, "❌ Мероприятие не найдено.")



@bot.message_handler(commands=['watchlist'])
def show_watchlist(message):
    watchlist = user_states[message.chat.id].get("watchlist", [])

    if not watchlist:
        bot.send_message(message.chat.id, "🗂️ Ваш список отслеживаемых мероприятий пуст.")
        return

    text = "📋 **Ваш список отслеживаемых мероприятий:**\n\n"
    for i, event in enumerate(watchlist, start=1):
        text += (
            f"{i}. 🎯 **Название:** {event['name']}\n"
            f"🏅 **Вид спорта:** {event['sport']}\n"
            f"📅 **Даты:** {event['dates'][0]} - {event['dates'][1]}\n"
            f"📍 **Место:** {event['location']}\n"
            f"🆔 **ID:** {event['id']}\n\n"  # Добавляем ID
        )

    # Кнопки для удаления мероприятий из отслеживаемого списка
    markup = types.InlineKeyboardMarkup()
    for event in watchlist:
        markup.add(
            types.InlineKeyboardButton(
                f"❌ Удалить: {event['name']}",
                callback_data=f"remove_watchlist_{event['id']}"
            )
        )

    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

# Обработка кнопки "Добавить фильтр"
@bot.callback_query_handler(func=lambda call: call.data == "add_filter")
def add_filter(call):
    send_filter_options(call.message)


# Обработка кнопок пагинации

@bot.callback_query_handler(func=lambda call: call.data.startswith("page_"))
def page_navigation(call):
    page = int(call.data.split("_")[1])
    filtered_events = events
    for key, value in user_states[call.message.chat.id]["filters"].items():
        if key == 'Место проведения':
            filtered_events = filter_by_location(filtered_events, value)
        elif key == 'Количество участников':
            filtered_events = filter_by_participants(filtered_events, value)
        elif key == 'Пол, возрастная группа':
            filtered_events = filter_by_gender(filtered_events, value)
        elif key == 'Дата проведения':
            selected_date = user_states[call.message.chat.id]["filters"].get("Дата проведения")
            filtered_events = [event for event in filtered_events if selected_date >= datetime.strptime(event['dates'][0], "%d.%m.%Y") and selected_date <= datetime.strptime(event['dates'][1], "%d.%m.%Y")]
        else:
            filtered_events = [event for event in filtered_events if value.lower() in str(event).lower()]
    send_event_list(call.message.chat.id, filtered_events, page, call.message)


notification_thread = threading.Thread(target=send_notifications)
notification_thread.daemon = True  # Чтобы поток завершался при остановке скрипта
notification_thread.start()

bot.polling(none_stop=True)
