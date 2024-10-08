from aiogram import Router, F
from aiogram.filters.command import Command
from aiogram.types import Message
from aiogram import types
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.filters import BaseFilter
from gameinfo import Station, StationStatus, Team
from bot import game_info, bot, logging


class IsCaretakerFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        user_id : int = message.from_user.id
        for caretaker_id, _ in game_info.caretakers.items():
            if caretaker_id == user_id:
                logging.info(f"IsCaretakerFilter: {user_id} is caretaker: {True}")
                return True
            
        logging.info(f"IsCaretakerFilter: {user_id} is caretaker: {True}")
        return False


caretaker_router = Router()
caretaker_router.message.filter(IsCaretakerFilter())


@caretaker_router.message(Command("start"))
async def cmd_start(message: types.Message):
    station = game_info.GetStationByCaretakerID(message.from_user.id)
    if station is None:
        logging.warning(f"Caretaker {message.from_user.id} попытался запустить команду /start, но не был найден для станции")
        await message.answer(f"Не было найдено станции за которую вы ответственны.")
        return

    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="Начать или продолжить работать со станцией"))

    logging.info(f"Caretaker {message.from_user.id} запустил команду /start для станции {station.GetName()}")
    await message.answer(
        f"Привет, {message.from_user.full_name}, твоя станция это - {station.GetName()}\n"
        f"Чтобы начать или продолжить работу, напиши команду: /go", reply_markup=builder.as_markup(resize_keyboard=True)
    )

@caretaker_router.message(Command("go"))
@caretaker_router.message(F.text.lower() ==  "начать или продолжить работать со станцией")
async def cmd_work(message: types.Message):
    logging.info(f"Caretaker {message.from_user.id} запустил команду /go")
    builder = ReplyKeyboardBuilder()

    builder.add(types.KeyboardButton(text="Принять новую команду"))
    builder.add(types.KeyboardButton(text="Перенаправить текущую команду"))

    builder.adjust(2)

    await message.answer(
        "Что вы хотите сделать?",
        reply_markup=builder.as_markup(resize_keyboard=True),
    )


@caretaker_router.message(F.text.lower() == "принять новую команду")
async def accept_new_task(message: types.Message):
    station = game_info.GetStationByCaretakerID(message.from_user.id)
    if station is None:
        logging.warning(f"Caretaker {message.from_user.id} попытался принять новую команду, но его станция не найдена")
        await message.reply("Не удалось найти вашу станцию.")
        return

    team = game_info.GetCurrentTeamOnStation(station.GetName())
    if team is None:
        logging.info(f"Caretaker {message.from_user.id} попытался принять новую команду, но на станции {station.GetName()} нет команды")
        await message.reply("На вашей станции нет команды.")
        return

    if  station.IsInProgress() :
        logging.warning(f"Caretaker {message.from_user.id} попытался принять новую команду, но станция {station.GetName()} уже занята")
        await message.reply("Станция уже занята.")
        return


    if game_info.HasLeavingTeam(station.GetName()):
        logging.warning(f"Caretaker {message.from_user.id} попытался принять новую команду, но станция {station.GetName()} еще не отправила прошлую команду дальше")
        await message.reply(f"Вы еще не отправили прошлую команду дальше")
        return

    team = game_info.GetCurrentTeamOnStation(station.GetName())
    location_name: str = station.GetName()[:-2]
    team.ToVisitLocation(location_name)
    station.SetStatus(StationStatus.IN_PROGRESS)
    logging.info(f"Caretaker {message.from_user.id} принял команду {team.GetName()} на станцию {station.GetName()}")


    await message.reply(f"Вы успешно приняли новую команду '{team.GetName()}' на станцию {station.GetName()}.")
    game_info.update_game_info()  



