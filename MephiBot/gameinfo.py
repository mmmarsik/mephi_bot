from enum import StrEnum
import json
import logging
import valkey

connection_pool = valkey.ConnectionPool(
    host='localhost',
    port=6379,
    db=0,
    max_connections=10
)



class StationStatus(StrEnum):
    FREE = "Free"
    WAITING = "Waiting"
    IN_PROGRESS = "In progress"


class Station():
    def __init__(self, name: str):
        self.name = name
        self.status = StationStatus.FREE

    def __eq__(self, other):
        if isinstance(other, Station):
            return self.name == other.name
        return False

    def __hash__(self):
        return hash(self.name)

    def IsFree(self) -> bool:
        return self.status == StationStatus.FREE

    def IsInProgress(self) -> bool:
        return self.status == StationStatus.IN_PROGRESS

    def IsWaiting(self) -> bool:
        return self.status == StationStatus.WAITING

    def SetStatus(self, status: StationStatus):
        self.status = status

    def GetName(self) -> str:
        return self.name

    def __str__(self) -> str:
        return f"{self.name} {self.status.name}"


class Location():
    def __init__(self, location_name: str, number_of_stations: int):
        self.name: str = location_name
        self.stations: list[Station] = []

        for i in range(1, number_of_stations + 1):
            station_name: str = self.name + "-" + str(i)
            self.stations.append(Station(station_name))

    def GetName(self) -> str:
        return self.name

    def __str__(self) -> str:
        to_visit_str = ",".join(self.to_visit)
        visited_str = ",".join(self.visited)
        return f"Team({self.name}:[{to_visit_str}]:[{visited_str}])"
 

class Team():
    def __init__(self, name: str, to_visit_list: list[str]) -> None:
        self.name = name
        self.to_visit_list = to_visit_list
        self.visited_list = []

    def __eq__(self, other):
        if isinstance(other, Team):
            return self.name == other.name
        return False

    def __hash__(self):
        return hash(self.name)

    def ToVisitLocation(self, location_name: str):
        if location_name in self.to_visit_list:
            self.to_visit_list.remove(location_name)
            self.visited_list.append(location_name)

    def AddToVisitLocation(self, location_name: str):
        if location_name in self.visited_list:
            self.visited_list.remove(location_name)
            self.to_visit_list.append(location_name)

    def GetToVisitList(self) -> list[str]:
        return self.to_visit_list

    def GetVisitedList(self) -> list[str]:
        return self.visited_list

    def GetName(self) -> str:
        return self.name

    def __str__(self) -> str:
        return f"{self.name} {self.to_visit_list} {self.visited_list}"


class GameInfo:
    def __init__(self, caretakers: dict[int, str], admins: set[int], location_list: list[tuple[str, int]],
                 teams: list[Team], team_on_station, team_leaving_station):
        self.caretakers: dict[int, str] = caretakers
        self.admins = admins
        self.locations: set[Location] = set()
        self.teams: set[Team] = set(teams)
        self.team_on_station: dict[str, str] = dict(team_on_station)
        self.team_leaving_station: dict[str, str] = dict(team_leaving_station)
        self.updates_count = 0
        self.BAD_ID = "INCORRECT_ID"
        self.client = valkey.Valkey(connection_pool=connection_pool)

        for elem in location_list:
            self.locations.add(
                Location(location_name=elem[0], number_of_stations=elem[1]))

        for location in self.locations:
            for station in location.stations:
                self.team_on_station[station.GetName()] = None

        for location in self.locations:
            for station in location.stations:
                self.team_leaving_station[station.GetName()] = None

    def AddTeam(self, team_name: str):
        to_visit_list: list[str] = [location.GetName()
                                    for location in self.locations]
        self.teams.add(Team(team_name, to_visit_list))

    def SendTeamOnStation(self, team_name: str, station_name: str):
        self.team_on_station[station_name] = team_name

    def StartLeavingStation(self, station_name: str):
        team_name: str = self.team_on_station[station_name]
        self.team_leaving_station[station_name] = team_name
        self.team_on_station[station_name] = None

    def LeaveStation(self, station_name: str):
        self.team_leaving_station[station_name] = None

    def GetTeamByName(self, team_name: str) -> Team | None:
        for team in self.teams:
            if team.GetName() == team_name:
                return team
        return None

    def GetStationByName(self, station_name: str) -> Station | None:
        for location in self.locations:
            for station in location.stations:
                if station.GetName() == station_name:
                    return station
        return None

    def GetNextFreeStation(self, team_name: str) -> Station | None:
        for team_ in self.teams:
            if team_.GetName() == team_name:
                team = team_

        to_visit_list: list[str] = team.GetToVisitList()

        for location in self.locations:
            if location.GetName() in to_visit_list:
                for station in location.stations:
                    if station.IsFree():
                        return station

        print(f"None in GetNextFreeStation")
        return None

    def GetStationByCaretakerID(self, caretaker_id: int) -> Station | None:
        print(f"GetStationByCaretakerID was called")
        station_name: str = self.caretakers.get(caretaker_id, None)
        location_name: str = station_name[:-2]
        for location in self.locations:
            if location.GetName() == location_name:
                for station in location.stations:
                    return station
        return None

    def GetCaretakersIDByStationName(self, station_name: str) -> list[int, int] | list[str, str]:
        id_list: list[int] = [self.BAD_ID, self.BAD_ID]
        for id, station in self.caretakers.items():
            if station_name == station:
                if id_list[0] == self.BAD_ID:
                    id_list[0] = id
                elif id_list[1] == self.BAD_ID:
                    id_list[1] = id

        return id_list

    def GetCurrentTeamOnStation(self, station_name: str) -> Team | None:
        team_name = self.team_on_station.get(station_name, None)

        if team_name is None:
            return None

        for team in self.teams:
            if team.GetName() == team_name:
                return team

        return None

    def GetLeavingTeamByStation(self, station_name: str) -> Team | None:
        team_name = self.team_leaving_station.get(station_name, None)

        if team_name is None:
            return None

        for team in self.teams:
            if team.GetName() == team_name:
                return team

        return None

    def HasLeavingTeam(self, station_name: str) -> bool:
        if self.team_leaving_station.get(station_name, None) == None:
            return False
        return True

    def HasTeam(self, station_name: str) -> bool:
        if self.team_on_station.get(station_name, None) == None:
            return False
        return True

    # def Update_game_info(self) -> None:
    #     self.updates_count += 1

    #     if self.updates_count >= 1:
    #         game_info_data = {
    #             "caretakers": self.caretakers,
    #             "admins": list(self.admins),
    #             "locations": [str(location) for location in self.locations],
    #             "teams": [str(team) for team in self.teams],
    #             "team_on_station": self.team_on_station,
    #             "team_leaving_station": self.team_leaving_station
    #         }

    #         self.client.set("game_info", json.dumps(game_info_data))
    #         logging.info("Game info сохранены в Valkey")
    #         self.updates_count = 0
    def Update_game_info(self):
        pass