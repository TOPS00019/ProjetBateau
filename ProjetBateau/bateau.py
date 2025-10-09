from ais import AIS


class Boat:
    def __init__(self) -> None:
        self.data = {
            "mmsi": "226123456", # MIDXXXXXX
            "navigational_status": "15", # 0-15
            "course_over_ground": "3599", #0-3599
            "speed_over_ground": "1022", # En 1/10 kt, 0-1022
            "rate_of_turn": "126", # -126 - +126
            "latitude": "108000000", # 1/10000 mn
            "longitude": "108000000", # 1/10000 mn
            "true_heading": "359", # 0-359, 511 pour non disponible
            "time_stamp": "59", # 0-59
            "position_accuracy": "0", # 0 ou 1
            "ais_version": "",
            "imo_number": "1073741823",
            "call_sign": "@@@@@@@",
            "name": "superbateau",
            "type_of_ship_and_cargo_type": "255",
            "A": "0",
            "B": "0",
            "C": "0",
            "D": "0",
            "type_of_epf_device": "1",
            "eta": {
                    "month": "12",
                    "day": "31",
                    "hour": "23",
                    "minute": "59"
                },
            "maximum_present_static_draught": "255", # 1/10 m
            "destination": "@@@@@@@@@@@@@@@@@@@@",
            "dte": "1",
            "spare": "0",
            "special_maneuvre_indicator": "0",
            "raim_flag": "1"
        }

        self.ais = AIS(self)
        
    def get_boat_data(self, name: str) -> str:
        return self.data[name]


if __name__ == "__main__":
    boat = Boat()
