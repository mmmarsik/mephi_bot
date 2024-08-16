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
from GameInfo import Station, Location, Team, StationStatus


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
            [KeyboardButton(text="Зарегистрировать команду")]
        ],
        resize_keyboard=True
    )
    return keyboard


@admin_router.message(Command("start"), StateFilter(default_state))
async def cmd_start(message: Message):
    await message.answer(f"Привет, {message.from_user.first_name}, твоя роль - админ.\n"
                         f"Чтобы зарегистрировать команду, нажми на кнопку или введи: /register",
                         reply_markup=register_keyboard()
                         )


@admin_router.message(Command("cancel"), StateFilter(default_state))
async def cmd_cancel(message: Message):
    await message.answer(f"Вы находитесь вне процесса регистрации команд, отменять нечего")


@admin_router.message(Command("cancel"), ~StateFilter(default_state))
async def process_cancel_command_state(message: Message, state: FSMContext):
    await message.answer(f"Вы сбросили процесс регистрации команды, чтобы повторить его напишите /register")
    await state.clear()


@admin_router.message(F.text == "Зарегистрировать команду", StateFilter(default_state))
@admin_router.message(Command("register"), StateFilter(default_state))
async def cmd_register(message: Message, state: FSMContext):
    await message.answer(f"Введите название команды")
    await state.set_state(FSMStatesRegister.choose_name)


@admin_router.message(StateFilter(FSMStatesRegister.choose_name), F.text)
async def process_name_sent(message: Message, state: FSMContext):
    await state.update_data(name=message.text)

    builder = ReplyKeyboardBuilder()

    builder.add(types.KeyboardButton(text="Да"))
    builder.add(types.KeyboardButton(text="Нет"))
    builder.adjust(2)

    await message.answer(f"Вы ввели название команды: {message.text}\n"
                         f"Верно?", reply_markup=builder.as_markup(resize_keyboard=True),)

    await state.set_state(FSMStatesRegister.accept_info)


@admin_router.message(StateFilter(FSMStatesRegister.choose_name))
async def warning_not_name(message: Message):
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
        await message.answer("Произошла ошибка: не удалось подтвердить регистрацию команды.")
        return

    for team_ in game_info.teams:
        if team_.GetName() == team_name:
            builder = ReplyKeyboardBuilder()
            builder.add(types.KeyboardButton(text="Зарегистрировать команду"))
            await state.clear()
            await message.answer(f"Произошла ошибка: команда с таким именем уже зарегистрирована.\n"
                                 f"Если хотите - нажмите кнопку для повторной регистрации\n"
                                 f"Или напишите: /register", 
                                 reply_markup=builder.as_markup(resize_keyboard=True),)
            return

    game_info.AddTeam(team_name)

    next_station: Station = game_info.GetNextFreeStation(team_name)

    if next_station is None:
        await state.clear()
        await message.answer("Произошла ошибка: Все станции заняты.")
        return

    team = game_info.GetTeamByTeamName(team_name)
    team.ToVisitLocation(next_station.GetName()[:-2])

    game_info.SendTeamOnStation(team, next_station)

    next_station.SetStatus(StationStatus.WAITING)

    print(f"trying to visit location called {next_station.GetName()[:-2]}")

    next_caretaker_id: int = game_info.GetIDByStationName(
        next_station.GetName())
    print(f"статус станции {next_station.GetName()} это {next_station.WriteStatus()}")

    if next_caretaker_id:
        await bot.send_message(next_caretaker_id, f"На вашу станцию направлена команда {team_name}")

    await state.clear()
    await message.answer(f"Успешно зарегистрирована команда {team_name}.\nОна отправлена на станцию {next_station.GetName()}.\n"
                         f"Чтобы посмотреть список зарегистрированных команд напишите /showteams\n\n"
                         f"Чтобы регистрировать другие команды, нажмите на кнопку ниже или введите команду:",
                         reply_markup=register_keyboard())


@admin_router.message(Command("showteams"))
async def cmd_show_teams(message: Message):
    string_teams_presentation: str = ""
    for team in game_info.teams:
        string_teams_presentation += team.GetName()
        string_teams_presentation += " "
    if len(string_teams_presentation) > 0:
        await message.answer(f"{string_teams_presentation}")
    else:
        await message.answer(f"Пока что не было зарегистрировано ни одной команды")

@admin_router.message(Command("stations"))
async def cmd_show_stations(message: Message):
    station_and_status: dict[Station, StationStatus] = dict()
    for location in game_info.locations:
        for station in location.stations:
            station_and_status[station] = station.status
    
    answer_repr = str()
    for station_, status_ in station_and_status.items():
        answer_repr += station_.GetName()
        answer_repr += " status is "
        answer_repr += station.WriteStatus()
        answer_repr += "\n"
    
    if len(answer_repr) > 0:
        await message.answer(answer_repr)
    else:
        await message.answer(f"Пока еще не было зарегистрировано ни одной команды")


@admin_router.message(StateFilter(FSMStatesRegister.accept_info), F.text.lower() == "нет")
async def cheking_correct_name(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(f"Процесс регистрации был отменен, чтобы повторить напишите /register")


@admin_router.message(StateFilter(FSMStatesRegister.accept_info))
async def cheking_not_correct_name(message: Message, state: FSMContext):
    await message.answer(
        f'Вы отправили что-то некорректное\n\n'
        f'Пожалуйста, напишите Да, если название верно, иначе напишите Нет\n\n'
        f'Если вы хотите прервать заполнение - '
        f'отправьте команду /cancel'
    )
