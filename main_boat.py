from boat import Boat
from ais import AIS
from random import randint


class MainBoat(Boat):
    def __init__(self,
        mmsi: int = 123456789,
        imo_number: int = 0,
        call_sign: str = "default",
        name: str = "superbateau",
        type_of_ship_and_cargo_type: int = 255,
        position_accuracy: int = 0,
        ais_version: int = 0,
        type_of_epf_device: int = 3,
        A: int = 0,
        B: int = 0,
        C: int = 0,
        D: int = 0,
        destination: str = "default",
        navigational_status: int = 0,
        time_stamp: int = 0,
        eta_month: int = 12,
        eta_day: int = 31,
        eta_hour: int = 23,
        eta_minute: int = 59,
        maximum_present_static_draught: int = 255,
        dte: int = 1,
        spare: int = 0,
        special_maneuvre_indicator: int = 0,
        raim_flag: int = 1,
        latitude: int = 0,
        longitude: int = 0,
        course_over_ground: int = 0,
        speed_over_ground: int = 0,
        rate_of_turn: int = 0,
        true_heading: int = 0) -> None:
        super().__init__(
            mmsi,
            imo_number,
            call_sign,
            name,
            type_of_ship_and_cargo_type,
            position_accuracy,
            ais_version,
            type_of_epf_device,
            A,
            B,
            C,
            D,
            destination,
            navigational_status,
            time_stamp,
            eta_month,
            eta_day,
            eta_hour,
            eta_minute,
            maximum_present_static_draught,
            dte,
            spare,
            special_maneuvre_indicator,
            raim_flag,
            latitude,
            longitude,
            course_over_ground,
            speed_over_ground,
            rate_of_turn,
            true_heading,
        )
        
        self.mmsi = randint(0,1000)
        
        self.ais = AIS(self)
        

if __name__ == "__main__":
    boats = []
    for _ in range(1):
        boats.append(MainBoat())