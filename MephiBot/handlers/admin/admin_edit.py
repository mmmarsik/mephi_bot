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

class IsStationNameFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        for location in game_info.locations:
            for station in location.stations:
                if message.text == station.GetName():
                    return True
        
        return False

edit_router= Router()


@edit_router.message(Command("cancel"), StateFilter(FSMStationStatusChange))
async def cancel_status_change(message: Message, state: FSMContext):
    logging.info(f"Админ {message.from_user.id} отменил процесс изменения статуса станции")
    await state.clear()
    await message.answer(f"Процесс изменения статуса станции был отменен. Вы можете начать процесс снова, отправив команду /changestatus", 
                         reply_markup=get_admin_menu_keyboard())
    
@edit_router.message(F.text == "Редактировать станцию у команды")
@edit_router.message(Command("edit_team_station"), StateFilter(default_state))
async def edit_team_station(message: Message, state: FSMContext):
    await state.set_state(FSMEditTeamStation.choose_team)
    await message.answer(f"Выберете команду для которой хотите поменять станцию", 
                         reply_markup=get_team_keyboard())

@edit_router.message(StateFilter(FSMEditTeamStation.choose_team), 
                      lambda message: message.text in [team.GetName() for team in game_info.teams])
async def edit_team_station_correct_team(message: Message, state: FSMContext):
    await state.update_data(team_name= message.text)
    await state.set_state(FSMEditTeamStation.choose_location)
    await message.answer(f"Вы выбрали команду {message.text}, если вы ошиблись напишите /cancel\n"
                         f"Если ваш выбор корректен, выберете локацию, на которую хотите отправить команду", 
                         reply_markup=get_location_keyboard())

@edit_router.message(StateFilter(FSMEditTeamStation.choose_team))
async def edit_team_station_invalid_team(message: Message, state: FSMContext):
    await message.answer(f"Вы отправили что-то некорректное, выберете команду заново", 
                         reply_markup=get_team_keyboard())

@edit_router.message(StateFilter(FSMEditTeamStation.choose_location), 
                      lambda message: message.text in [location.GetName() for location in game_info.locations])
async def edit_team_station_correct_location(message: Message, state: FSMContext):
    await state.update_data(location_name= message.text)
    await state.set_state(FSMEditTeamStation.choose_station)

    location_name: str = message.text

    reply_markup = get_stations_by_location_keyboard(location_name)

    await message.answer(f"Вы выбрали локацию {location_name}, если вы ошиблись напишите /cancel\n"
                         f"Если ваш выбор корректен, выберете станцию, на которую хотите отправить команду", 
                         reply_markup=reply_markup)

@edit_router.message(StateFilter(FSMEditTeamStation.choose_location))
async def edit_team_station_invalid_location(message: Message, state: FSMContext):
    await message.answer(f"Вы отправили что-то некорректное, выберете локацию заново", 
                         reply_markup=get_location_keyboard())



@edit_router.message(StateFilter(FSMEditTeamStation.choose_station), IsStationNameFilter())
async def edit_team_station_choose_station(message: Message, state: FSMContext):
    data = await state.get_data()
    location_name = data.get("location_name")
    station_name = message.text
    team_name = data.get("team_name")

    reply_markup = get_stations_by_location_keyboard(location_name)

    if station_name[:-2] != location_name:
        await message.answer(f"Вы выбрали локацию {location_name}, но в качестве станции указали {station_name}. \
                             Данная станция не соответствует выбранной локации, выберете станцию еще раз", 
                             reply_markup=reply_markup)
        return
    
    await state.update_data(station_name= station_name)
    await state.set_state(FSMEditTeamStation.accept_info)
    await message.answer(f"Вы выбрали команду {team_name} и хотите отправить ее на станцию {station_name}. Верно ?",
                          reply_markup=get_yes_no_keyboard())


@edit_router.message(StateFilter(FSMEditTeamStation.choose_station))
async def edit_team_station_invalid_name(message: Message, state: FSMContext):
    data = await state.get_data()
    location_name = data.get("location_name")
    reply_markup = get_stations_by_location_keyboard(location_name)

    await message.answer(f"Вы ввели что-то некорректное попробуйте выбрать название станции еще раз", 
                         reply_markup= reply_markup)