@caretaker_router.message(F.text.lower() == "перенаправить текущую команду")
async def redirect_task(message: types.Message):
    station = game_info.GetStationByCaretakerID(message.from_user.id)
    if station is None:
        logging.warning(f"Caretaker {message.from_user.id} попытался перенаправить команду, но станция не найдена")
        await message.reply("Не удалось найти вашу станцию.")
        return

    team = game_info.GetCurrentTeamOnStation(station.GetName())


    if not game_info.HasLeavingTeam(station.GetName()) and not (team is None) and station.IsInProgress():
        game_info.StartLeavingStation(station.GetName())
        station.SetStatus(StationStatus.FREE)



        if not (team is None) and len(team.GetToVisitList()) == 0:
            game_info.LeaveStation(station.GetName())
            await message.answer(f"Команда {team.GetName()} посетила все станции, некуда перенаправить ее\n\n"
                                 f"Можете принимать новую команду, если она назначена")
            game_info.update_game_info()  
            return
            


        next_station = game_info.GetNextFreeStation(team.GetName())
        if next_station is None:
            logging.error(f"Caretaker {message.from_user.id} попытался перенаправить команду, но все станции заняты")
            await message.reply("Пока что все станции заняты. Повторите попытку немного позже")
            return
        
        next_station.SetStatus(StationStatus.WAITING)
        game_info.LeaveStation(station.GetName())
        game_info.SendTeamOnStation(team.GetName(), next_station.GetName())

        next_caretakers_id: tuple[int, int] = game_info.GetCaretakersIDByStationName(next_station.GetName())
        next_caretaker_id_1: int = next_caretakers_id[0]
        next_caretaker_id_2: int = next_caretakers_id[1]

        team_name = team.GetName()

        if  next_caretaker_id_1 != game_info.BAD_ID: 
            logging.info(f"Найден куратор с id {next_caretaker_id_1} к нему идет команда {team_name}")
            await bot.send_message(next_caretaker_id_1, f"На вашу станцию направлена команда {team_name}")

        if  next_caretaker_id_2 != game_info.BAD_ID:
            logging.info(f"Найден куратор с id {next_caretaker_id_2} к нему идет команда {team_name}")
            await bot.send_message(next_caretaker_id_2, f"На вашу станцию направлена команда {team_name}")


        logging.info(f"Команда {team.GetName()} перенаправлена со станции {station.GetName()} на станцию {next_station.GetName()}")
        await message.answer(f"Команда '{team.GetName()}' перенаправлена на станцию {next_station.GetName()}.")
        game_info.update_game_info()  
        return
    
    if game_info.HasLeavingTeam(station.GetName()):
        team_leaving_station: Team = game_info.GetLeavingTeamByStation(station.GetName())

        if not (team_leaving_station is None) and len(team_leaving_station.GetToVisitList()) == 0:
            
            game_info.LeaveStation(station.GetName())
            await message.answer(f"Команда {team.GetName()} посетила все станции, некуда перенаправить ее\n\n"
                                 f"Можете принимать новую команду, если она назначена")
            game_info.update_game_info()  
            return
            


        next_station = game_info.GetNextFreeStation(team_leaving_station.GetName())
        if next_station is None:
            logging.error(f"Caretaker {message.from_user.id} попытался перенаправить команду, но все станции заняты")
            await message.reply("Пока что все станции заняты. Повторите попытку немного позже")
            return
        
        next_station.SetStatus(StationStatus.WAITING)
        game_info.LeaveStation(station.GetName())
        game_info.SendTeamOnStation(team_leaving_station.GetName(), next_station.GetName()) 
        team_name = team_leaving_station.GetName()

        next_caretakers_id: tuple[int, int] = game_info.GetCaretakersIDByStationName(next_station.GetName())
        next_caretaker_id_1: int = next_caretakers_id[0]
        next_caretaker_id_2: int = next_caretakers_id[1]

        if  next_caretaker_id_1 != game_info.BAD_ID: 
            logging.info(f"Найден куратор с id {next_caretaker_id_1} к нему идет команда {team_name}")
            await bot.send_message(next_caretaker_id_1, f"На вашу станцию направлена команда {team_name}")

        if  next_caretaker_id_2 != game_info.BAD_ID:
            logging.info(f"Найден куратор с id {next_caretaker_id_2} к нему идет команда {team_name}")
            await bot.send_message(next_caretaker_id_2, f"На вашу станцию направлена команда {team_name}")

        logging.info(f"Команда {team_leaving_station.GetName()} перенаправлена со станции {station.GetName()} на станцию {next_station.GetName()}")
        await message.answer(f"Команда '{team_leaving_station.GetName()}' перенаправлена на станцию {next_station.GetName()}.")
        game_info.update_game_info()  
        return

    if not game_info.HasLeavingTeam(station.GetName()) and not game_info.HasTeam(station.GetName()):
        logging.warning(f"Caretaker {message.from_user.id} попытался перенаправить команду со своей станции, но на ней никого не оказалось")
        await message.answer(f"На данной станции нет ни одной команды, некого перенаправлять")
        return

    if not game_info.HasLeavingTeam(station.GetName()) and game_info.HasTeam(station.GetName()) and station.IsWaiting():
        await message.answer(f"Некого перенаправлять, команда еще не дошла до вашей станции, или вы забыли нажать кнопку 'Принять новую команду'.")
        return
    
    


