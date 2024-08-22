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
from aiogram.types import ReplyKeyboardRemove
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

def admin_menu_keyboard() -> ReplyKeyboardMarkup:
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
                         reply_markup=admin_menu_keyboard()
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

    teams_count = len(game_info.teams)
    stations_count = 0

    for location in game_info.locations:
        stations_count += len(location.stations)
    
    if teams_count >= stations_count:
        logging.warning(f"Админ {message.from_user.id} попытался зарегистрировать команду, но их количество уже максимально допустимо")
        await message.answer(f"Команд уже максимально возможное количество")
        return

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
    # team.ToVisitLocation(location_name)

    game_info.SendTeamOnStation(team.GetName(), next_station.GetName())
    next_station.SetStatus(StationStatus.WAITING)
    logging.info(f"Команда {team_name} отправлена на станцию {next_station.GetName()}")

    next_caretakers_id: tuple[int, int] = game_info.GetCaretakersIDByStationName(next_station.GetName())
    
    print(f"\n\n\n\\n\n\n")
    print(next_caretakers_id)
    print(f"\n\n\n\\n\n\n")
    
    
    next_caretaker_id_1 = next_caretakers_id[0]
    next_caretaker_id_2 = next_caretakers_id[1]
    

    if  next_caretaker_id_1 != game_info.BAD_ID:
        logging.info(f"Найден куратор с id {next_caretaker_id_1} к нему идет команда {team_name}")
        await bot.send_message(next_caretaker_id_1, f"На вашу станцию направлена команда {team_name}")

    if  next_caretaker_id_2 != game_info.BAD_ID:
        logging.info(f"Найден куратор с id {next_caretaker_id_2} к нему идет команда {team_name}")
        await bot.send_message(next_caretaker_id_2, f"На вашу станцию направлена команда {team_name}")

    await state.clear()
    await message.answer(f"Успешно зарегистрирована команда {team_name}.\nОна отправлена на станцию {next_station.GetName()}.\n"
                         f"Чтобы посмотреть список зарегистрированных команд напишите /showteams\n\n"
                         f"Чтобы регистрировать другие команды, нажмите на кнопку ниже или введите команду:",
                         reply_markup=admin_menu_keyboard())

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



@admin_router.message(Command("showteams"))
@admin_router.message(F.text == "Показать команды")
async def cmd_show_teams(message: Message):
    logging.info(f"Админ {message.from_user.id} запросил список команд")
    
    if len(game_info.teams) == 0:
        logging.warning(f"Админ {message.from_user.id} запросил список команд, но оказалось что ни одной команды не было зарегистировано")
        await message.answer(f"Пока что ни одной команды не было зарегистрировано")
        return

    builder = ReplyKeyboardBuilder()


    for team in game_info.teams:
        builder.add(types.KeyboardButton(text= team.GetName()))
    
    builder.adjust(6)


    await message.answer(f"Выберете команду о которой вы хотите получить информацию", reply_markup=builder.as_markup(resize_keyboard = True),  )

@admin_router.message(lambda msg: msg.text in [team.GetName() for team in game_info.teams])
async def cmd_answer_show_teams(message: Message):
    team_name: str = message.text
    logging.info(f"Админ {message.from_user.id} запросил информацию о команде {team_name}")

    team = game_info.GetTeamByName(team_name)
    if team is None:
        logging.warning(f"Админу {message.from_user.id} не удалось получить информацию о команде {team_name}")
        await message.answer(f"Что-то пошло не так")
        return

    list_answer: list[str] =  team.GetToVisitList()
    unpacked_list_answer = ", ".join(list_answer)

    string_ans_representation: str = f"Команде {team_name} Осталось посетить локации : {unpacked_list_answer}"
    if len(string_ans_representation) > 0:
        await message.answer(string_ans_representation, reply_markup=admin_menu_keyboard())
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


def station_selection_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    for location in game_info.locations:
        for station in location.stations:
            builder.add(types.KeyboardButton(text=station.GetName()))
    builder.adjust(3)
    return builder.as_markup(resize_keyboard=True)

def status_selection_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🟢 Свободна"))
    builder.add(KeyboardButton(text="🟡 Ожидание"))
    builder.add(KeyboardButton(text="🔴 В процессе"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)

class FSMStationStatusChange(StatesGroup):
    choose_station = State()
    choose_status = State()

@admin_router.message(Command("changestatus"), StateFilter(default_state))
@admin_router.message(F.text == "Изменить статус станции", StateFilter(default_state))
async def cmd_change_status(message: Message, state: FSMContext):
    logging.info(f"Админ {message.from_user.id} начал процесс изменения статуса станции")
    
    await message.answer("Выберите станцию, статус которой вы хотите изменить:", reply_markup=station_selection_keyboard())
    await state.set_state(FSMStationStatusChange.choose_station)

@admin_router.message(StateFilter(FSMStationStatusChange.choose_station), F.text)
async def process_station_selected(message: Message, state: FSMContext):
    selected_station_name = message.text
    station = game_info.GetStationByName(selected_station_name)
    
    if station is None:
        logging.warning(f"Админ {message.from_user.id} выбрал некорректное название станции: {selected_station_name}")
        await message.answer("Станция не найдена. Пожалуйста, выберите корректное название станции.")
        return
    
    await state.update_data(station_name=selected_station_name)
    await message.answer(f"Вы выбрали станцию: {selected_station_name}.\nТеперь выберите новый статус:", reply_markup=status_selection_keyboard())
    await state.set_state(FSMStationStatusChange.choose_status)

@admin_router.message(StateFilter(FSMStationStatusChange.choose_status), F.text)
async def process_status_selected(message: Message, state: FSMContext):
    status_map = {
        "🟢 Свободна": StationStatus.FREE,
        "🟡 Ожидание": StationStatus.WAITING,
        "🔴 В процессе": StationStatus.IN_PROGRESS
    }
    
    selected_status_text = message.text
    new_status = status_map.get(selected_status_text)
     
    if new_status is None:
        logging.warning(f"Админ {message.from_user.id} выбрал некорректный статус: {selected_status_text}")
        await message.answer("Некорректный статус. Пожалуйста, выберите корректный статус.")
        return
    
    data = await state.get_data()
    station_name = data.get("station_name")
    station = game_info.GetStationByName(station_name)
    
    if station is None:
        logging.error(f"Ошибка при изменении статуса станции: станция {station_name} не найдена")
        await message.answer("Произошла ошибка: станция не найдена.")
        await state.clear()
        return
    
    station.SetStatus(new_status)
    logging.info(f"Админ {message.from_user.id} изменил статус станции {station_name} на {new_status.name}")
    
    await state.clear()
    await message.answer(f"Статус станции {station_name} успешно изменен на {selected_status_text}.", reply_markup=admin_menu_keyboard())

@admin_router.message(StateFilter(FSMStationStatusChange.choose_station))
async def warning_invalid_station(message: Message):
    logging.warning(f"Админ {message.from_user.id} ввел некорректное название станции")
    await message.answer(
        f'Название станции некорректно.\n\n'
        f'Пожалуйста, выберите станцию из списка.\n\n'
        f'Если вы хотите прервать процесс изменения статуса, отправьте команду /cancel'
    )

@admin_router.message(StateFilter(FSMStationStatusChange.choose_status))
async def warning_invalid_status(message: Message):
    logging.warning(f"Админ {message.from_user.id} ввел некорректный статус")
    await message.answer(
        f'Некорректный статус.\n\n'
        f'Пожалуйста, выберите статус из предложенных вариантов.\n\n'
        f'Если вы хотите прервать процесс изменения статуса, отправьте команду /cancel'
    )
