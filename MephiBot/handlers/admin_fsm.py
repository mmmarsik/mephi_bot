from aiogram.filters.state import State, StatesGroup

class FSMStatesRegister(StatesGroup):
    choose_name = State()
    accept_info = State()


class FSMStationStatusChange(StatesGroup):
    choose_station = State()
    choose_status = State()

class FSMEditStation(StatesGroup):
    choosing_team = State()
    editing_stations = State()
    adding_station = State()
    removing_station = State()

class FSMShowStationTeams(StatesGroup):
    choose_station = State()
