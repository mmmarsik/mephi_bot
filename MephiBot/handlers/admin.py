from aiogram import Router, F
from aiogram.filters.command import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import BaseFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, State, StatesGroup
from aiogram.filters import StateFilter
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram import types
from bot import bot
from types import NoneType
from bot import game_info
from gameinfo import Station, Location, Team, StationStatus
from bot import logging

class IsAdminFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return message.from_user.id in game_info.admins

admin_router = Router()
admin_router.message.filter(IsAdminFilter())

class FSMStatesRegister(StatesGroup):
    choose_name = State()
    accept_info = State()

def register_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Зарегистрировать команду")],
            [KeyboardButton(text="Показать команды"), KeyboardButton(text="Статус станций")]
        ],
        resize_keyboard=True
    )
    return keyboard

@admin_router.message(Command("start"), StateFilter(default_state))
async def cmd_start(message: Message):
    logging.info(f"Админ {message.from_user.id} вызвал команду /start")
    await message.answer(f"Привет, {message.from_user.first_name}, твоя роль - админ.\n"
                         f"Чтобы зарегистрировать команду, нажми на кнопку ниже или введи: /register\n"
                         f"Чтобы посмотреть список станций и их статус нажми на кнопку ниже или введи /stations\n"
                         f"Чтобы посмотреть список зарегистрированных команд нажми на кнопку ниже или введи /showteams",
                         reply_markup=register_keyboard()
                         )

@admin_router.message(Command("cancel"), StateFilter(default_state))
async def cmd_cancel(message: Message):
    logging.info(f"Админ {message.from_user.id} вызвал команду /cancel вне процесса регистрации")
    await message.answer(f"Вы находитесь вне процесса регистрации команд, отменять нечего")

@admin_router.message(Command("cancel"), ~StateFilter(default_state))
async def process_cancel_command_state(message: Message, state: FSMContext):
    logging.info(f"Админ {message.from_user.id} прервал процесс регистрации команды")
    await message.answer(f"Вы сбросили процесс регистрации команды, чтобы повторить его напишите /register")
    await state.clear()

@admin_router.message(F.text == "Зарегистрировать команду", StateFilter(default_state))
@admin_router.message(Command("register"), StateFilter(default_state))
async def cmd_register(message: Message, state: FSMContext):
    logging.info(f"Админ {message.from_user.id} начал процесс регистрации команды")
    await message.answer(f"Введите название команды")
    await state.set_state(FSMStatesRegister.choose_name)

@admin_router.message(StateFilter(FSMStatesRegister.choose_name), F.text)
async def process_name_sent(message: Message, state: FSMContext):
    logging.info(f"Админ {message.from_user.id} ввел название команды: {message.text}")
    await state.update_data(name=message.text)

    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="Да"))
    builder.add(types.KeyboardButton(text="Нет"))
    builder.adjust(2)

    await message.answer(f"Вы ввели название команды: {message.text}\nВерно?",
                         reply_markup=builder.as_markup(resize_keyboard=True),)
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
    team.ToVisitLocation(location_name)

    game_info.SendTeamOnStation(team.GetName(), next_station.GetName())
    next_station.SetStatus(StationStatus.WAITING)
    logging.info(f"Команда {team_name} отправлена на станцию {next_station.GetName()}")

    next_caretaker_id: int = game_info.GetCaretakerIDByStationName(next_station.GetName())
    if next_caretaker_id:
        logging.info(f"Найден куратор с id {next_caretaker_id} к нему идет команда {team_name}")
        await bot.send_message(next_caretaker_id, f"На вашу станцию направлена команда {team_name}")

    await state.clear()
    await message.answer(f"Успешно зарегистрирована команда {team_name}.\nОна отправлена на станцию {next_station.GetName()}.\n"
                         f"Чтобы посмотреть список зарегистрированных команд напишите /showteams\n\n"
                         f"Чтобы регистрировать другие команды, нажмите на кнопку ниже или введите команду:",
                         reply_markup=register_keyboard())

@admin_router.message(StateFilter(FSMStatesRegister.accept_info), F.text.lower() == "нет")
async def cheking_correct_name(message: Message, state: FSMContext):
    logging.info(f"Админ {message.from_user.id} отменил процесс регистрации команды")
    await state.clear()
    await message.answer(f"Процесс регистрации был отменен, чтобы повторить напишите /register")

@admin_router.message(StateFilter(FSMStatesRegister.accept_info))
async def cheking_not_correct_name(message: Message, state: FSMContext):
    logging.warning(f"Админ {message.from_user.id} отправил некорректный ответ на этапе подтверждения имени команды")
    await message.answer(
        f'Вы отправили что-то некорректное\n\n'
        f'Пожалуйста, напишите Да, если название верно, иначе напишите Нет\n\n'
        f'Если вы хотите прервать заполнение - '
        f'отправьте команду /cancel'
    )

# @admin_router.message(Command("showteams"))
# @admin_router.message(F.text == "Показать команды")
# async def cmd_show_teams(message: Message):
#     logging.info(f"Админ {message.from_user.id} запросил список команд")
#     string_teams_presentation = "Зарегистрированные команды:\n"
#     for team in game_info.teams:
#         string_teams_presentation += f"- {team.GetName()} : Осталось посетить станции {team.GetToVisitList()}\n"
#     if len(game_info.teams) > 0:
#         await message.answer(string_teams_presentation)
#     else:
#         await message.answer("Пока что не было зарегистрировано ни одной команды")

@admin_router.message(Command("showteams"))
@admin_router.message(F.text == "Показать команды")
async def cmd_show_teams(message: Message):
    logging.info(f"Админ {message.from_user.id} запросил список команд")
    builder = ReplyKeyboardBuilder()
    for team in game_info.teams:
        builder.add(types.KeyboardButton(text= team.GetName()))
    
    builder.adjust(6)

    await message.answer(f"Выберете команду о которой вы хотите получить информацию", reply_markup=builder.as_markup(resize_keyboard = True), )

@admin_router.message(lambda x: x in [team.GetName() for team in game_info.teams])
# @admin_router.message(F.text in [team.GetName() for team in game_info.teams])
async def cmd_answer_show_teams(message: Message):
    team_name: str = F.text
    logging.info(f"Админ {message.from_user.id} запросил информацию о команде {team_name}")

    team = game_info.GetTeamByName(team_name)
    if team is None:
        logging.warning(f"Админу {message.from_user.id} не удалось получить информацию о команде {team_name}")
        await message.answer(f"Что-то пошло не так")
        return

    string_ans_representation: str = f"Команде {team_name} Осталось посетить станции: {team.GetToVisitList()}"
    if len(string_ans_representation) > 0:
        await message.answer(string_ans_representation)
    else:
        logging.warning(f"Админу {message.from_user.id} не удалось получить информацию о команде {team_name}")
        await message.answer(f"Что-то пошло не так")


@admin_router.message(Command("stations"))
@admin_router.message(F.text == "Статус станций")
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
            status_text = status_emojis.get(station.status, "Неизвестный статус")
            answer_repr += f"- {station.GetName()}: {status_text}\n"
        answer_repr += "\n"  
    
    if len(answer_repr.strip()) > 0:
        await message.answer(answer_repr)
    else:
        await message.answer("Пока еще не было зарегистрировано ни одной станции.")
