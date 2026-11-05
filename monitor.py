import os
import re
import requests
from playwright.sync_api import Playwright, sync_playwright

# Дату можно переопределить через переменные окружения (см. ниже)
DATE_MONTH_TEXT = os.getenv("DATE_MONTH_TEXT", "ноября, чт")
DATE_CELL_NAME = os.getenv("DATE_CELL_NAME", "Fri Nov 06")


def send_telegram_alert(message: str) -> None:
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("ОШИБКА: не заданы TELEGRAM_TOKEN или TELEGRAM_CHAT_ID")
        return
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": message},
            timeout=30,
        )
        r.raise_for_status()
        print("✅ Уведомление отправлено в Telegram")
    except Exception as e:
        print(f"❌ Ошибка Telegram: {e}")


def check_available_seats(page) -> list[dict]:
    """Возвращает список рейсов со свободными местами."""
    available = []
    blocks = page.locator(".booking-trip")

    for i in range(blocks.count()):
        block = blocks.nth(i)
        try:
            seats_el = block.locator(".booking-trip-price-block-text-3").first
            seats_text = seats_el.inner_text(timeout=2000).strip()
        except Exception:
            continue

        # "нет мест" — пропускаем
        if "нет мест" in seats_text.lower():
            continue

        # Извлекаем число мест
        match = re.search(r"(\d+)\s*мест", seats_text.lower())
        if not match:
            continue
        if int(match.group(1)) <= 0:
            continue

        # Время отправления
        try:
            time_text = block.locator(".booking-trip-time").first.inner_text(timeout=1000)
        except Exception:
            time_text = "?"

        available.append({"time": time_text, "seats": seats_text})

    return available


def run(playwright: Playwright) -> None:
    # headless=true для GitHub Actions, false для локальной отладки
    headless = os.getenv("HEADLESS", "true").lower() != "false"
    browser = playwright.chromium.launch(headless=headless)
    context = browser.new_context()
    page = context.new_page()

    try:
        print(f"→ Открываю сайт (headless={headless})")
        page.goto("https://minskslonim.by/", timeout=60000)

        # Выбор маршрута и даты
        page.get_by_text("Куда", exact=True).click()
        page.get_by_text("Слоним").click()
        page.get_by_text(DATE_MONTH_TEXT).click()
        page.get_by_role("gridcell", name=DATE_CELL_NAME).click()

        # Ждём загрузки блоков с рейсами
        page.wait_for_selector(".booking-trip", timeout=30000)
        page.wait_for_timeout(2000)  # добираем возможные поздние подгрузки

        available = check_available_seats(page)

        if available:
            lines = [f"🚐 {a['time']} — {a['seats']}" for a in available]
            message = (
                f"Свободные места Минск → Слоним ({DATE_CELL_NAME}):\n\n"
                + "\n".join(lines)
                + "\n\nhttps://minskslonim.by/"
            )
            print(message)
            send_telegram_alert(message)
        else:
            print("Свободных мест нет")

    except Exception as e:
        print(f"❌ Ошибка выполнения: {e}")
    finally:
        context.close()
        browser.close()


with sync_playwright() as playwright:
    run(playwright)
