import PyPDF2
import xml.etree.ElementTree as ET
import re
import pandas as pd
import csv

# Функция для извлечения текста из PDF
def extract_text_from_pdf(pdf_file):
    text = ""
    with open(pdf_file, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text()
    return text


import xml.etree.ElementTree as ET


def create_xml_from_text(text):
    root = ET.Element("Data")

    # Разбиваем текст на события, разделённые знаком +
    events = text.split('///')

    for event_text in events:
        event_text = event_text.strip()  # Убираем лишние пробелы и пустые строки
        if event_text:  # Пропускаем пустые строки
            # Создаем элемент для события (все данные одного события на одной строке)
            event = ET.SubElement(root, "Event")

            # Разделяем строку на колонки по символу '|'
            columns = event_text.split('|')

            # Заполняем первые 5 колонок
            for i in range(min(5, len(columns))):
                column_element = ET.SubElement(event, f"Column{i + 1}")
                column_element.text = columns[i].strip()

            # Для остальных колонок (начиная с Column6) записываем оставшиеся данные
            for i in range(5, len(columns)):
                column_index = i + 1
                column_element = ET.SubElement(event, f"Column{column_index}")
                column_element.text = columns[i].strip()

    # Записываем XML в файл
    tree = ET.ElementTree(root)
    tree.write("./BOOKS/XML/output.xml", encoding='utf-8', xml_declaration=True)



# Главная функция
def main():
    pdf_file = './BOOKS/PDF/file.pdf'  # Укажите путь к PDF файлу
    text = extract_text_from_pdf(pdf_file)

    c = text
    lines = c.split('\n')
    lines = lines[15:]
    new_text = '\n'.join(lines)
    print(new_text)
    import re

    # Исходный текст для примера
    text = new_text

    # Функция для удаления строк с нумерацией страниц
    def remove_page_numbers(text):
        text = re.sub(r"Стр\.\s*\d+\s*из\s*\d+", "", text)
        return text.strip()

    # Шаблоны для поиска
    sport_pattern = r"([А-Яа-я\s]+)\nОсновной состав"  # Спорт: находим строку перед "Основной состав"
    composition_pattern = r"(Основной состав|Молодежный \(резервный\) состав)"  # Находим состав
    event_id_pattern = r"(\d{11,})"  # Индекс мероприятия: числа с 11 и более знаками
    title_pattern = r"([А-ЯA-Z0-9\s\-\"']+)"  # Название мероприятия, включая кавычки
    description_and_class_discipline_pattern = r"(?<=title_end).*?(?=date_start)"  # Текст между title и началом первой даты
    date_pattern = r"(\d{2}\.\d{2}\.\d{4})"  # Дата
    location_pattern = r"([А-Яа-я\s,г\.\-]+)(\d+)$"  # Местоположение и индекс мероприятия
    participants_pattern = r"(\d+)$"  # Количество участников (в конце строки)
    # Функция для парсинга одного мероприятия
    def parse_event(event_text):
        # Инициализация переменных
        sport = "АВИАМОДЕЛЬНЫЙ СПОРТ"  # Первый спорт всегда будет "АВИАМОДЕЛЬНЫЙ СПОРТ"
        composition = "Основной состав"  # Начинаем с "Основной состав"
        result = []

        event_ids = re.findall(event_id_pattern, event_text)
        prev_idx = 0
        processed_event_ids = set()  # Множество обработанных индексов мероприятий

        for idx in event_ids:
            # Пропускаем индексы, которые уже были обработаны
            if idx in processed_event_ids:
                continue
            processed_event_ids.add(idx)

            # Найдем участок текста между двумя индексами
            start_idx = event_text.find(idx, prev_idx)
            end_idx = event_text.find(event_ids[event_ids.index(idx) + 1], start_idx) if event_ids.index(idx) + 1 < len(
                event_ids) else len(event_text)

            # Обрабатываем текст между этими индексами
            block_text = event_text[start_idx:end_idx]

            # Удаляем индекс мероприятия из текста блока
            block_text = block_text.replace(idx, "", 1).strip()

            # Спорт: обновляем его каждый раз, когда видим "Основной состав"
            composition_match = re.search(composition_pattern, block_text)
            if composition_match:
                sport_match = re.search(sport_pattern, block_text)
                if sport_match:
                    sport = sport_match.group(1).strip()

            # Основной состав
            composition_match = re.search(composition_pattern, block_text)
            if composition_match:
                composition = composition_match.group(1).strip()

            # Название мероприятия
            title_match = re.search(title_pattern, block_text)
            title = title_match.group(1).strip() if title_match else "Неизвестное название"
            title_end = title_match.end() if title_match else 0

            # Даты
            dates = re.findall(date_pattern, block_text)
            first_date = dates[0] if len(dates) > 0 else "Неизвестная дата"
            second_date = dates[1] if len(dates) > 1 else "Неизвестная дата"

            # Описание и класс/дисциплина
            description_start = title_end
            description_end = block_text.find(first_date) if first_date != "Неизвестная дата" else len(block_text)
            description_and_class_discipline = block_text[description_start:description_end].strip()

            # Местоположение
            location_match = re.search(location_pattern, block_text)
            if location_match:
                location = location_match.group(1).strip()

            # Количество участников
            participants_match = re.search(participants_pattern, block_text)
            if participants_match:
                participants = participants_match.group(1).strip()

            # Формируем строку
            result.append(
                f"{sport}|{composition}|{idx}|{title}|{description_and_class_discipline}|{first_date}|{second_date}|{location}|{participants}")

        return "///".join(result)

    # Удаляем номера страниц из текста
    cleaned_text = remove_page_numbers(text)

    # Парсим события
    event_info = parse_event(cleaned_text)

    print(event_info)
    create_xml_from_text(event_info)





if __name__ == "__main__":
    main()