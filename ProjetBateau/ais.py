from antenna import Antenna
import threading
import misc
import os
import datetime
import time


RAMP_UP_BITS = "11111111"
SYNC_SEQUENCE = "010101010101010101010101"
START_FLAG = "01111110"
END_FLAG = "01111110"
BUFFER = "11111111111111111111111"


class AIS:
    def __init__(self, boat) -> None:
        self.date = datetime.datetime
        self.antenna1 = Antenna(161975000, self) #87B
        self.antenna2 = Antenna(162025000, self) #88B
        self.occupied_slots = []
        self.boat = boat
        self.dev_menu_thread = threading.Thread(target=self.dev_menu, daemon=True)
        self.handle_message123_thread = threading.Thread(target=self.handle_message123, daemon=True)
        self.dev_menu_thread.start()
        self.handle_message123_thread.start()
        print(self.decode_message123(self.generate_message123()))
    
    def select_slot(self) -> str:
        pass
    
    def update_slots_map(self) -> None:
        pass
    
    def generate_message123(self) -> str:
        payload = misc.int_to_bin(1, size=6)
        payload += misc.int_to_bin(3, size=2)
        payload += misc.int_to_bin(self.boat.get_boat_data("mmsi"), size=30)
        payload += misc.int_to_bin(self.boat.get_boat_data("navigational_status"), size=4)
        payload += misc.int_to_bin(self.boat.get_boat_data("rate_of_turn"), size=8)
        payload += misc.int_to_bin(self.boat.get_boat_data("speed_over_ground"), size=10)
        payload += misc.int_to_bin(self.boat.get_boat_data("position_accuracy"), size=1)
        payload += misc.int_to_bin(self.boat.get_boat_data("longitude"), size=28)
        payload += misc.int_to_bin(self.boat.get_boat_data("latitude"), size=27)
        payload += misc.int_to_bin(self.boat.get_boat_data("course_over_ground"), size=12)
        payload += misc.int_to_bin(self.boat.get_boat_data("true_heading"), size=9)
        payload += misc.int_to_bin(self.boat.get_boat_data("time_stamp"), size=6)
        payload += misc.int_to_bin(self.boat.get_boat_data("special_maneuvre_indicator"), size=2)
        payload += misc.int_to_bin(self.boat.get_boat_data("spare"), size=3)
        payload += misc.int_to_bin(self.boat.get_boat_data("raim_flag"), size=1)
        payload += misc.complete_bits("1111111111111111111", 19)
        crc = self.compute_crc16(payload)
        return RAMP_UP_BITS + SYNC_SEQUENCE + START_FLAG + payload + crc + END_FLAG + BUFFER
    
    def generate_message5(self) -> str:
        pass
    
    def decode_message123(self, msg: str) -> str:
        payload = msg[40:208]
        crc = msg[208:224]
        if self.check_crc16(crc, payload):
            return {
                "message_id": misc.bin_to_int(payload[:6]),
                "repeat_indicator": misc.bin_to_int(payload[6:8]),
                "user_id": misc.bin_to_int(payload[8:38]),
                "navigational_status": misc.bin_to_int(payload[38:42]),
                "rate_of_turn": misc.bin_to_int(payload[42:50]),
                "speed_over_ground": misc.bin_to_int(payload[50:60]),
                "position_accuracy": misc.bin_to_int(payload[60:61]),
                "longitude": misc.bin_to_int(payload[61:89]),
                "latitude": misc.bin_to_int(payload[89:116]),
                "course_over_ground": misc.bin_to_int(payload[116:128]),
                "true_heading": misc.bin_to_int(payload[128:137]),
                "time_stamp": misc.bin_to_int(payload[137:143]),
                "special_maneuvre_indicator": misc.bin_to_int(payload[143:145]),
                "spare": misc.bin_to_int(payload[145:148]),
                "raim_flag": misc.bin_to_int(payload[148:149]),
                "communication_state": misc.bin_to_int(payload[149:168])
            }
        return "Erreur"
    
    def decode_message5(self) -> str:
        pass
    
    def compute_crc16(self, data: str) -> str:
        poly = 0x8005
        init_crc = 0x0000
        bits = [int(b) for b in data]
        crc = init_crc
        for bit in bits:
            msb = (crc >> 15) & 1
            crc = ((crc << 1) & 0xFFFF) | bit
            if msb:
                crc ^= poly
        return format(crc, "016b")
    
    def check_crc16(self, crc: str, data: str) -> bool:
        return self.compute_crc16(data) == crc
    
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
            
    def handle_message123(self):
        while True:
            self.send("87B", self.generate_message123())
            time.sleep(5)
    
    def dev_menu(self) -> None:
        while True:
            choice = int(input("\n1 - Envoyer un message au serveur.\n2 - Quitter.\n\n"))
            match choice:
                case 1:
                    self.send("87B", str(input("Entrez le message : ")))
                case 2:
                    os._exit(1)
