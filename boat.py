from time import time, sleep
import numpy as np
from threading import Thread
from misc import degs_to_rads, SLEEP_TIME


BOAT_INFO_KEYS = [
    "mmsi",
    "imo_number",
    "call_sign",
    "name",
    "type_of_ship_and_cargo_type",
    "position_accuracy",
    "ais_version",
    "type_of_epf_device",
    "A",
    "B",
    "C",
    "D",
    "destination",
    "navigational_status",
    "time_stamp",
    "eta_month",
    "eta_day",
    "eta_hour",
    "eta_minute",
    "maximum_present_static_draught",
    "dte",
    "spare",
    "special_maneuvre_indicator",
    "raim_flag",
    "latitude",
    "longitude",
    "course_over_ground",
    "speed_over_ground",
    "rate_of_turn",
    "true_heading",
]


MODIFIABLE_BOAT_INFO_KEYS = [
    "mmsi",
    "imo_number",
    "call_sign",
    "name",
    "type_of_ship_and_cargo_type",
    "position_accuracy",
    "ais_version",
    "type_of_epf_device",
    "A",
    "B",
    "C",
    "D",
    "destination",
    "navigational_status",
    "time_stamp",
    "eta_month",
    "eta_day",
    "eta_hour",
    "eta_minute",
    "maximum_present_static_draught",
    "dte",
    "spare",
    "special_maneuvre_indicator",
    "raim_flag",
    "latitude",
    "longitude",
    "course_over_ground",
    "speed_over_ground",
    "rate_of_turn",
    "true_heading",
]


class Boat:
    def __init__(
        self,
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
        true_heading: int = 0
    ) -> None:
        self.mmsi = mmsi  # MIDXXXXXX
        self.imo_number = imo_number
        self.call_sign = call_sign
        self.name = name

        self.type_of_ship_and_cargo_type = type_of_ship_and_cargo_type
        self.position_accuracy = position_accuracy  # 0 ou 1
        self.ais_version = ais_version
        self.type_of_epf_device = type_of_epf_device
        self.A = A
        self.B = B
        self.C = C
        self.D = D

        self.destination = destination
        self.navigational_status = navigational_status  # 0-15
        self.time_stamp = time_stamp  # 0-59
        self.eta_month = eta_month
        self.eta_day = eta_day
        self.eta_hour = eta_hour
        self.eta_minute = eta_minute
        self.maximum_present_static_draught = maximum_present_static_draught
        self.dte = dte
        self.spare = spare
        self.special_maneuvre_indicator = special_maneuvre_indicator
        self.raim_flag = raim_flag

        self.latitude = latitude  # +-1/10000 mn
        self.longitude = longitude  # +-1/10000 mn
        self.course_over_ground = course_over_ground  # 0-3599
        self.speed_over_ground = speed_over_ground  # En 1/10 kt, 0-1022
        self.rate_of_turn = rate_of_turn  # -126 - +126, = round(4.733 * sqrt(rot capteur))
        self.true_heading = true_heading  # 0-359, 511 pour non disponible
        
        self.boat_position_updater_thread = Thread(target=self.update_boat_position, daemon=True)
        self.boat_position_updater_thread.start()
        
    
    def __str__(self) -> str:
        return f"Mmsi: {self.mmsi}\n\tImo number: {self.imo_number}\n\tCall sign: {self.call_sign}\n\tName: {self.name}\n\tType of ship and cargo type: {self.type_of_ship_and_cargo_type}\n\tPosition accuracy: {self.position_accuracy}\n\tAis version: {self.ais_version}\n\tType of epf device: {self.type_of_epf_device}\n\tA: {self.A}\n\tB: {self.B}\n\tC: {self.C}\n\tD: {self.D}\n\tDestination: {self.destination}\n\tNavigational status: {self.navigational_status}\n\tTime stamp: {self.time_stamp}\n\tEta month: {self.eta_month}\n\tEta day: {self.eta_day}\n\tEta hour: {self.eta_hour}\n\tEta minute: {self.eta_minute}\n\tMaximum present static draught: {self.maximum_present_static_draught}\n\tDte: {self.dte}\n\tSpare: {self.spare}\n\tSpecial maneuvre indicator: {self.special_maneuvre_indicator}\n\tRaim flag: {self.raim_flag}\n\tLatitude: {self.latitude}\n\tLongitude: {self.longitude}\n\tCourse over ground: {self.course_over_ground}\n\tSpeed over ground: {self.speed_over_ground}\n\tRate of turn: {self.rate_of_turn}\n\tTrue heading: {self.true_heading}\n"
    

    def __repr__(self) -> str:
        return self.__str__()
    
    
    def deg_to_ais_rot(self, rot_sensor: float) -> int:
        return round(4.733*rot_sensor**0.5)
    
    
    def ais_to_deg_rot(self, rot_ais: int) -> int:
        return round((rot_ais/4.733)**2)
     
        
    def update_boat_position(self) -> None:
        last_update_time = time()
        while True:
            update_time = time()
            elapsed_time = last_update_time - update_time
            last_update_time = update_time
            
            vertical_speed = np.sin(degs_to_rads(self.course_over_ground)) * self.speed_over_ground * (10/36) # En 10000 èmes d'arc par seconde
            horizontal_speed = np.cos(degs_to_rads(self.course_over_ground)) * (10/36) # En 10000 èmes d'arc par seconde
            deg_rot = self.ais_to_deg_rot(self.rate_of_turn)
            
            new_course_over_ground = (self.course_over_ground + deg_rot)%360
            new_true_heading = new_course_over_ground
            new_latitude = round((self.latitude + elapsed_time * vertical_speed)%54000000)
            new_longitude = round((self.longitude + elapsed_time * horizontal_speed)%108000000)
            
            self.course_over_ground = new_course_over_ground
            self.true_heading = new_true_heading
            self.latitude = new_latitude
            self.longitude = new_longitude
            sleep(SLEEP_TIME)
            
    
    def set_parameter(self, param: str, value) -> None:
        setattr(self, param, value)
        
        
    def get_parameter(self, param: str):
        return getattr(self, param)
