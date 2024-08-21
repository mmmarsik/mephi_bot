import asyncio
import logging
from aiogram import Bot, Dispatcher
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
    
    caretakers={1808760043: "Painting-1"}, 
    admins={1413950580, 593807464},
    location_list=[("Painting", 3), ("Plov-Center", 3), ("Cooking", 3), ("Restraunt", 3), ("A-100", 3), ("Funny-Eggs", 3), ("Water", 3), ("Fire" ,3)]
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
