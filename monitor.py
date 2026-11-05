import os
import requests
from playwright.sync_api import sync_playwright

# --- Настройки ---
# URL страницы, где происходит поиск (замените на актуальный)
SEARCH_URL = "https://minskslonim.by/" 
# Элемент, появление которого означает, что места есть (нужно уточнить)
# Например, это может быть кнопка "Забронировать" или текст "Свободно"
TARGET_SELECTOR = "text=Забронировать" 

def send_telegram_alert(message: str):
    """Отправляет сообщение в Telegram."""
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Ошибка: не заданы TELEGRAM_TOKEN или TELEGRAM_CHAT_ID")
        return
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
        print("Уведомление отправлено в Telegram.")
    except Exception as e:
        print(f"Ошибка отправки в Telegram: {e}")

def main():
    with sync_playwright() as p:
        # Запускаем браузер в фоновом режиме (обязательно для GitHub Actions)
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            print(f"Переход на {SEARCH_URL}")
            page.goto(SEARCH_URL, timeout=60000)
            
            # --- ЗДЕСЬ ВАШИ ДЕЙСТВИЯ НА САЙТЕ ---
            # Пример (замените на реальные селекторы):
            # page.select_option('select[name="from"]', label="Минск")
            # page.select_option('select[name="to"]', label="Слоним")
            # page.fill('input[name="date"]', "2026-11-10")
            # page.click('button:has-text("Найти билеты")')
            # -------------------------------------
            
            # Ждём, пока результаты загрузятся (например, 5 секунд)
            page.wait_for_timeout(5000)
            
            # Проверяем, появился ли целевой элемент (свободные места)
            # Используем wait_for_selector с коротким таймаутом, чтобы не ждать долго
            try:
                page.wait_for_selector(TARGET_SELECTOR, timeout=10000, state="visible")
                # Если элемент найден, отправляем уведомление
                message = "🚐 Похоже, появились свободные места на маршрутку! Проверьте сайт."
                send_telegram_alert(message)
            except Exception:
                # Элемент не найден — мест нет
                print("Свободных мест не найдено.")
                
        except Exception as e:
            print(f"Произошла ошибка: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
