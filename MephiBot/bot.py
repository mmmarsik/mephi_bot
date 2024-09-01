import asyncio
import logging
import argparse
from aiogram import Bot, Dispatcher
from gameinfo import GameInfo
from aiogram.fsm.storage.memory import MemoryStorage
import os

from dotenv import load_dotenv

from handlers.admin import admin

load_dotenv()

TOKEN = os.environ.get("TOKEN")

storage = MemoryStorage()

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=storage)

parser = argparse.ArgumentParser(description="Запуск бота с заданным файлом кураторов и локаций")
parser.add_argument('--caretakers-file', type=str, help='Путь к файлу с данными кураторов', default="users.txt")
parser.add_argument('--locations-file', type=str, help='Путь к файлу с данными локаций', default="locations.txt")
args = parser.parse_args()

def load_caretakers_from_file(file_path: str) -> dict[int, str]:
    caretakers = {}
    with open(file_path, 'r') as f:
        for line in f:
            user_id, station_name = line.strip().split()
            caretakers[int(user_id)] = station_name
    return caretakers

def load_locations_from_file(file_path: str) -> list[tuple[str, int]]:
    locations = []
    with open(file_path, 'r') as f:
        for line in f:
            location_name, max_users = line.strip().split()
            locations.append((location_name, int(max_users)))
    return locations

caretakers_data = load_caretakers_from_file(args.caretakers_file)
location_list_data = load_locations_from_file(args.locations_file)

game_info = GameInfo(
    caretakers=caretakers_data, 
    admins={1413950580, 593807464, 783440088},
    location_list=location_list_data
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

from handlers import caretaker

async def main():
    dp.include_router(caretaker.caretaker_router)
    dp.include_router(admin.admin_router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

