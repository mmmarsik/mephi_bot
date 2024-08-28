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
from .keyboards import *

class IsAdminFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return message.from_user.id in game_info.admins


admin_router = Router()
admin_router.message.filter(IsAdminFilter())


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
    await message.answer(f"Вы находитесь вне процесса регистрации команд, отменять нечего")


@admin_router.message(Command("cancel"), StateFilter(FSMStationStatusChange))
async def cancel_status_change(message: Message, state: FSMContext):
    logging.info(
        f"Админ {message.from_user.id} отменил процесс изменения статуса станции")
    await state.clear()
    await message.answer(f"Процесс изменения статуса станции был отменен. Вы можете начать процесс снова, отправив команду /changestatus", reply_markup=get_admin_menu_keyboard())


@admin_router.message(Command("cancel"), ~StateFilter(default_state))
async def process_cancel_command_state(message: Message, state: FSMContext):
    logging.info(
        f"Админ {message.from_user.id} прервал процесс регистрации команды")
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
    await message.answer(f"Успешно зарегистрирована команда {team_name}.\nОна отправлена на станцию {next_station.GetName()}.\n"
                         f"Чтобы посмотреть список зарегистрированных команд напишите /showteams\n\n"
                         f"Чтобы регистрировать другие команды, нажмите на кнопку ниже или введите команду:",reply_markup=get_admin_menu_keyboard())


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


@admin_router.message(F.text == "Редактировать список локаций для опр. команды")
@admin_router.message(Command(commands='edit_command_stations'))
async def cmd_edit_stations(message: Message, state: FSMContext):
    keyboard = get_team_keyboard()

    if len(game_info.teams) == 0:
        logging.warning(f"Админ {message.from_user.id} хотел редактировать список посещенных станций для команд, но пока еще не зарегистрировано ни одной команды")
        await message.answer(f"Пока что ни одной команды не было зарегистрировано, не у кого менять список посещенных станций")
        return

    await message.answer("Выберите команду:", reply_markup=keyboard)
    await state.set_state(FSMEditStation.choosing_team)


