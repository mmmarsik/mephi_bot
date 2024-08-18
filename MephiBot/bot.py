import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import TOKEN
from GameInfo import GameInfo
from aiogram.fsm.storage.memory import MemoryStorage

storage = MemoryStorage()


bot = Bot(token=TOKEN)
dp = Dispatcher(storage=storage)


game_info = GameInfo(
    caretakers={1808760043: "Shreks-1", 832090978: "Plov-Center-1"},
    # caretakers={1808760043: "Shreks-1"},

    admins={1413950580, 593807464},
    location_list=[("Shreks", 1), ("Plov-Center", 1)]
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
