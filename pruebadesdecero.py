"""
Парсер e-mail из био SoundCloud:
  • читает info_final.csv
  • ищет e-mail (по ключевым словам) в био каждого профиля
  • записывает адреса в 3-й столбец, остальные строки удаляет
  • сохраняет новый CSV info_final_with_emails.csv
"""

import re
import pandas as pd
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# ─── НАСТРОЙКИ ─────────────────────────────────────────────────────────────────
CSV_FILE = (
    "/Users/nikolai/Desktop/Programacion/Python/web scraping/"
    "1001Track_parcing/artist_info_scrapped/info_final_with_emails_unique_with_emails.csv"
)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

BASE_SC  = "https://soundcloud.com/"
KEYWORDS = {"promo", "demo"}
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
# ──────────────────────────────────────────────────────────────────────────────

# ─── ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ──────────────────────────────────────────────────
def accept_cookies(driver, timeout=5):
    try:
        WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
        ).click()
    except TimeoutException:
        pass


def normalize_sc_url(raw: str | None) -> str | None:
    """Возвращает полноценный URL SoundCloud или None."""
    if not isinstance(raw, str):
        return None
    txt = raw.strip()
    if not txt or txt.lower() in {"soundcloud", "na", "none", "null", "-", "n/a"}:
        return None

    low = txt.lower()
    if low.startswith(("http://", "https://")) and "soundcloud.com" in low:
        return txt

    if "soundcloud.com" in low:
        part = txt[low.index("soundcloud.com") + len("soundcloud.com") :]
        return urljoin(BASE_SC, part.lstrip("/"))

    handle = txt.lstrip("@/")
    if re.fullmatch(r"[A-Za-z0-9_\-\.]+", handle):
        return urljoin(BASE_SC, handle)

    return None


def extract_emails_from_bio(soup) -> set[str]:
    bio = (
        soup.select_one("article.infoStats div.infoStats__description")
        or soup.select_one("div.userDescription")
    )
    if not bio:
        return set()

    emails = set()
    for p in bio.find_all("p"):
        text = p.get_text(separator="\n").lower()
        if any(kw in text for kw in KEYWORDS):
            emails.update(EMAIL_RE.findall(text))
    return emails


def scrape_profile(url: str, driver) -> set[str]:
    driver.get(url)
    accept_cookies(driver)
    try:
        WebDriverWait(driver, 1).until(
            EC.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    "article.infoStats div.infoStats__description, div.userDescription",
                )
            )
        )
    except TimeoutException:
        pass
    soup = BeautifulSoup(driver.page_source, "html.parser")
    return extract_emails_from_bio(soup)


# ─── ОСНОВНОЙ СКРИПТ ──────────────────────────────────────────────────────────
def main():
    path = Path(CSV_FILE).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"CSV не найден: {path}")

    df = pd.read_csv(path, header=None, dtype=str, keep_default_na=False)
    if df.shape[1] <= 4:
        raise ValueError(f"В {path.name} меньше 5 столбцов (нашли {df.shape[1]}).")

    try:
        start = int(input(f"Введите начальную строку (0 — первая): "))
        end = int(input(f"Введите конечную строку (не включительно, максимум {len(df)}): "))
    except ValueError:
        print("Ошибка ввода. Введите целые числа.")
        return

    if start < 0 or end > len(df) or start >= end:
        print("Некорректный диапазон.")
        return

    options = Options()
    options.headless = True
    options.set_preference("general.useragent.override", USER_AGENT)
    driver = webdriver.Firefox(options=options)

    rows_to_drop = []

    try:
        for idx, raw_link in df.iloc[start:end, 4].items():
            url = normalize_sc_url(raw_link)
            if not url:
                rows_to_drop.append(idx)
                continue

            try:
                emails = scrape_profile(url, driver)
            except Exception as e:
                print(f"⚠️  {url} → {e}")
                rows_to_drop.append(idx)
                continue

            if emails:
                df.iat[idx, 2] = ", ".join(sorted(emails))
                print(f"✔ {url} → {df.iat[idx, 2]}")
            else:
                rows_to_drop.append(idx)
                print(f"✖ {url} → e-mail не найден")

    finally:
        driver.quit()

    if rows_to_drop:
        df.drop(index=rows_to_drop, inplace=True)

    df.to_csv(path, index=False, header=False)
    print(f"\n✅ Готово. Файл обновлён: {path}")
    print(f"   Строк осталось: {len(df)}")

if __name__ == "__main__":
    main()