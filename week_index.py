from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from bs4 import BeautifulSoup
import requests 
import re
import csv
import random

num = 1
week = f"{num}"
index = ""

headers = {
'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
'accept-language': 'en-US,en;q=0.9',
'priority': 'u=0, i',
'sec-fetch-dest': 'document',
'sec-fetch-mode': 'navigate',
'sec-fetch-site': 'none',
'sec-fetch-user': '?1',
'upgrade-insecure-requests': '1',
'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Mobile Safari/537.36',
}


def stable_fetch(url, headers, retries=3, delay=2):
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200 and len(response.text) > 1000:  # базовая проверка
                time.sleep(delay)  # дожидаемся полной загрузки контента
                return BeautifulSoup(response.text, "html.parser")
            else:
                print(f"[!] Попытка {attempt+1}: Недостаточный HTML-контент или плохой статус: {response.status_code}")
        except Exception as e:
            print(f"[!] Попытка {attempt+1}: Ошибка при запросе {url} → {e}")
        time.sleep(delay)
    return None

options = Options()
options.headless = False

driver = webdriver.Firefox(options=options)
driver.get("about:blank")  
time.sleep(3)

#iframes = driver.find_elements(By.TAG_NAME, "iframe")
#print(f"[DEBUG] Найдено iframe: {len(iframes)}")

#try:
#    iframe = driver.find_elements(By.TAG_NAME, "iframe")[4]
#    driver.switch_to.frame(iframe)
#    print("[INFO] Переключились в iframe[4]")
#
 #   WebDriverWait(driver, 10).until(
 #       EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[title="Accept"]'))
 #   ).click()
 #   print("[INFO] Кнопка 'Accept' нажата.")
#except Exception as e:
#    print(f"[ERROR] Не удалось нажать кнопку 'Accept': {e}")

driver.switch_to.default_content()

with open("artist_info.csv", mode="w", newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerow(["Nickname", "Genre", "Email", "Instagram", "SoundCloud"])
    # сначала 2024, потом 2025
    week_years = [
        #(2024, range(47, 53)),  # 28–52 неделя 2024
        (2025, range(13, 29))    # 1–28 неделя 2025
                ]
    for year, weeks in week_years:
        for week_num in weeks:
            week = f"{week_num:02d}"
            for index_num in range(1, 4):  # index, index2, index3...
                index_suffix = "" if index_num == 0 else str(index_num)
                base_url = f"https://www.1001tracklists.com/charts/weekly/{year}/{week}/index{index_suffix}.html"
                print(f"[DEBUG] Переход на страницу чарта: {base_url}")
                driver.get(base_url)
                time.sleep(3)

                soup = BeautifulSoup(driver.page_source, 'lxml')
                accounts = soup.find_all('div', class_=lambda x: x and 'bItm' in x and 'oItm' in x)
                print(f"[DEBUG] Найдено аккаунтов: {len(accounts)}")

                for account in accounts:
                    try:
                        profile_link = account.find('div', class_='ml5').find('div', class_='fontL').find('a')['href']
                        full_url = "https://www.1001tracklists.com" + profile_link

                        driver.get(full_url)
                        time.sleep(3)

                        # Попытка нажать Accept, если он есть
                        try:
                            iframe = driver.find_elements(By.TAG_NAME, "iframe")[4]
                            driver.switch_to.frame(iframe)
                            WebDriverWait(driver, 3).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[title="Accept"]'))
                            ).click()
                            print("[INFO] Кнопка 'Accept' нажата.")
                            driver.switch_to.default_content()
                        except:
                            driver.switch_to.default_content()

                        soup2 = BeautifulSoup(driver.page_source, "html.parser")
                        if not soup2:
                            print(f"[!] Пропуск профиля — не удалось загрузить: {full_url}")
                            continue

                        text = account.find('div', class_='ml5').find('div', class_='fontL').find('a').text
                        parts = re.split(r'\s*[-@]\s*', text)
                        Nickname = parts[0].strip()

                        # Жанр
                        genre = None
                        tags = soup2.find_all("div", class_="h")
                        for tag in tags:
                            if tag.text.strip() == "Genre":
                                next_div = tag.find_next_sibling("div")
                                if next_div and "ptb5" in next_div.get("class", []):
                                    genre = next_div.text.strip()
                                break

                        # Соцсети
                        soundcloud_link = None
                        instagram_link = None
                        email = None

                        for a in soup2.find_all("a", href=True):
                            href = a["href"]
                            if "soundcloud.com" in href and "1001tracklists" not in href:
                                soundcloud_link = href
                            if "instagram.com" in href and "1001tracklists" not in href:
                                instagram_link = href

                        writer.writerow([Nickname, genre, email, instagram_link, soundcloud_link])
                        print(f"[✔] Добавлен: {Nickname} | Жанр: {genre}")
                        time.sleep(1)

                    except Exception as e:
                        print(f"[!] Ошибка при обработке артиста: {e}")
                        continue

driver.quit()

#response = requests.get(base_url, headers=headers)