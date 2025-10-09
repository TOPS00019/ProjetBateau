from antenna import Antenna
import threading
import misc
import os
import datetime
from bateau import Boat


RAMP_UP_BITS = "11111111"
SYNC_SEQUENCE = "010101010101010101010101"
START_FLAG = "01111110"
END_FLAG = "01111110"
BUFFER = "11111111111111111111111"


class AIS:
    def __init__(self, boat: Boat) -> None:
        self.date = datetime.datetime
        self.antenna1 = Antenna(161975000, self) #87B
        self.antenna2 = Antenna(162025000, self) #88B
        self.occupied_slots = []
        self.boat = boat
        self.dev_menu_thread = threading.Thread(target=self.dev_menu, daemon=True)
        self.dev_menu_thread.start()
    
    def select_slot(self) -> str:
        pass
    
    def update_slots_map(self) -> None:
        pass
    
    def generate_message123(self) -> str:
        payload = misc.complete_bits(misc.int_to_bin(1), 6)
        payload += misc.complete_bits(misc.int_to_bin(3), 2)
        payload += misc.complete_bits(misc.int_to_bin(self.boat.get_boat_data("mmsi")), 30)
        payload += misc.complete_bits(misc.int_to_bin(self.boat.get_boat_data("navigational_status")), 4)
        payload += misc.complete_bits(misc.int_to_bin(self.boat.get_boat_data("rate_of_turn")), 8)
        payload += misc.complete_bits(misc.int_to_bin(self.boat.get_boat_data("speed_over_ground")), 10)
        payload += misc.complete_bits(misc.int_to_bin(self.boat.get_boat_data("position_accuracy")), 1)
        payload += misc.complete_bits(misc.int_to_bin(self.boat.get_boat_data("longitude")), 28)
        payload += misc.complete_bits(misc.int_to_bin(self.boat.get_boat_data("latitude")), 27)
        payload += misc.complete_bits(misc.int_to_bin(self.boat.get_boat_data("course_over_ground")), 12)
        payload += misc.complete_bits(misc.int_to_bin(self.boat.get_boat_data("true_heading")), 9)
        payload += misc.complete_bits(misc.int_to_bin(self.boat.get_boat_data("time_stamp")), 6)
        payload += misc.complete_bits(misc.int_to_bin(self.boat.get_boat_data("special_maneuvre_indicator")), 2)
        payload += misc.complete_bits(misc.int_to_bin(self.boat.get_boat_data("raim_flag")), 1)
        payload += misc.complete_bits("1111111111111111111", 19)
        crc = ""
        return RAMP_UP_BITS + SYNC_SEQUENCE + START_FLAG + payload + crc + END_FLAG + BUFFER
    
    def generate_message5(self) -> str:
        pass
    
    def decode_message123(self) -> str:
        pass
    
    def decode_message5(self) -> str:
        pass
    
    def compute_crc16(self, data: str) -> str:
        pass
    
    def check_crc16(self) -> str:
        pass
    
    def handle_transmission(self, trans: str, channel: str) -> None:
        transmission_date = self.date.now()
        print(f"[Transmission reçue sur le canal {channel} le {transmission_date.strftime("%d/%m/%Y à %H:%M:%S.%f")} (slot {self.time_to_slot_number(channel, transmission_date)})]\n\"{misc.decode_message(trans)}\"\n")

    def time_to_slot_number(self, channel: str, date) -> int:
        microseconds = int(date.strftime("%f")) / 1000 + int(date.strftime("%S")) * 1000
        slot = int(microseconds//((60/2250) * 1000) + 1)
        if channel == "88B":
            slot += 2250
        return slot
    
    def send(self, channel: str, msg: str) -> None:
        if channel == "87B":
            self.antenna1.send(misc.encode_message(msg))
        elif channel == "88B":
            self.antenna2.send(misc.encode_message(msg))
    
    def dev_menu(self) -> None:
        while True:
            choice = int(input("\n1 - Envoyer un message au serveur.\n2 - Quitter.\n\n"))
            match choice:
                case 1:
                    self.send("87B", str(input("Entrez le message : ")))
                case 2:
                    os._exit(1)
