import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import TOKEN
from gameinfo import GameInfo
from aiogram.fsm.storage.memory import MemoryStorage
import os

from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ.get("TOKEN")

storage = MemoryStorage()


bot = Bot(token=TOKEN)
dp = Dispatcher(storage=storage)


game_info = GameInfo(
    
    caretakers={1808760043: "Shreks-1"}, 
    admins={1413950580, 593807464},
    location_list=[("Painting", 10), ("Plov-Center", 10), ("Cooking", 10)]
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(funcName)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("bot_log.txt"),
        logging.StreamHandler()
    ]
)

from handlers import caretaker, admin


async def main():
    dp.include_router(caretaker.caretaker_router)
    dp.include_router(admin.admin_router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
