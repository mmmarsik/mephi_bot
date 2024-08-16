from aiogram import Router, F
from aiogram.filters.command import Command
from aiogram.types import Message
from aiogram import Bot, Dispatcher, types
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.filters import BaseFilter
from GameInfo import Station, Location, Team, StationStatus

from bot import game_info
from bot import bot


class IsCaretakerFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return message.from_user.id in game_info.caretakers


caretaker_router = Router()
caretaker_router.message.filter(IsCaretakerFilter())


@caretaker_router.message(Command("start"))
async def cmd_start(message: types.Message):
    station = game_info.GetStationByID(message.from_user.id)
    if not station:
        await message.answer(f"Не было найдено станции за которую вы отвественны")
        return

    await message.answer(
        (f"Привет, {message.from_user.full_name}, твоя станция это - {station.GetName()}\n"
            f"Чтобы начать , напиши команду: /go"))


@caretaker_router.message(Command("go"))
async def cmd_work(message: types.Message):
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
        await message.reply("Не удалось найти вашу станцию.")
        return

    team = game_info.GetTeamByStation(station)
    if team is None:
        await message.reply("На вашей станции нет команды.")
        return

    if not station.IsFree():
        await message.reply("Станция уже занята.")
        return

    station.SetStatus(StationStatus.IN_PROGRESS)
    print(f"статус станции {station.GetName()} это {station.WriteStatus()}")

    await message.reply(f"Вы успешно приняли новую команду '{team.GetName()}' на станцию {station.GetName()}.")


@caretaker_router.message(F.text.lower() == "перенаправить текущую команду")
async def redirect_task(message: types.Message):
    station = game_info.GetStationByID(message.from_user.id)
    if not station:
        await message.reply("Не удалось найти вашу станцию.")
        return

    team = game_info.GetTeamByStation(station)
    if not team:
        await message.reply("На вашей станции нет команды для перенаправления.")
        return

    if station.IsInProgress():

        next_station = game_info.GetNextFreeStation(team.GetName())

        if next_station is not None:

            station.SetStatus(StationStatus.FREE)
            game_info.ResetTeamOnStation(station)
            print(f"статус станции {station.GetName()} это {station.WriteStatus()}")

            next_station.SetStatus(StationStatus.WAITING)
            print(f"trying to visit location called {next_station.GetName()[:-2]}")
            
            team.ToVisitLocation(next_station.GetName()[:-2])

            next_station_caretaker_id = game_info.GetIDByStationName(
                next_station.GetName())

            if next_station_caretaker_id:
                await bot.send_message(next_station_caretaker_id, f"К вам идет команда '{team.GetName()}'.")

            await message.answer(f"Команда '{team.GetName()}' перенаправлена на станцию {next_station.GetName()}.")
        else:
            await message.reply("Нет доступных станций для перенаправления.")
    else:
        await message.reply("Станция не в процессе работы. Невозможно перенаправить команду.")
