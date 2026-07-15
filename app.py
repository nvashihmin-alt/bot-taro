import os
import asyncio
import threading
import logging
from flask import Flask, jsonify
from bot import main

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({"status": "running", "message": "Tarot Bot is active! 🤖"})

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

def run_bot():
    """Запускает бота в отдельном цикле событий"""
    try:
        logger.info("🔄 Запуск бота Таро...")
        # Создаем новый цикл для этого потока
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main())
    except Exception as e:
        logger.error(f"❌ Ошибка в боте: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    # Запускаем бота в фоновом потоке
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    logger.info("✅ Бот запущен в фоновом потоке")
    
    # Запускаем Flask-сервер для Render
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"🌐 Запуск веб-сервера на порту {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
