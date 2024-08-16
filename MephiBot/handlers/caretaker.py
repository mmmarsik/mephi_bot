from aiogram import Router, F
from aiogram.filters.command import Command
from aiogram.types import Message
from aiogram import types
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.filters import BaseFilter

from GameInfo import Station, StationStatus
from bot import game_info, bot, logging


class IsCaretakerFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        user_id : int = message.from_user.id
        print(f"{user_id}")
        print(len(game_info.caretakers))
        for caretaker_id, _ in game_info.caretakers:
            if caretaker_id == user_id:
                is_caretaker = True
                logging.info(f"IsCaretakerFilter: {user_id} is caretaker: {is_caretaker}")
                return True
        return False


caretaker_router = Router()
caretaker_router.message.filter(IsCaretakerFilter())


@caretaker_router.message(Command("start"))
async def cmd_start(message: types.Message):
    station = game_info.GetStationByID(message.from_user.id)
    if station is None:
        logging.warning(f"Caretaker {message.from_user.id} попытался запустить команду /start, но не был найден для станции")
        await message.answer(f"Не было найдено станции за которую вы ответственны.")
        return

    logging.info(f"Caretaker {message.from_user.id} запустил команду /start для станции {station.GetName()}")
    await message.answer(
        f"Привет, {message.from_user.full_name}, твоя станция это - {station.GetName()}\n"
        f"Чтобы начать, напиши команду: /go"
    )


@caretaker_router.message(Command("go"))
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
    station = game_info.GetStationByID(message.from_user.id)
    if station is None:
        logging.warning(f"Caretaker {message.from_user.id} попытался принять новую команду, но его станция не найдена")
        await message.reply("Не удалось найти вашу станцию.")
        return

    team = game_info.GetTeamByStation(station.GetName())
    if team is None:
        logging.info(f"Caretaker {message.from_user.id} попытался принять новую команду, но на станции {station.GetName()} нет команды")
        await message.reply("На вашей станции нет команды.")
        return

    if not station.IsFree():
        logging.warning(f"Caretaker {message.from_user.id} попытался принять новую команду, но станция {station.GetName()} уже занята")
        await message.reply("Станция уже занята.")
        return

    station.SetStatus(StationStatus.IN_PROGRESS)
    logging.info(f"Caretaker {message.from_user.id} принял команду {team.GetName()} на станцию {station.GetName()}")
    await message.reply(f"Вы успешно приняли новую команду '{team.GetName()}' на станцию {station.GetName()}.")


@caretaker_router.message(F.text.lower() == "перенаправить текущую команду")
async def redirect_task(message: types.Message):
    station = game_info.GetStationByID(message.from_user.id)
    if station is None:
        logging.warning(f"Caretaker {message.from_user.id} попытался перенаправить команду, но станция не найдена")
        await message.reply("Не удалось найти вашу станцию.")
        return

    team = game_info.GetTeamByStation(station.GetName())
    if team is None:
        logging.info(f"Caretaker {message.from_user.id} попытался перенаправить команду, но на станции {station.GetName()} нет команды")
        await message.reply("На вашей станции нет команды для перенаправления.")
        return

    if not station.IsInProgress():
        logging.warning(f"Caretaker {message.from_user.id} попытался перенаправить команду, но станция {station.GetName()} не в процессе работы")
        await message.reply("Станция не в процессе работы. Невозможно перенаправить команду.")
        return

    next_station = game_info.GetNextFreeStation(team.GetName())
    if next_station is None:
        logging.error(f"Caretaker {message.from_user.id} попытался перенаправить команду, но все станции заняты")
        await message.reply("Нет доступных станций для перенаправления.")
        return

    station.SetStatus(StationStatus.FREE)
    game_info.ResetTeamOnStation(station.GetName())
    next_station.SetStatus(StationStatus.WAITING)

    location_name: str = next_station.GetName()[:-2]
    team.ToVisitLocation(location_name)
    next_station_caretaker_id = game_info.GetIDByStationName(next_station.GetName())
    game_info.SendTeamOnStation(team.GetName(), next_station.GetName())

    if next_station_caretaker_id:
        logging.info(f"Caretaker {message.from_user.id} перенаправил команду {team.GetName()} на станцию {next_station.GetName()} (ID куратора {next_station_caretaker_id})")
        await bot.send_message(next_station_caretaker_id, f"К вам идет команда '{team.GetName()}'.")

    logging.info(f"Команда {team.GetName()} перенаправлена со станции {station.GetName()} на станцию {next_station.GetName()}")
    await message.answer(f"Команда '{team.GetName()}' перенаправлена на станцию {next_station.GetName()}.")