@edit_router.message(StateFilter(FSMEditTeamStation.accept_info), 
                      lambda message: message.text.lower() in ["да", "нет"])
async def edit_team_station_accept_choice(message: Message, state: FSMContext):
    data = await state.get_data()
    team_name = data.get("team_name")
    station_name = data.get("station_name")
    
    if message.text.lower() == "да":
        game_info.team_on_station[station_name] = team_name

        for prev_station_name, team_name_ in game_info.team_on_station.items():
            if team_name == team_name_:
                game_info.team_on_station[prev_station_name] = None
                station_ = game_info.GetStationByName(prev_station_name)

                if not game_info.HasLeavingTeam(prev_station_name):
                    station_.SetStatus(StationStatus.FREE)

                                    

                caretaker_id: list[int] = game_info.GetCaretakersIDByStationName(prev_station_name)

                if caretaker_id[0] != game_info.BAD_ID:
                    await bot.send_message(caretaker_id[0], 
                                           text=f"Админ убрал команду {team_name} с вашей станции.")

                if caretaker_id[1] != game_info.BAD_ID:
                    await bot.send_message(caretaker_id[1], 
                                            text=f"Админ убрал команду {team_name} с вашей станции.")

        for prev_station_name, team_name_ in game_info.team_leaving_station.items():
            if team_name == team_name_:
                game_info.team_leaving_station[prev_station_name] = None
                station_ = game_info.GetStationByName(prev_station_name)

                if not game_info.HasTeam(prev_station_name):
                    station_.SetStatus(StationStatus.FREE)

                caretaker_id: list[int] = game_info.GetCaretakersIDByStationName(prev_station_name)

                if caretaker_id[0] != game_info.BAD_ID:
                    await bot.send_message(caretaker_id[0], 
                                           text=f"Админ убрал команду {team_name} с вашей станции.")

                if caretaker_id[1] != game_info.BAD_ID:
                    await bot.send_message(caretaker_id[1],  
                                           text=f"Админ убрал команду {team_name} с вашей станции.")

            
        caretaker_id: list[int] = game_info.GetCaretakersIDByStationName(station_name)

        if caretaker_id[0] != game_info.BAD_ID:
            await bot.send_message(caretaker_id[0], 
                                   text=f"Админ переназначил команду на вашей станции, теперь это {team_name}.")

        if caretaker_id[1] != game_info.BAD_ID:
            await bot.send_message(caretaker_id[1],
                                    text=f"Админ переназначил команду на вашей станции, теперь это {team_name}..")
        
        await message.answer(f"Вы успешно назначили команде {team_name} станцию {station_name}. \
                             ОБЯЗАТЕЛЬНО передайте данную информацию команде, иначе она об этом не узнает",
                             reply_markup=get_admin_menu_keyboard())
    
    if message.text.lower() == "нет":
        await message.answer(f"Процесс редактирования станции для команды {team_name} был отменен.", 
                             reply_markup=get_admin_menu_keyboard( ))

    await state.clear()

@edit_router.message(StateFilter(FSMEditTeamStation.accept_info))
async def edit_team_station_invalid_accept(message: Message, state: FSMContext):
    data = await state.get_data()
    team_name = data.get("team_name")
    station_name = data.get("station_name")

    await message.answer(f"Вы ввели что-то некорректное. Вы согласны отправить команду {team_name} на станцию {station_name} ?", 
                         reply_markup=get_yes_no_keyboard())



@edit_router.message(F.text == "Редактировать список локаций для опр. команды")
@edit_router.message(Command(commands='edit_command_stations'))
async def cmd_edit_stations(message: Message, state: FSMContext):

    print(f"опа логирование")
    if len(game_info.teams) == 0:
        logging.warning(f"Админ {message.from_user.id} хотел редактировать список посещенных станций для команд, \
                        но пока еще не зарегистрировано ни одной команды")
        await message.answer(f"Пока что ни одной команды не было зарегистрировано, не у кого менять список посещенных станций")
        return

    await message.answer("Выберите команду:", reply_markup=get_team_keyboard())
    await state.set_state(FSMEditStation.choosing_team)


