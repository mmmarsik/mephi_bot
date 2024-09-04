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

from .admin_edit import edit_router
from .admin_read import read_router

from .admin_fsm import *
from ..keyboards import *

class IsAdminFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return message.from_user.id in game_info.admins

admin_router = Router()
admin_router.message.filter(IsAdminFilter())
admin_router.include_routers(edit_router, read_router)


@admin_router.message(Command("start"), StateFilter(default_state))
async def cmd_start(message: Message):
    logging.info(f"Админ {message.from_user.id} вызвал команду /start")
    await message.answer(f"Привет, {message.from_user.first_name}, твоя роль - админ.\n"
                         f"Чтобы зарегистрировать команду, нажми на кнопку ниже или введи: /register\n"
                         f"Чтобы посмотреть список станций и их статус нажми на кнопку ниже или введи /stations\n"
                         f"Чтобы посмотреть список зарегистрированных команд нажми на кнопку ниже или введи /showteams",
                         reply_markup=get_admin_menu_keyboard()
                         )


@admin_router.message(Command("cancel"), StateFilter(default_state))
async def cmd_cancel(message: Message):
    logging.info(
        f"Админ {message.from_user.id} вызвал команду /cancel вне процесса регистрации")
    await message.answer(f"Вы находитесь вне какого-либо процесса, отменять нечего", reply_markup=get_admin_menu_keyboard())





@admin_router.message(Command("cancel"), ~StateFilter(default_state))
async def process_cancel_command_state(message: Message, state: FSMContext):
    logging.info(
        f"Админ {message.from_user.id} прервал процесс регистрации команды")
    await message.answer(f"Вы сбросили запущенный вами процесс, выберете что вы хотите сделать нажав на кнопку",
                          reply_markup=get_admin_menu_keyboard())
    await state.clear()


@admin_router.message(F.text == "Зарегистрировать команду", StateFilter(default_state))
@admin_router.message(Command("register"), StateFilter(default_state))
async def cmd_register(message: Message, state: FSMContext):
    logging.info(f"Админ {message.from_user.id} начал процесс регистрации команды")

    teams_count = len(game_info.teams)
    stations_count = 0

    for location in game_info.locations:
        stations_count += len(location.stations)

    if teams_count >= stations_count:
        logging.warning(f"Админ {message.from_user.id} попытался зарегистрировать команду, \
                        но их количество уже максимально допустимо")
        await message.answer(f"Команд уже максимально возможное количество", 
                             reply_markup=get_admin_menu_keyboard())
        return

    await message.answer(f"Введите название команды")
    await state.set_state(FSMStatesRegister.choose_name)


@admin_router.message(StateFilter(FSMStatesRegister.choose_name), F.text)
async def process_name_sent(message: Message, state: FSMContext):
    logging.info(f"Админ {message.from_user.id} ввел название команды: {message.text}")
    await state.update_data(name=message.text)

    await message.answer(f"Вы ввели название команды: {message.text}\nВерно?",
                         reply_markup=get_yes_no_keyboard(),)
    await state.set_state(FSMStatesRegister.accept_info)


@admin_router.message(StateFilter(FSMStatesRegister.choose_name))
async def warning_not_name(message: Message):
    logging.warning(f"Админ {message.from_user.id} ввел некорректное название команды")
    await message.answer(
        f'То, что вы отправили не похоже на название команды\n\n'
        f'Пожалуйста, введите верное название\n\n'
        f'Если вы хотите прервать заполнение - '
        f'отправьте команду /cancel'
    )


@admin_router.message(StateFilter(FSMStatesRegister.accept_info), F.text.lower() == "да")

async def cheking_correct_name(message: Message, state: FSMContext):
    data = await state.get_data()
    team_name: str = data.get("name")

    if not team_name:
        logging.error("Ошибка регистрации команды: название команды не найдено")
        await message.answer("Произошла ошибка: не удалось подтвердить регистрацию команды.")
        return

    for team_ in game_info.teams:
        if team_.GetName() == team_name:
            logging.warning(f"Попытка зарегистрировать существующую команду: {team_name}")
            builder = ReplyKeyboardBuilder()
            builder.add(types.KeyboardButton(text="Зарегистрировать команду"))
            await state.clear()
            await message.answer(f"Произошла ошибка: команда с таким именем уже зарегистрирована.\n"
                                 f"Если хотите - нажмите кнопку для повторной регистрации\n"
                                 f"Или напишите: /register",
                                 reply_markup=builder.as_markup(resize_keyboard=True),)
            return

    game_info.AddTeam(team_name)
    logging.info(f"Команда {team_name} успешно зарегистрирована")

    next_station: Station = game_info.GetNextFreeStation(team_name)

    if next_station is None:
        logging.error("Все станции заняты, невозможно отправить команду на станцию")
        await state.clear()
        await message.answer("Произошла ошибка: Все станции заняты.")
        return

    team = game_info.GetTeamByName(team_name)
    location_name: str = next_station.GetName()[:-2]

    game_info.SendTeamOnStation(team.GetName(), next_station.GetName())
    next_station.SetStatus(StationStatus.WAITING)
    logging.info(f"Команда {team_name} отправлена на станцию {next_station.GetName()}")

    next_caretakers_id: tuple[int, int] = game_info.GetCaretakersIDByStationName(next_station.GetName())

    next_caretaker_id_1 = next_caretakers_id[0]
    next_caretaker_id_2 = next_caretakers_id[1]

    if next_caretaker_id_1 != game_info.BAD_ID:
        logging.info(f"Найден куратор с id {next_caretaker_id_1} к нему идет команда {team_name}")
        await bot.send_message(next_caretaker_id_1, f"На вашу станцию направлена команда {team_name}")

    if next_caretaker_id_2 != game_info.BAD_ID:
        logging.info(f"Найден куратор с id {next_caretaker_id_2} к нему идет команда {team_name}")
        await bot.send_message(next_caretaker_id_2, f"На вашу станцию направлена команда {team_name}")

    await state.clear()

    with open("admin_logi.txt", "w") as f:
        f.write(f"In admin.py {[str(team) for team in game_info.teams]}")

    game_info.update_game_info()  


    await message.answer(f"Успешно зарегистрирована команда {team_name}.\nОна отправлена на станцию {next_station.GetName()}.\n"
                         f"Чтобы посмотреть список зарегистрированных команд напишите /showteams\n\n"
                         f"Чтобы регистрировать другие команды, нажмите на кнопку ниже или введите команду:",
                         reply_markup=get_admin_menu_keyboard())


@admin_router.message(StateFilter(FSMStatesRegister.accept_info), F.text.lower() == "нет")
async def cheking_correct_name(message: Message, state: FSMContext):
    logging.info(f"Админ {message.from_user.id} отменил процесс регистрации команды")
    await state.clear()
    await message.answer(f"Процесс регистрации был отменен, чтобы повторить напишите /register", reply_markup=get_admin_menu_keyboard())


@admin_router.message(StateFilter(FSMStatesRegister.accept_info))
async def cheking_not_correct_name(message: Message, state: FSMContext):
    logging.warning(f"Админ {message.from_user.id} отправил некорректный ответ на этапе подтверждения имени команды")
    await message.answer(
        f'Вы отправили что-то некорректное\n\n'
        f'Пожалуйста, напишите Да, если название верно, иначе напишите Нет\n\n'
        f'Если вы хотите прервать заполнение - '
        f'отправьте команду /cancel'
    )


