import asyncio
import logging
import argparse
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
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
 
storage = MemoryStorage()
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=storage)

parser = argparse.ArgumentParser(
    description="Запуск бота с заданным файлом кураторов и локаций")
parser.add_argument('--caretakers-file', type=str,
                    help='Путь к файлу с данными кураторов', default="users.txt")
parser.add_argument('--locations-file', type=str,
                    help='Путь к файлу с данными локаций', default="locations.txt")
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

from gameinfo import GameInfo

game_info = GameInfo(
    caretakers=caretakers_data,
    admins={1413950580, 593807464, 783440088},
    location_list=location_list_data,
    teams=[], team_on_station=dict(), team_leaving_station=dict()
)



import json
import logging
import valkey
from gameinfo import Team, Location, StationStatus, Station

import json
import logging

# def parse_location(location_str: str) -> Location:
#     try:
#         # Ожидаемый формат: "Name:Station1 Status1;Station2 Status2;..."
#         name, stations_str = location_str.split(":", 1)
#         station_strs = stations_str.split(";")
#         location = Location(name, len(station_strs))
#         location.stations = [parse_station(station) for station in station_strs]
#         return location
#     except Exception as e:
#         logging.error(f"Error parsing location string: {location_str} - {e}")
#         return None


# def parse_station(station_str: str) -> Station:
#     try:
#         # Ожидаемый формат: "Name Status"
#         name, status_str = station_str.rsplit(" ", 1)
#         station = Station(name)
#         station.SetStatus(StationStatus[status_str])
#         return station
#     except Exception as e:
#         logging.error(f"Error parsing station string: {station_str} - {e}")
#         return None

# def parse_team(team_str: str) -> Team:
#     try:
#         # Ожидаемый формат: "Name:[ToVisit],[Visited]"
#         name, rest = team_str.split(":[", 1)
#         to_visit_str, visited_str = rest.split("],[", 1)
#         visited_str = visited_str.rstrip("]")
#         to_visit_list = to_visit_str.split(",") if to_visit_str else []
#         visited_list = visited_str.split(",") if visited_str else []
#         team = Team(name, to_visit_list)
#         team.visited_list = visited_list
#         return team
#     except Exception as e:
#         logging.error(f"Error parsing team string: {team_str} - {e}")
#         return None



# def load_game_info(client) -> GameInfo:
#     try:
#         # Fetch and parse data from the client
#         game_info_data = json.loads(client.get("game_info"))

#         # Parse locations
#         locations = [
#             parse_location(location_str)
#             for location_str in game_info_data["locations"]
#             if parse_location(location_str) is not None
#         ]

#         # Parse teams
#         teams = [
#             parse_team(team_str)
#             for team_str in game_info_data["teams"]
#             if parse_team(team_str) is not None
#         ]

#         # Create GameInfo object
#         game_info = GameInfo(
#             caretakers=game_info_data["caretakers"],
#             admins=set(game_info_data["admins"]),
#             location_list=[(loc.GetName(), len(loc.stations)) for loc in locations],
#             teams=teams,
#             team_on_station=game_info_data["team_on_station"],
#             team_leaving_station=game_info_data["team_leaving_station"]
#         )

#         logging.info("Game info successfully loaded")
#         return game_info
#     except Exception as e:
#         logging.error(f"Error loading game info: {e}")
#         return None







# loaded_game_info = load_game_info(game_info.client)
# if loaded_game_info:
#     game_info = loaded_game_info
#     logging.info("Нашли сохранение")
#     print(game_info.locations)
# else:
#     logging.info("Еще нету сохранений")

from handlers import caretaker
from handlers.admin_folder import admin

async def main():
    dp.include_router(caretaker.caretaker_router)
    dp.include_router(admin.admin_router)

    await bot.delete_webhook(drop_pending_updates=True)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