@edit_router.message(FSMEditStation.choosing_team)
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
    await message.answer(f"Команда {team_name} выбрана. Выберите действие:", 
                         reply_markup=get_edit_action_keyboard())
    await state.set_state(FSMEditStation.editing_stations)


@edit_router.message(FSMEditStation.editing_stations)
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


@edit_router.message(FSMEditStation.adding_station)
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
                             f"Если хотите попробовать еще раз нажмите кнопку или напишите /edit_command_stations", 
                             reply_markup=get_admin_menu_keyboard())
        await state.clear()
        return

    if location_name not in team.to_visit_list:
        team.to_visit_list.append(location_name)
        await message.answer(f"Станция {location_name} добавлена в список станций для посещения команды {team_name}.\n\n"
                             f"Если хотите попробовать еще раз нажмите кнопку или напишите /edit_command_stations",
                               reply_markup=get_admin_menu_keyboard())
    else:
        await message.answer(f"Станция {location_name} уже в списке станций для посещения команды {team_name}.\n\n"
                             f"Если хотите попробовать еще раз нажмите кнопку или напишите /edit_command_stations", 
                             reply_markup=get_admin_menu_keyboard())

    await state.clear()


@edit_router.message(FSMEditStation.removing_station)
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
                             f"Если хотите попробовать еще раз нажмите кнопку или напишите /edit_command_stations", 
                             reply_markup=get_admin_menu_keyboard())
        await state.clear()
        return

    to_visit_list: list[str] = team.GetToVisitList()

    if location_name in to_visit_list:
        team.to_visit_list.remove(location_name)

        await message.answer(f"Локация {location_name} удалена из списка станций для посещения команды {team_name}.\n\n"
                             f"Если хотите попробовать еще раз нажмите кнопку или напишите /edit_command_stations",
                               reply_markup=get_admin_menu_keyboard())
    else:
        print(f"\n\n\n\n\n {to_visit_list} \n\n\n\n\n ")

        await message.answer(f"Станция {location_name} не найдена в списке станций для посещения команды {team_name}.\n\n"
                             f"Если хотите попробовать еще раз нажмите кнопку или напишите /edit_command_stations",
                               reply_markup=get_admin_menu_keyboard())

    await state.clear()


async def cancel_editing(message: Message, state: FSMContext):
    await message.answer("Редактирование отменено.\n\n"
                         f"Если хотите попробовать еще раз нажмите кнопку или напишите /edit_command_stations",
                           reply_markup=get_admin_menu_keyboard())
    await state.clear()

@edit_router.message(Command("changestatus"), StateFilter(default_state))
@edit_router.message(F.text == "Изменить статус станции", StateFilter(default_state))
async def cmd_change_status(message: Message, state: FSMContext):
    logging.info(
        f"Админ {message.from_user.id} начал процесс изменения статуса станции")

    await message.answer("Выберите станцию, статус которой вы хотите изменить:", 
                         reply_markup=get_station_selection_keyboard())
    await state.set_state(FSMStationStatusChange.choose_station)


@edit_router.message(StateFilter(FSMStationStatusChange.choose_station), F.text)
async def process_station_selected(message: Message, state: FSMContext):
    selected_station_name = message.text
    station = game_info.GetStationByName(selected_station_name)

    if station is None:
        logging.warning(f"Админ {message.from_user.id} выбрал некорректное название станции: {selected_station_name}")
        await message.answer("Станция не найдена. Пожалуйста, выберите корректное название станции.")
        return

    await state.update_data(station_name=selected_station_name)
    await message.answer(f"Вы выбрали станцию: {selected_station_name}.\nТеперь выберите новый статус:", 
                         reply_markup=get_status_selection_keyboard())
    await state.set_state(FSMStationStatusChange.choose_status)


@edit_router.message(StateFilter(FSMStationStatusChange.choose_status), F.text)
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
    await message.answer(f"Статус станции {station_name} успешно изменен на {selected_status_text}.", 
                         reply_markup=get_admin_menu_keyboard())


