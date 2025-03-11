import requests
import re
import time
import random
import warnings

warnings.filterwarnings("ignore", category=requests.packages.urllib3.exceptions.InsecureRequestWarning)

url = "https://www.minsport.gov.ru/activity/government-regulation/edinyj-kalendarnyj-plan/"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
    'Connection': 'keep-alive'
}

session = requests.Session()
session.headers.update(headers)

response = session.get(url, verify=False)

if response.status_code == 200:
    print("Страница успешно загружена!")

    pdf_pattern = re.compile(r'http://storage\.minsport\.gov\.ru/cms-uploads/cms/II_chast_EKP_[^"]+\.pdf')
    pdf_links = pdf_pattern.findall(response.text)

    if pdf_links:
        pdf_url = pdf_links[0]  # Берем только первую найденную ссылку
        print(f"Найдена ссылка на PDF: {pdf_url}")

        for attempt in range(5):
            try:
                pdf_response = session.get(pdf_url, verify=False, headers=headers)

                if pdf_response.status_code == 200:
                    with open('./BOOKS/PDF/file.pdf', 'wb') as f:
                        f.write(pdf_response.content)
                    print("Файл успешно скачан!")
                    break
                else:
                    print(f"Ошибка при скачивании файла (попытка {attempt + 1}): {pdf_response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"Произошла ошибка при скачивании файла (попытка {attempt + 1}): {str(e)}")

            time.sleep(random.uniform(5, 10))
    else:
        print("Не удалось найти ссылку на PDF файл.")
else:
    print(f"Ошибка при загрузке страницы: {response.status_code}")
