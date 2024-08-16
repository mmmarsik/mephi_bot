from enum import Enum

class StationStatus(Enum):
    FREE, WAITING, IN_PROGRESS = range(3)


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

    def SetStatus(self, status: StationStatus):
        self.status = status

    def GetName(self) -> str:
        return self.name
    
    def WriteStatus(self) -> str:
        if self.status == StationStatus.FREE:
            return "Free"
        elif self.status == StationStatus.IN_PROGRESS:
            return "In progress"
        elif self.status == StationStatus.WAITING:
            return "Waiting"


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
    def __init__(self, name: str, to_visit_list: list[Location]) -> None:
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
            if location.GetName() == location_name:
                location_to_remove = location
        
        self.to_visit_list.remove(location_to_remove)

    def GetToVisitList(self) -> list[Location]:
        return self.to_visit_list

    def GetName(self) -> str:
        return self.name


class GameInfo:
    def __init__(self, caretakers: dict[int, str], admins: set[int], location_list: list[tuple[str, int]]):
        self.caretakers: dict[int, Station] = dict()
        self.admins = admins
        self.locations: set[Location] = set()
        self.teams: set[Team] = set()
        self.team_on_station: dict[Station, Team] = dict()

        for elem in location_list:

            self.locations.add(Location(location_name=elem[0], number_of_stations=elem[1]))

        for caretaker_id, station_name in caretakers.items():
            self.caretakers[caretaker_id] = Station(station_name)

    def AddTeam(self, team_name: str):
        self.teams.add(Team(team_name, self.locations.copy()))

    def SendTeamOnStation(self, team: Team, station: Station):
        self.team_on_station[station] = team
    
    def ResetTeamOnStation(self, station: Station):
        self.team_on_station[station] = None

    def GetTeamByTeamName(self, team_name: str):
        for team in self.teams:
            if team.GetName() == team_name:
                return team
        return None

    def GetNextFreeStation(self, team_name: str) -> Station | None:
        team: Team = str()

        for team_ in self.teams:
            if team_.GetName() == team_name:
                team = team_

        to_visit_list: list[Location] = team.GetToVisitList()

        for location in to_visit_list:
            for station in location.stations:
                if station.IsFree():
                    return station

        print(f"None in GetNextFreeStation")
        return None

    def GetStationByID(self, caretaker_id: int) -> Station | None:
        return self.caretakers.get(caretaker_id, None)
    
    def GetIDByStationName(self, station_name: str) -> int | None:
        for id, station in self.caretakers.items():
            if station_name == station.GetName():
                return id
        return None
    
    def GetTeamByStation(self, station: Station) -> Team:    
        return self.team_on_station.get(station, None)


    
        

