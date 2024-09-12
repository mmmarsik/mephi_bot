from aiogram import types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from bot import game_info

def get_yes_no_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Да"), KeyboardButton(text="Нет")]
        ],
        resize_keyboard=True
    )
    return keyboard


def get_admin_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Зарегистрировать команду")],
            [KeyboardButton(text="Получить инфо о команде"),
             KeyboardButton(text="Статус станций")],
            [KeyboardButton(text="Показать команды на станции"), KeyboardButton(text="Изменить статус станции")], [
                KeyboardButton(text="Редактировать список локаций для опр. команды"), KeyboardButton(text="Сбросить команды на всех станциях")],
            [KeyboardButton(text="Редактировать станцию у команды"), KeyboardButton(text="Найти команды без станций")],
            [KeyboardButton(text="Сбросить команды на конкретной станции")]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_team_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    for team in game_info.teams:
        builder.add(KeyboardButton(text=team.GetName()))
    builder.adjust(4)
    return builder.as_markup(resize_keyboard=True)


def get_edit_action_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="Добавить станцию"))
    builder.add(KeyboardButton(text="Удалить станцию"))
    builder.add(KeyboardButton(text="Отмена"))
    return builder.as_markup(resize_keyboard=True)


def get_location_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    for location in game_info.locations:
        builder.add(KeyboardButton(text=location.GetName()))
    builder.adjust(4)
    return builder.as_markup(resize_keyboard=True)

def get_station_selection_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    for location in game_info.locations:
        for station in location.stations:
            builder.add(types.KeyboardButton(text=station.GetName()))
    builder.adjust(4)
    return builder.as_markup(resize_keyboard=True)


def get_status_selection_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🟢 Свободна"))
    builder.add(KeyboardButton(text="🟡 Ожидание"))
    builder.add(KeyboardButton(text="🔴 В процессе"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)

def get_stations_by_location_keyboard(location_name: str) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()

    for location in game_info.locations:
        if location.GetName() == location_name:
            for station in location.stations:
                builder.add(types.KeyboardButton(text=station.GetName()))
    
    builder.adjust(3)
    return builder.as_markup(resize_keyboard=True)
