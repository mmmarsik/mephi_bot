        

# from aiogram import Router, F
# from aiogram.filters.command import Command
# from aiogram.types import Message
# from aiogram import types
# from aiogram.utils.keyboard import ReplyKeyboardBuilder
# from aiogram.filters import BaseFilter
# from gameinfo import Station, StationStatus, Team
# from bot import game_info, bot, logging


# class IsCaretakerFilter(BaseFilter):
#     async def __call__(self, message: Message) -> bool:
#         user_id : int = message.from_user.id
#         for caretaker_id, _ in game_info.caretakers.items():
#             if caretaker_id == user_id:
#                 logging.info(f"IsCaretakerFilter: {user_id} is caretaker: {True}")
#                 return True
            
#         logging.info(f"IsCaretakerFilter: {user_id} is caretaker: {True}")
#         return False


# caretaker_router = Router()
# caretaker_router.message.filter(IsCaretakerFilter())


# @caretaker_router.message(Command("start"))
# async def cmd_start(message: types.Message):
#     station = game_info.GetStationByCaretakerID(message.from_user.id)
#     if station is None:
#         logging.warning(f"Caretaker {message.from_user.id} попытался запустить команду /start, но не был найден для станции")
#         await message.answer(f"Не было найдено станции за которую вы ответственны.")
#         return

#     builder = ReplyKeyboardBuilder()
#     builder.add(types.KeyboardButton(text="Начать работать со станцией"))

#     logging.info(f"Caretaker {message.from_user.id} запустил команду /start для станции {station.GetName()}")
#     await message.answer(
#         f"Привет, {message.from_user.full_name}, твоя станция это - {station.GetName()}\n"
#         f"Чтобы начать, напиши команду: /go", reply_markup=builder.as_markup(resize_keyboard=True)
#     )

# @caretaker_router.message(Command("go"))
# @caretaker_router.message(F.text.lower() ==  "начать работать со станцией")
# async def cmd_work(message: types.Message):
#     logging.info(f"Caretaker {message.from_user.id} запустил команду /go")
#     builder = ReplyKeyboardBuilder()

#     builder.add(types.KeyboardButton(text="Принять новую команду"))
#     builder.add(types.KeyboardButton(text="Перенаправить текущую команду"))

#     builder.adjust(2)

#     await message.answer(
#         "Что вы хотите сделать?",
#         reply_markup=builder.as_markup(resize_keyboard=True),
#     )


# @caretaker_router.message(F.text.lower() == "принять новую команду")
# async def accept_new_task(message: types.Message):
#     station = game_info.GetStationByCaretakerID(message.from_user.id)
#     if station is None:
#         logging.warning(f"Caretaker {message.from_user.id} попытался принять новую команду, но его станция не найдена")
#         await message.reply("Не удалось найти вашу станцию.")
#         return

#     team = game_info.GetCurrentTeamOnStation(station.GetName())
#     if team is None:
#         logging.info(f"Caretaker {message.from_user.id} попытался принять новую команду, но на станции {station.GetName()} нет команды")
#         await message.reply("На вашей станции нет команды.")
#         return

#     if not station.IsWaiting() :
#         logging.warning(f"Caretaker {message.from_user.id} попытался принять новую команду, но станция {station.GetName()} уже занята")
#         await message.reply("Станция уже занята.")
#         return
    
#     if game_info.HasLeavingTeam(station.GetName()):
#         logging.warning(f"Caretaker {message.from_user.id} попытался принять новую команду, но станция {station.GetName()} еще не отправила прошлую команду дальше")
#         await message.reply(f"Вы еще не отправили прошлую команду дальше")
#         return

#     station.SetStatus(StationStatus.IN_PROGRESS)
#     logging.info(f"Caretaker {message.from_user.id} принял команду {team.GetName()} на станцию {station.GetName()}")
#     await message.reply(f"Вы успешно приняли новую команду '{team.GetName()}' на станцию {station.GetName()}.")


# @caretaker_router.message(F.text.lower() == "перенаправить текущую команду")
# async def redirect_task(message: types.Message):
#     station = game_info.GetStationByCaretakerID(message.from_user.id)

#     if station is None:
#         logging.warning(f"Caretaker {message.from_user.id} попытался перенаправить команду, но станция не найдена")
#         await message.reply("Не удалось найти вашу станцию.")
#         return

#     station_name: str = station.GetName()

#     team_on_station: Team = game_info.GetCurrentTeamOnStation(station_name)

#     if not game_info.HasLeavingTeam(station_name) and game_info.HasTeam(station_name) and not team_on_station is None and station.IsInProgress():
#         game_info.StartLeavingStation(station_name)
#         station.SetStatus(StationStatus.FREE)

#     team_leaving_station: Team = game_info.GetLeavingTeamByStation(station_name)

#     if game_info.HasLeavingTeam(station_name) and not team_leaving_station is None:

#         if len(team_leaving_station.GetToVisitList()) == 0:
#             logging.info(f"Caretaker с ID {message.from_user.id} хочет перенаправить команду {team_leaving_station.GetName()} на другую станцию, но\n"
#                          f"данная команда прошла все локации и закачивает квест")   
#             await message.reply(f"Команда {team_leaving_station.GetName()} прошла все станции, квест для нее считается законченным"
#                                 f"Если к вам идет новая команда нажмите 'Принять новую команду' .")     
#             return
        
#         next_station: Station = game_info.GetNextFreeStation(team_leaving_station.GetName())

#         if next_station is None:
#             logging.warning(f"Caretaker с ID {message.from_user.id} хочет перенаправить команду {team_leaving_station.GetName()} на другую станцию, но\n"
#                             f"Все станции пока что заняты")
#             await message.reply(f"Пока что нет свободных локаций для данной команды, повторите попытку немного позже")
#             return
        
#         next_station.SetStatus(StationStatus.WAITING)
#         game_info.LeaveStation(station.GetName())
#         game_info.SendTeamOnStation(team_leaving_station.GetName(), station.GetName())
#         location_name: str = next_station.GetName()[:-2]
#         team_leaving_station.ToVisitLocation(location_name)
#         next_station_caretaker_id = game_info.GetCaretakersIDByStationName(next_station.GetName())
#         if next_station_caretaker_id:
#             logging.info(f"Caretaker {message.from_user.id} перенаправил команду {team_leaving_station.GetName()} на станцию {next_station.GetName()} (ID куратора {next_station_caretaker_id})")
#             await bot.send_message(next_station_caretaker_id, f"К вам идет команда '{team_leaving_station.GetName()}'.")


#         logging.info(f"Caretaker с ID {message.from_user.id} перенаправил команду {team_leaving_station.GetName()} на станцию {next_station.GetName()}")
#         await message.reply(f"Вы успешно перенаправили команду {team_leaving_station.GetName()} на станцию {next_station.GetName()}")
#         return



#     if not game_info.HasTeam(station_name) and not game_info.HasLeavingTeam(station_name):
#         logging.warning(f"Caretaker {message.from_user.id} попытался перенаправить команду, но станция пуста")
#         await message.reply(f"На вашей станции нет ни одной команды, некого перенаправлять")
#         return
    
#     if not game_info.HasLeavingTeam(station.GetName()) and game_info.HasTeam(station.GetName()) and station.IsWaiting():
#         await message.answer(f"Некого перенаправлять, команда еще не дошла до вашей станции, или вы забыли нажать кнопку 'Принять новую команду'.")
#         return
    
    

