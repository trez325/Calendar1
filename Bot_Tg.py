import telebot
from telebot import types
import xml.etree.ElementTree as ET
from datetime import datetime

bot = telebot.TeleBot('5198735526:AAHYngDdLU4ywk7bp1s6G7GB_CrOSF3o_Y0')

# Загружаем и парсим XML файл
def load_xml():
    tree = ET.parse('./BOOKS/XML/output.xml')  # Укажите путь к вашему XML файлу
    root = tree.getroot()
    events = []

    # Разбираем данные и сохраняем события в список
    for event in root.findall('Event'):
        event_data = {}
        for column in event:
            event_data[column.tag] = column.text
        events.append(event_data)

    return events

# Пагинация
PAGE_SIZE = 5  # Количество мероприятий на одной странице

# Словарь для хранения состояния пользователя
user_data = {}

# Функция для отправки списка мероприятий с пагинацией
def send_event_list_with_pagination(chat_id, events, current_page=0, filters=None, message_id=None):
    start_index = current_page * PAGE_SIZE
    end_index = start_index + PAGE_SIZE

    filtered_events = events

    # Применение фильтров
    if filters:
        filtered_events = []
        for event in events:
            match = True
            for key, value in filters.items():
                if key in event:
                    # Применяем фильтр с учетом регистра
                    if value.lower() not in event[key].lower():
                        match = False
                        break
            if match:
                filtered_events.append(event)

    # Получаем срез списка
    page_events = filtered_events[start_index:end_index]
    if not page_events:
        bot.send_message(chat_id, "Нет мероприятий на текущей странице.")
        return

    # Формируем текст для каждого мероприятия
    event_text = "Список мероприятий:\n"
    for event in page_events:
        sport = event.get('Column1', 'Неизвестно')
        composition = event.get('Column2', 'Неизвестно')
        date = event.get('Column6', 'Неизвестная дата')
        location = event.get('Column7', 'Неизвестно')
        event_text += f"{sport} | {composition} | {date} | {location}\n"

    # Inline-кнопки
    markup = types.InlineKeyboardMarkup()
    for event in page_events:
        event_id = event.get('Column3', '')  # Используем ID мероприятия для идентификации
        btn = types.InlineKeyboardButton(f"{sport} | {composition} | {date} | {location}", callback_data=f"event_{event_id}")
        markup.add(btn)

    # Пагинация (Далее и Назад)
    navigation_buttons = []
    if current_page > 0:
        navigation_buttons.append(types.InlineKeyboardButton("Назад", callback_data=f"prev_{current_page - 1}"))
    if end_index < len(filtered_events):
        navigation_buttons.append(types.InlineKeyboardButton("Далее", callback_data=f"next_{current_page + 1}"))

    markup.add(*navigation_buttons)

    # Кнопка для добавления фильтра
    add_filter_button = types.InlineKeyboardButton("Добавить фильтр", callback_data="add_filter")
    markup.add(add_filter_button)

    if message_id:
        bot.edit_message_text(event_text, chat_id, message_id, reply_markup=markup)
    else:
        bot.send_message(chat_id, event_text, reply_markup=markup)

# Функция для отправки доступных фильтров для выбора
def send_filter_options(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    btn1 = types.KeyboardButton('Вид спорта')
    btn2 = types.KeyboardButton('Дисциплина')
    btn3 = types.KeyboardButton('Программа')
    btn4 = types.KeyboardButton('Место проведения')
    btn5 = types.KeyboardButton('Количество участников')
    btn6 = types.KeyboardButton('Пол, возрастная группа')
    btn7 = types.KeyboardButton('Сроки проведения')
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6, btn7)
    bot.send_message(message.chat.id, 'Выберите фильтр для мероприятий:', reply_markup=markup)

# Функция для отправки списка доступных значений для фильтра
def send_filter_values(message, filter_name, values):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for value in values:
        markup.add(types.KeyboardButton(value))
    back_button = types.KeyboardButton("Назад")
    markup.add(back_button)
    bot.send_message(message.chat.id, f'Выберите {filter_name}:', reply_markup=markup)

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def start(message):
    user_data[message.chat.id] = {'filters': {}, 'page': 0}  # Сброс состояния пользователя
    events = load_xml()  # Загружаем все мероприятия
    send_event_list_with_pagination(message.chat.id, events)

