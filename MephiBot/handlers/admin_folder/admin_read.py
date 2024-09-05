from aiogram import Router, F
from aiogram.filters.command import Command
from aiogram.types import Message
from aiogram.filters import BaseFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.filters import StateFilter
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram import types
from bot import bot
from bot import game_info
from gameinfo import Station, StationStatus
from bot import logging

from .admin_fsm import *
from ..keyboards import *

read_router = Router()


@read_router.message(Command("showteams"))
@read_router.message(F.text == "Получить инфо о команде")
async def cmd_show_teams(message: Message):
    logging.info(f"Админ {message.from_user.id} запросил список команд")

    if len(game_info.teams) == 0:
        logging.warning(f"Админ {message.from_user.id} запросил список команд, но оказалось, что ни одной команды не было зарегистрировано")
        await message.answer(f"Пока что ни одной команды не было зарегистрировано")
        return
    await message.answer(f"Выберите команду, о которой вы хотите получить информацию",
                         reply_markup=get_team_keyboard())


@read_router.message(lambda msg: msg.text in [team.GetName() for team in game_info.teams])
async def cmd_answer_show_teams(message: Message):
    team_name: str = message.text
    logging.info(
        f"Админ {message.from_user.id} запросил информацию о команде {team_name}")

    team = game_info.GetTeamByName(team_name)
    if team is None:
        logging.warning(f"Админу {message.from_user.id} не удалось получить информацию о команде {team_name}")
        await message.answer(f"Что-то пошло не так")
        return

    list_answer: list[str] = team.GetToVisitList()
    unpacked_list_answer = ", ".join(list_answer)

    string_ans_representation: str = f"Команде {
        team_name} осталось посетить локации: {unpacked_list_answer}"

    if len(string_ans_representation) > 0:
        await message.answer(string_ans_representation,
                             reply_markup=get_admin_menu_keyboard())
    else:
        logging.warning(f"Админу {message.from_user.id} не удалось получить информацию о команде {team_name}")
        await message.answer(f"Что-то пошло не так")


@read_router.message(Command("stations"))
@read_router.message(F.text == "Статус станций")
async def cmd_show_stations(message: Message):
    logging.info(f"Админ {message.from_user.id} запросил состояние станций")

    status_emojis = {
        StationStatus.FREE: "🟢 Свободна",
        StationStatus.WAITING: "🟡 Ожидание",
        StationStatus.IN_PROGRESS: "🔴 В процессе"
    }

    answer_repr = "📍 Состояние станций\n\n"

    for location in game_info.locations:
        answer_repr += f"{location.GetName()}\n"
        for station in location.stations:
            status_text = status_emojis.get(
                station.status, "Неизвестный статус")
            answer_repr += f"- {station.GetName()}: {status_text}\n"
        answer_repr += "\n"

    if len(answer_repr.strip()) > 0:
        logging.info(
            f"Админу {message.from_user.id} был показан статус станций")
        await message.answer(answer_repr)
    else:
        logging.warning(f"Админ { message.from_user.id} запросил состояние станций, но ни одной станции не было зарегистрировано")
        await message.answer("Пока еще не было зарегистрировано ни одной станции.")


@read_router.message(Command("showstationteams"))
@read_router.message(F.text == "Показать команды на станции")
async def cmd_show_station_teams(message: Message, state: FSMContext):
    logging.info(
        f"Админ {message.from_user.id} начал процесс выбора станции для показа команд")

    await message.answer("Выберите станцию, для которой вы хотите посмотреть список команд:",
                         reply_markup=get_station_selection_keyboard())
    await state.set_state(FSMShowStationTeams.choose_station)


@read_router.message(StateFilter(FSMShowStationTeams.choose_station), F.text)
async def process_station_selected(message: Message, state: FSMContext):
    selected_station_name = message.text
    logging.info(f"Админ {message.from_user.id} выбрал станцию {selected_station_name}")

    station = game_info.GetStationByName(selected_station_name)

    if station is None:
        logging.warning(f"Админ {message.from_user.id} выбрал некорректное название станции: {selected_station_name}")
        await message.answer("Станция не найдена. Пожалуйста, выберите корректное название станции.")
        return

    current_team = game_info.GetCurrentTeamOnStation(selected_station_name)
    leaving_team = game_info.GetLeavingTeamByStation(selected_station_name)

    if current_team is None and leaving_team is None:
        logging.info(
            f"На станции {selected_station_name} нет зарегистрированных команд")
        await message.answer(f"На станции {selected_station_name} нет зарегистрированных команд.")
    else:
        status_messages = []
        if current_team:
            status_messages.append(
                f"Команда '{current_team.GetName()}' находится на станции.")
        if leaving_team:
            status_messages.append(
                f"Команда '{leaving_team.GetName()}' покидает станцию.")

        logging.info(f"Админу {message.from_user.id} были показаны команды на станции {selected_station_name}")
        await message.answer("\n".join(status_messages))

    await state.clear()
    await message.answer("Вы можете выбрать другую станцию или вернуться в главное меню.",
                         reply_markup=get_admin_menu_keyboard())


@read_router.message(StateFilter(FSMShowStationTeams.choose_station))
async def warning_invalid_station(message: Message):
    logging.warning(
        f"Админ {message.from_user.id} ввел некорректное название станции")
    await message.answer(
        f'Название станции некорректно.\n\n'
        f'Пожалуйста, выберите станцию из списка.\n\n'
        f'Если вы хотите прервать процесс, отправьте команду /cancel'
    )


@read_router.message(F.text == "Найти команды без станций")
@read_router.message(Command("find_teams_without_station"))
async def find_teams_without_station(message: Message):
    teams_without_station: set[str] = set()

    for team in game_info.teams:
        if len(team.GetToVisitList()) > 0:
            if not (team.GetName() in game_info.team_on_station.values()) \
                    and not (team.GetName() in game_info.team_leaving_station.values()):
                teams_without_station.add(team.GetName())

    if len(teams_without_station) == 0:
        await message.answer(f"У всех команд назначена станция", reply_markup=get_admin_menu_keyboard())
        return

    await message.answer(f"Вот список команд у которых не назначено ни одной станции\n"
                         f"{list(teams_without_station)}", reply_markup=get_admin_menu_keyboard())
