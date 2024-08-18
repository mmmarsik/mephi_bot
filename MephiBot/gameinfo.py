from enum import StrEnum


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


class Location():
    def __init__(self, location_name: str, number_of_stations: int):
        self.name: str = location_name
        self.stations: list[Station] = []

        for i in range(1, number_of_stations + 1):
            station_name: str = self.name + "-" + str(i)
            self.stations.append(Station(station_name))

    def GetName(self) -> str:
        return self.name


class Team():
    def __init__(self, name: str, to_visit_list: list[str]) -> None:
        self.name = name
        self.to_visit_list = to_visit_list

    def __eq__(self, other):
        if isinstance(other, Team):
            return self.name == other.name
        return False

    def __hash__(self):
        return hash(self.name)

    def ToVisitLocation(self, location_name: str):

        for location in self.to_visit_list:
            if location == location_name:
                location_to_remove = location

        self.to_visit_list.remove(location_to_remove)

    def GetToVisitList(self) -> list[str]:
        return self.to_visit_list

    def GetName(self) -> str:
        return self.name


class GameInfo:

    def __init__(self, caretakers: dict[int, str], admins: set[int], location_list: list[tuple[str, int]]):
        self.caretakers: dict[int, str] = caretakers
        self.admins = admins
        self.locations: set[Location] = set()
        self.teams: set[Team] = set()
        self.team_on_station: dict[str, str] = dict()
        self.team_leaving_station: dict[str, str] = dict()

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

    def GetCaretakerIDByStationName(self, station_name: str) -> int | None:
        for id, station in self.caretakers.items():
            if station_name == station:
                return id
        return None

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
        if self.team_leaving_station[station_name] == None:
            return False
        return True
    
    