import asyncio
import logging
import argparse
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
import valkey
from gameinfo import GameInfo
import json  
import os


load_dotenv()
TOKEN = os.environ.get("TOKEN")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(funcName)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("bot_log.txt"),
        logging.StreamHandler()
    ]
)

connection_pool = valkey.ConnectionPool(
    host='localhost',
    port=6379,
    db=0,
    max_connections=10  
)

client = valkey.Valkey(connection_pool=connection_pool)

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
    location_list=location_list_data,
    teams=[], team_on_station= dict(), team_leaving_station= dict()
)

def save_game_info():
    game_info_data = {
        "caretakers": game_info.caretakers,
        "admins": list(game_info.admins),
        "location_list": game_info.location_list,
        "teams" : list(game_info.teams),
        "team_on_station": game_info.team_on_station,
        "team_leaving_station": game_info.team_leaving_station
    }
    client.set("game_info", json.dumps(game_info_data))  
    logging.info("Game info сохранены в Valkey")

def load_game_info():
    data = client.get("game_info")  
    if data:
        game_info_data = json.loads(data)

        return GameInfo(
            caretakers=game_info_data["caretakers"],
            admins=set(game_info_data["admins"]),
            location_list=game_info_data["location_list"],
            teams=set(game_info_data["teams"]),
            team_on_station=game_info_data.get("team_on_station", {}),
            team_leaving_station=game_info_data.get("team_leaving_station", {})
        )
        
    return None

loaded_game_info = load_game_info()
if loaded_game_info:
    game_info = loaded_game_info
    logging.info("Нашли сохранение")
else:
    logging.info("Еще нету сохранений")

from handlers import caretaker
from handlers.admin_folder import admin

async def periodic_save(interval: int):
    while True:
        await asyncio.sleep(interval)
        save_game_info()
        logging.info("Данные игры сохранены по таймеру")

async def main():
    dp.include_router(caretaker.caretaker_router)
    dp.include_router(admin.admin_router)

    await bot.delete_webhook(drop_pending_updates=True)

    # asyncio.create_task(periodic_save(10))  


    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
