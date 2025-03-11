import os
import time
from datetime import datetime
import subprocess

download_script_path = "DownloadFile.py"
parse_script_path = "2ParsePDF.py"
scheduled_time = "00:00"

def is_time_to_run(scheduled_time):
    """Проверяет, совпадает ли текущее время с запланированным."""
    current_time = datetime.now().strftime("%H:%M")
    return current_time == scheduled_time

def run_script(script_path):
    """Запускает указанный скрипт."""
    try:
        # Используем subprocess для запуска скрипта
        subprocess.run(["python", script_path], check=True)
        print(f"[{datetime.now()}] Скрипт {script_path} успешно выполнен.")
    except Exception as e:
        print(f"[{datetime.now()}] Ошибка при выполнении скрипта: {e}")

# Основной цикл
if __name__ == "__main__":
    print("Запущен скрипт для планирования выполнения задачи.")
    while True:
        try:
            if is_time_to_run(scheduled_time):
                print(f"[{datetime.now()}] Наступило время для запуска скрипта.")
                run_script(download_script_path)
                run_script(parse_script_path)
                time.sleep(60)  # Ждем 60 секунд, чтобы избежать повторного выполнения в ту же минуту
            else:
                time.sleep(10)  # Проверяем каждые 10 секунд
        except KeyboardInterrupt:
            print("Скрипт остановлен пользователем.")
            break