@edit_router.message(StateFilter(FSMStationStatusChange.choose_station))
async def warning_invalid_station(message: Message):
    logging.warning(
        f"Админ {message.from_user.id} ввел некорректное название станции")
    await message.answer(
        f'Название станции некорректно.\n\n'
        f'Пожалуйста, выберите станцию из списка.\n\n'
        f'Если вы хотите прервать процесс изменения статуса, отправьте команду /cancel'
    )


@edit_router.message(StateFilter(FSMStationStatusChange.choose_status))
async def warning_invalid_status(message: Message):
    logging.warning(f"Админ {message.from_user.id} ввел некорректный статус")
    await message.answer(
        f'Некорректный статус.\n\n'
        f'Пожалуйста, выберите статус из предложенных вариантов.\n\n'
        f'Если вы хотите прервать процесс изменения статуса, отправьте команду /cancel'
    )


@edit_router.message(F.text == "Сбросить команды на всех станциях")
@edit_router.message(Command("reset_all_stations_teams"), StateFilter(default_state))
async def reset_all_stations_teams_query(message: Message, state: FSMContext):
    await state.set_state(FSMResetAllStationsTeams.accept_info)
    await message.answer("Вы точно хотите сбросить команды на ВСЕХ станциях?", 
                         reply_markup=get_yes_no_keyboard())

@edit_router.message(StateFilter(FSMResetAllStationsTeams.accept_info), 
                      lambda message: message.text.lower() in ["да", "нет"])
async def reset_all_stations_teams_action(message: Message, state: FSMContext):
    if message.text.lower() != "да":
        await state.clear()
        await message.answer("Действие отменено.", reply_markup=get_admin_menu_keyboard())
        return

    for station_name, team_name in game_info.team_on_station.items():
        game_info.team_on_station[station_name] = None

        station = game_info.GetStationByName(station_name)
        station.SetStatus(StationStatus.FREE)

        caretaker_id: list[int] = game_info.GetCaretakersIDByStationName(station_name)

        if caretaker_id[0] != game_info.BAD_ID:
            await bot.send_message(caretaker_id[0],
                                    text=f"Админ сбросил команду, которая идет на вашу станцию или выполняет на ней задание.")

        if caretaker_id[1] != game_info.BAD_ID:
            await bot.send_message(caretaker_id[1], 
                                   text=f"Админ сбросил команду, которая идет на вашу станцию или выполняет на ней задание.")

    for station_name, team_name in game_info.team_leaving_station.items():
        game_info.team_leaving_station[station_name] = None

        station = game_info.GetStationByName(station_name)
        station.SetStatus(StationStatus.FREE)

        caretaker_id: list[int] = game_info.GetCaretakersIDByStationName(station_name)

        if caretaker_id[0] != game_info.BAD_ID:
            await bot.send_message(caretaker_id[0], 
                                   text=f"Админ сбросил команду, которая покидает вашу станцию.")

        if caretaker_id[1] != game_info.BAD_ID:
            await bot.send_message(caretaker_id[1], 
                                   text=f"Админ сбросил команду, которая покидает вашу станцию.")

    logging.info("У всех станций были очищены команды на них")
    await message.answer(
        "У всех станций были очищены команды на них\n\n"
        "ВНИМАНИЕ!!! Теперь нужно направить каждую команду на станцию, "
        "так как иначе ей будет некуда идти",
        reply_markup=get_admin_menu_keyboard()
    )

    await state.clear()

@edit_router.message(F.text == "Сбросить команды на конкретной станции", StateFilter(default_state))
@edit_router.message(Command("reset_selected_station"), StateFilter(default_state))
async def reset_selected_station(message: Message, state: FSMContext):
    await message.answer(f"Сначала выберете локацию у которой хотите сбросить команды", reply_markup=get_location_keyboard())
    await state.set_state(FSMResetSelectedStation.choose_location)

@edit_router.message(StateFilter(FSMResetSelectedStation.choose_location), 
                      lambda message: message.text in [location.GetName() for location in game_info.locations])
async def reset_selected_station_choose_location(message: Message, state: FSMContext):
    state.update_data(location_name = message.text)
    
    reply_markup = get_stations_by_location_keyboard(message.text)

    await state.set_state(FSMResetSelectedStation.choose_station)
    await message.answer(f"Вы выбрали локацию {message.text}, далее выберете станцию из данной локации.\n"
                         f"Если хотите отменить действие напишите /cancel", 
                         reply_markup=reply_markup)

