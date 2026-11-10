import asyncio
import logging
import sqlite3
import yt_dlp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

logging.basicConfig(level=logging.INFO)

TOKEN = "9078863865:AAG7DStcKB_waN6bDmSBgusZv7-Bx-bIR2Q"
TIKTOK_USERNAME = "Nadyushanekrasova"
CHECK_INTERVAL = 300
DB_FILE = "subscribers.db"

bot = Bot(token=TOKEN)
dp = Dispatcher()
is_streaming_now = False

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            user_id INTEGER PRIMARY KEY
        )
    """)
    conn.commit()
    conn.close()

def add_subscriber(user_id: int):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO subscribers (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def remove_subscriber(user_id: int):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM subscribers WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_subscribers() -> list[int]:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM subscribers")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

def check_tiktok_live(username: str) -> bool:
    url = f"https://www.tiktok.com/@{username}/live"
    ydl_opts = {'quiet': True, 'extract_flat': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get('is_live', False) or 'live' in info.get('webpage_url', '')
    except Exception:
        return False

async def background_live_checker(bot_instance: Bot):
    global is_streaming_now
    while True:
        try:
            loop = asyncio.get_running_loop()
            live_status = await loop.run_in_executor(None, check_tiktok_live, TIKTOK_USERNAME)
            
            if live_status and not is_streaming_now:
                is_streaming_now = True
                stream_link = f"https://www.tiktok.com/@{TIKTOK_USERNAME}/live"
                subscribers = get_subscribers()
                for user_id in subscribers:
                    try:
                        await bot_instance.send_message(
                            user_id, 
                            f"🔴 **Внимание!** @{TIKTOK_USERNAME} запустила стрим в TikTok!\n\n🔗 **Ссылка на эфир:** {stream_link}",
                            parse_mode="Markdown"
                        )
                    except Exception as e:
                        logging.error(f"Не удалось отправить {user_id}: {e}")
            elif not live_status and is_streaming_now:
                is_streaming_now = False
        except Exception as e:
            logging.error(f"Ошибка: {e}")
        await asyncio.sleep(CHECK_INTERVAL)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    add_subscriber(message.from_user.id)
    await message.answer(f"Привет! 👋 Я успешно запущен в облаке и слежу за эфирами `@{TIKTOK_USERNAME}`!")

@dp.message(Command("stop"))
async def cmd_stop(message: types.Message):
    remove_subscriber(message.from_user.id)
    await message.answer("Ты отписался от уведомлений.")

async def main():
    init_db()
    asyncio.create_task(background_live_checker(bot))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
  