@admin_router.message(FSMEditStation.choosing_team)
async def choose_team(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_editing(message, state)
        return

    team_name = message.text
    team = game_info.GetTeamByName(team_name)

    if team is None:
        await message.answer("Команда не найдена, попробуйте снова.")
        return

    await state.update_data(team_name=team_name)
    await message.answer(f"Команда {team_name} выбрана. Выберите действие:", reply_markup=get_edit_action_keyboard())
    await state.set_state(FSMEditStation.editing_stations)


@admin_router.message(FSMEditStation.editing_stations)
async def choose_action(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_editing(message, state)
        return

    action = message.text

    if action == "Добавить станцию":
        keyboard = get_location_keyboard()
        await message.answer("Выберите станцию для добавления:", reply_markup=keyboard)
        await state.set_state(FSMEditStation.adding_station)
    elif action == "Удалить станцию":
        keyboard = get_location_keyboard()
        await message.answer("Выберите станцию для удаления:", reply_markup=keyboard)
        await state.set_state(FSMEditStation.removing_station)
    else:
        await message.answer("Неверная команда. Попробуйте снова.")


@admin_router.message(FSMEditStation.adding_station)
async def add_station(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_editing(message, state)
        return

    location_name = message.text
    data = await state.get_data()
    team_name = data.get("team_name")

    team = game_info.GetTeamByName(team_name)
    if team is None:
        await message.answer("Команда не найдена.\n\n"
                             f"Если хотите попробовать еще раз нажмите кнопку или напишите /edit_command_stations", reply_markup=get_admin_menu_keyboard())
        await state.clear()
        return

    if location_name not in team.to_visit_list:
        team.to_visit_list.append(location_name)
        await message.answer(f"Станция {location_name} добавлена в список посещений команды {team_name}.\n\n"
                             f"Если хотите попробовать еще раз нажмите кнопку или напишите /edit_command_stations", reply_markup=get_admin_menu_keyboard())
    else:
        await message.answer(f"Станция {location_name} уже в списке посещений команды {team_name}.\n\n"
                             f"Если хотите попробовать еще раз нажмите кнопку или напишите /edit_command_stations", reply_markup=get_admin_menu_keyboard())

    await state.clear()


@admin_router.message(FSMEditStation.removing_station)
async def remove_station(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_editing(message, state)
        return

    location_name = message.text
    data = await state.get_data()
    team_name = data.get("team_name")

    team = game_info.GetTeamByName(team_name)
    if team is None:
        await message.answer("Команда не найдена.\n\n"
                             f"Если хотите попробовать еще раз нажмите кнопку или напишите /edit_command_stations", reply_markup=get_admin_menu_keyboard())
        await state.clear()
        return

    to_visit_list: list[str] = team.GetToVisitList()

    if location_name in to_visit_list:
        team.to_visit_list.remove(location_name)

        await message.answer(f"Локация {location_name} удалена из списка посещений команды {team_name}.\n\n"
                             f"Если хотите попробовать еще раз нажмите кнопку или напишите /edit_command_stations", reply_markup=get_admin_menu_keyboard())
    else:
        print(f"\n\n\n\n\n {to_visit_list} \n\n\n\n\n ")

        await message.answer(f"Станция {location_name} не найдена в списке посещений команды {team_name}.\n\n"
                             f"Если хотите попробовать еще раз нажмите кнопку или напишите /edit_command_stations", reply_markup=get_admin_menu_keyboard())

    await state.clear()


async def cancel_editing(message: Message, state: FSMContext):
    await message.answer("Редактирование отменено.\n\n"
                         f"Если хотите попробовать еще раз нажмите кнопку или напишите /edit_command_stations", reply_markup=get_admin_menu_keyboard())
    await state.clear()


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
        builder.add(types.KeyboardButton(text=team.GetName()))

    builder.adjust(6)

    await message.answer(f"Выберете команду о которой вы хотите получить информацию", reply_markup=builder.as_markup(resize_keyboard=True),)


@admin_router.message(lambda msg: msg.text in [team.GetName() for team in game_info.teams])
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
        team_name} Осталось посетить локации : {unpacked_list_answer}"
    if len(string_ans_representation) > 0:
        await message.answer(string_ans_representation, reply_markup=get_admin_menu_keyboard())
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
            status_text = status_emojis.get(
                station.status, "Неизвестный статус")
            answer_repr += f"- {station.GetName()}: {status_text}\n"
        answer_repr += "\n"

    if len(answer_repr.strip()) > 0:
        await message.answer(answer_repr)
    else:
        await message.answer("Пока еще не было зарегистрировано ни одной станции.")


@admin_router.message(Command("changestatus"), StateFilter(default_state))
@admin_router.message(F.text == "Изменить статус станции", StateFilter(default_state))
async def cmd_change_status(message: Message, state: FSMContext):
    logging.info(
        f"Админ {message.from_user.id} начал процесс изменения статуса станции")

    await message.answer("Выберите станцию, статус которой вы хотите изменить:", reply_markup=get_station_selection_keyboard())
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
    await message.answer(f"Вы выбрали станцию: {selected_station_name}.\nТеперь выберите новый статус:", reply_markup=get_status_selection_keyboard())
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
    await message.answer(f"Статус станции {station_name} успешно изменен на {selected_status_text}.", reply_markup=get_admin_menu_keyboard())


@admin_router.message(StateFilter(FSMStationStatusChange.choose_station))
async def warning_invalid_station(message: Message):
    logging.warning(
        f"Админ {message.from_user.id} ввел некорректное название станции")
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


@admin_router.message(Command("showstationteams"))
@admin_router.message(F.text == "Показать команды на станции")
async def cmd_show_station_teams(message: Message, state: FSMContext):
    logging.info(
        f"Админ {message.from_user.id} начал процесс выбора станции для показа команд")

    await message.answer("Выберите станцию, для которой вы хотите посмотреть список команд:", reply_markup=get_station_selection_keyboard())
    await state.set_state(FSMShowStationTeams.choose_station)


@admin_router.message(StateFilter(FSMShowStationTeams.choose_station), F.text)
async def process_station_selected(message: Message, state: FSMContext):
    selected_station_name = message.text
    station = game_info.GetStationByName(selected_station_name)

    if station is None:
        logging.warning(f"Админ {message.from_user.id} выбрал некорректное название станции: {selected_station_name}")
        await message.answer("Станция не найдена. Пожалуйста, выберите корректное название станции.")
        return

    current_team = game_info.GetCurrentTeamOnStation(selected_station_name)
    leaving_team = game_info.GetLeavingTeamByStation(selected_station_name)

    if current_team is None and leaving_team is None:
        await message.answer(f"На станции {selected_station_name} нет зарегистрированных команд.")
    else:
        status_messages = []
        if current_team:
            status_messages.append(
                f"Команда '{current_team.GetName()}' находится на станции.")
        if leaving_team:
            status_messages.append(
                f"Команда '{leaving_team.GetName()}' покидает станцию.")
        await message.answer("\n".join(status_messages))

    await state.clear()
    await message.answer("Вы можете выбрать другую станцию или вернуться в главное меню.", reply_markup=get_admin_menu_keyboard())


@admin_router.message(StateFilter(FSMShowStationTeams.choose_station))
async def warning_invalid_station(message: Message):
    logging.warning(
        f"Админ {message.from_user.id} ввел некорректное название станции")
    await message.answer(
        f'Название станции некорректно.\n\n'
        f'Пожалуйста, выберите станцию из списка.\n\n'
        f'Если вы хотите прервать процесс, отправьте команду /cancel'
    )


@admin_router.message(F.text == "Сбросить команды на всех станциях")
@admin_router.message(Command("reset_all_stations_teams"), StateFilter(default_state))
async def reset_all_stations_teams_query(message: Message, state: FSMContext):
    await message.answer("Вы точно хотите сбросить команды на ВСЕХ станциях?", reply_markup=get_yes_no_keyboard())
    await state.update_data(confirm_action="reset_all_stations_teams")


@admin_router.message(StateFilter(default_state))
async def reset_all_stations_teams_action(message: Message, state: FSMContext):
    data = await state.get_data()
    confirm_action = data.get("confirm_action")

    if confirm_action != "reset_all_stations_teams" or message.text.lower() != "да":
        await message.answer(f"Сброс команд на всех станциях был отменен, вы можете выбрать следущую команду на клавиатуре.", reply_markup=get_admin_menu_keyboard())
        await state.clear()
        return

    for station_name, team_name in game_info.team_on_station.items():
        game_info.team_on_station[station_name] = None
        caretaker_id: int = game_info.GetCaretakersIDByStationName(station_name)
        await bot.send_message(caretaker_id, text=f"Админ сбросил команду, которая идёт или выполняет задание на вашей станции")

    for station_name, team_name in game_info.team_leaving_station.items():
        game_info.team_leaving_station[station_name] = None
        caretaker_id: int = game_info.GetCaretakersIDByStationName(station_name)
        await bot.send_message(caretaker_id, text=f"Админ сбросил команду, которая покидает вашу станцию")


    logging.info("У всех станций были очищены команды на них")
    await message.answer(
        "У всех станций были очищены команды на них\n\n"
        "ВНИМАНИЕ!!! Теперь нужно направить каждую команду на станцию, "
        "так как иначе ей будет некуда идти",
        reply_markup=get_admin_menu_keyboard()
    )

    await state.clear()

@admin_router.message(F.text == "Отправить команду на станцию")
@admin_router.message(Command("edit_team_station"), StateFilter(default_state))
async def edit_team_station(message: Message, state: FSMContext):
    await state.set_state(FSMEditTeamStation.choose_team)
    await message.answer(f"Выберете команду для которой хотите поменять станцию", reply_markup=get_team_keyboard())

@admin_router.message(StateFilter(FSMEditTeamStation.choose_team), lambda message: message.text in [team.GetName() for team in game_info.teams])
async def edit_team_station_choose_team(message: Message, state: FSMContext):
    await state.update_data(team_name= message.text)
    await message.answer(f"Вы выбрали команду {message.text}, если вы ошиблись напишите /cancel\n"
                         f"Если ваш выбор корректен, выберете локацию, на которую хотите отправить команду", reply_markup=get_location_keyboard())
    