@edit_router.message(StateFilter(FSMResetSelectedStation.choose_location))
async def reset_selected_station_invalid_location_name(message: Message, state: FSMContext):
    await message.answer(f"Вы ввели некорректное название локации, если хотите отменить процесс, то напишите /cancel\n"
                         f"Если вы хотите выбрать локацию еще раз, то нажмите кнопку", 
                         reply_markup=get_location_keyboard())

@edit_router.message(StateFilter(FSMResetSelectedStation.choose_station), IsStationNameFilter())
async def reset_selected_station_choose_station(message: Message, state: FSMContext):
    station_name = message.text
    await state.update_data(station_name=station_name)
    await state.set_state(FSMResetSelectedStation.accept_info)

    await message.answer(f"Вы выбрали станцию {station_name}, Вы уверены ?", 
                         reply_markup= get_yes_no_keyboard())

@edit_router.message(StateFilter(FSMResetSelectedStation.choose_station))
async def reset_selected_station_invalid_station(message: Message, state: FSMContext):
    data = await state.get_data()
    location_name = data.get(location_name)

    await message.answer(f"Вы ввели некорректное название станции, если хотите отменить процесс - напишите /cancel\n"
                         f"Если вы хотите попробовать еще раз, то веберете заново название станции", 
                         reply_markup=get_stations_by_location_keyboard(location_name))

@edit_router.message(StateFilter(FSMResetSelectedStation.accept_info), 
                      lambda message: message.text.lower() in ["да",  "нет"])
async def reset_selected_station_accept_info(message: Message, state: FSMContext):
    data = await state.get_data()
    station_name = data.get("station_name")

    await state.clear()

    if message.text.lower() == "да":
        game_info.team_on_station[station_name] = None
        game_info.team_leaving_station[station_name] = None

        station = game_info.GetStationByName(station_name)
        station.SetStatus(StationStatus.FREE)

        caretaker_id: list[int] = game_info.GetCaretakersIDByStationName(station_name)

        if caretaker_id[0] != game_info.BAD_ID:
            await bot.send_message(caretaker_id[0], 
                                   text=f"Админ сбросил команду, которая покидает вашу станцию.")

        if caretaker_id[1] != game_info.BAD_ID:
            await bot.send_message(caretaker_id[1], 
                                   text=f"Админ сбросил команду, которая покидает вашу станцию.")
        
        await message.answer(f"Вы успешно сбросили команды на станции {station_name}"
                             f"ВНИМАНИЕ !!! Не забудьте назначить командам, которые находились сейчас на данной станции следующую\n"
                             f"Иначе команда не сможет продолжить выполнения квеста", reply_markup=get_admin_menu_keyboard())
    
    if message.text.lower() == "нет":
        await message.answer(f"Процесс сброса команд на станции {station_name} был отменен", reply_markup=get_admin_menu_keyboard())
    
@edit_router.message(StateFilter(FSMResetSelectedStation.accept_info))
async def reset_selected_station_accept_info_invalid(message: Message, state: FSMContext):
    data = await state.get_data()
    station_name = data.get("station_name")

    await message.answer(f"Вы ввели что-то некорректное.\n"
                         f"Вы хотите сбросить команды на станции {station_name} ?", reply_markup=get_yes_no_keyboard())

@edit_router.message(F.text == "Найти команды без станций")
@edit_router.message(Command("find_teams_without_station"))
async def find_teams_without_station(message: Message):
    teams_without_station: set[str] = set()

    for team in game_info.teams:
        if len(team.GetToVisitList()) > 0:
            if not team.GetName() in game_info.team_on_station.values():
                teams_without_station.add(team.GetName())
            
            if not team.GetName() in game_info.team_leaving_station.values():
                teams_without_station.add(team.GetName())

    if len(teams_without_station) == 0:
        await message.answer(f"У всех команд назначена станция", reply_markup=get_admin_menu_keyboard())
        return

    await message.answer(f"Вот список команд у которых не назначено ни одной станции\n"
                        f"{list(teams_without_station)}", reply_markup=get_admin_menu_keyboard())
    