# Обработчик нажатия кнопок фильтров
@bot.message_handler(func=lambda message: message.text in ['Вид спорта', 'Дисциплина', 'Программа', 'Место проведения', 'Количество участников', 'Пол, возрастная группа', 'Сроки проведения'])
def handle_filter_selection(message):
    filter_name = message.text
    events = load_xml()

    # Сканирование всех столбцов для получения уникальных значений для фильтра
    if filter_name == 'Вид спорта':
        values = list(set(event['Column1'] for event in events if 'Column1' in event))
    elif filter_name == 'Дисциплина':
        values = list(set(event['Column2'] for event in events if 'Column2' in event))
    elif filter_name == 'Программа':
        values = list(set(event['Column4'] for event in events if 'Column4' in event))
    elif filter_name == 'Место проведения':
        values = list(set(event['Column8'] for event in events if 'Column8' in event))
    elif filter_name == 'Количество участников':
        values = [str(i) for i in set(int(event['Column9']) for event in events if 'Column9' in event)]  # Преобразуем в строки для удобства
    elif filter_name == 'Пол, возрастная группа':
        values = ['Мужской', 'Женский']  # Разделение по полу
    elif filter_name == 'Сроки проведения':
        values = ['Выбрать даты']  # Для календаря позже

    send_filter_values(message, filter_name, values)

# Обработчик выбора фильтра
@bot.message_handler(func=lambda message: message.text not in ['Вид спорта', 'Дисциплина', 'Программа', 'Место проведения', 'Количество участников', 'Пол, возрастная группа', 'Сроки проведения'])
def handle_filter_value_selection(message):
    user_input = message.text
    events = load_xml()

    # Применяем фильтр
    filters = user_data[message.chat.id]['filters']
    filters[message.text] = user_input.lower()  # Применяем фильтр для других параметров

    user_data[message.chat.id]['filters'] = filters

    # Отправляем отфильтрованный список с пагинацией
    send_event_list_with_pagination(message.chat.id, events, filters=filters, current_page=user_data[message.chat.id]['page'])

# Обработчик нажатия на мероприятие
@bot.callback_query_handler(func=lambda call: call.data.startswith('event_'))
def handle_event_details(call):
    event_id = call.data.split('_')[1]  # Получаем ID мероприятия
    events = load_xml()
    selected_event = next((event for event in events if event.get('Column3') == event_id), None)

    if selected_event:
        send_event_details(call.message.chat.id, selected_event)

    bot.delete_message(call.message.chat.id, call.message.message_id)

# Обработчик для пагинации
@bot.callback_query_handler(func=lambda call: call.data.startswith('next_') or call.data.startswith('prev_'))
def handle_pagination(call):
    events = load_xml()
    filters = user_data[call.message.chat.id]['filters']  # Получаем текущие фильтры пользователя
    current_page = int(call.data.split('_')[1])

    # Обновляем страницу в состоянии
    user_data[call.message.chat.id]['page'] = current_page

    # Отправляем новый список с пагинацией
    send_event_list_with_pagination(call.message.chat.id, events, current_page=current_page, filters=filters, message_id=call.message.message_id)

# Обработчик нажатия кнопки "Добавить фильтр"
@bot.callback_query_handler(func=lambda call: call.data == "add_filter")
def handle_add_filter(call):
    send_filter_options(call.message)

# Функция для отправки подробной информации о мероприятии
def send_event_details(chat_id, event):
    event_text = f"""
    **Вид спорта:** {event['Column1']}
    **Дисциплина:** {event['Column2']}
    **Дата начала:** {event['Column6']}
    **Дата окончания:** {event['Column7']}
    **Место проведения:** {event['Column8']}
    **Количество участников:** {event['Column9']}
    **Описание:** {event['Column4']}
    """
    back_button = types.InlineKeyboardButton("Назад", callback_data="back_to_list")
    markup = types.InlineKeyboardMarkup()
    markup.add(back_button)

    bot.send_message(chat_id, event_text, reply_markup=markup)

# Обработчик кнопки "Назад" из подробностей мероприятия
@bot.callback_query_handler(func=lambda call: call.data == "back_to_list")
def handle_back_to_list(call):
    events = load_xml()
    filters = user_data[call.message.chat.id]['filters']
    send_event_list_with_pagination(call.message.chat.id, events, filters=filters, current_page=user_data[call.message.chat.id]['page'])

# Запуск бота
bot.polling(none_stop=True)