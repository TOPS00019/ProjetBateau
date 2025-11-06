import crc16
import misc


MSG123_CONTENT = [
    ("mmsi", "int", 30),
    ("navigational_status", "int", 4),
    ("rate_of_turn", "int", 8),
    ("speed_over_ground", "int", 10),
    ("position_accuracy", "int", 1),
    ("longitude", "int", 28),
    ("latitude", "int", 27),
    ("course_over_ground", "int", 12),
    ("true_heading", "int", 9),
    ("time_stamp", "int", 6),
    ("special_maneuvre_indicator", "int", 2),
    ("spare", "int", 3),
    ("raim_flag", "int", 1)
]

MSG5_CONTENT = [
    ("mmsi", "int", 30),
    ("ais_version", "int", 2),
    ("imo_number", "int", 30),
    ("call_sign", "str", 42),
    ("name", "str", 120),
    ("type_of_ship_and_cargo_type", "int", 8),
    ("A", "int", 9),
    ("B", "int", 9),
    ("C", "int", 6),
    ("D", "int", 6),
    ("type_of_epf_device", "int", 4),
    ("eta_minute", "int", 6),
    ("eta_hour", "int", 5),
    ("eta_day", "int", 5),
    ("eta_month", "int", 4),
    ("maximum_present_static_draught", "int", 8),
    ("destination", "str", 120),
    ("dte", "int", 1),
    ("spare", "int", 1)
]


class Message:
    def __init__(self, boat, ais, slots_map):
        """Build and parse AIS-like messages used by the simulation.

        Parameters
        ----------
        boat
            Boat instance providing static/dynamic fields for message
            construction via its get_parameter() method.
        ais
            AIS subsystem instance used to access communication state
            and reservation information.
        slots_map
            SlotsMap instance used for slot computations when building
            communication state fields.
        """
        self.ramp_up_bits: str = "11111111"
        self.sync_sequence: str = "010101010101010101010101"
        self.start_flag: str = "01111110"
        self.end_flag: str = "01111110"
        self.buffer: str = "11111111111111111111111"
        self.crc_handler: crc16.CRC16 = crc16.CRC16()
        self.boat = boat
        self.ais = ais
        self.slots_map = slots_map
        
        
    def type(self, msg: str) -> int:
        """Return the message type identifier parsed from the raw bitstring.

        The function expects a full message bitstring where the 6-bit
        message type field is located at bits 40..45 (inclusive).

        Parameters
        ----------
        msg : str
            Bitstring representing the full message.

        Returns
        -------
        int
            Numeric message type.
        """
        return int(msg[40:46], 2)
    
    
    def build_sub_message(self, offset: int) -> str:
        """Build the 14-bit SOTDMA sub-message according to timeout.

        The SOTDMA communication state contains a 14-bit sub-message whose
        interpretation depends on the current timeout value. This helper
        implements that selection logic and returns the appropriate 14-bit
        string.

        Parameters
        ----------
        offset : int
            Offset value used when timeout==0.
        """
        match self.ais.SOTDMA_NTS.timeout:
            case 3 | 5 | 7:
                return misc.int_to_bits(self.ais.recv_stations, 14)
            case 2 | 4 | 6:
                return misc.int_to_bits(self.ais.SOTDMA_NTS.number, 14)
            case 1:
                now_dt = misc.get_current_datetime()
                return misc.pad_left(misc.int_to_bits(now_dt.hour, 5) + misc.int_to_bits(now_dt.minute, 6), 14)
            case 0:
                return misc.int_to_bits(offset, 14)
            
            
    def build_communication_state(self, type: int, keep_flag: bool, offset: int, slots_nbr: int):
        """Return the communication state bits appended to payloads for
        SOTDMA/ITDMA messages.

        The returned string starts with a two-bit sync state. For message
        types 1 and 2 the function appends the 3-bit timeout and the
        14-bit sub-message built by :meth:`build_sub_message`. For type 3
        (ITDMA) a different layout is used (offset/slots/keep_flag).
        """
        com_state = misc.int_to_bits(self.ais.sync_state, bits_size=2)

        if type in [1, 2]:
            com_state += misc.int_to_bits(self.ais.SOTDMA_NTS.timeout, bits_size=3) + self.build_sub_message(offset)
        elif type == 3:
            com_state += misc.int_to_bits(offset, bits_size=13) + misc.int_to_bits(slots_nbr, bits_size=3) + misc.int_to_bits(1 if keep_flag else 0, 1)

        return com_state
    
    
    def build_payload(self, type: int, keep_flag: bool, offset: int, slots_nbr: int) -> str:
        """Build the message payload bitstring for the provided message type.

        The method serializes the message fields using the MSG123_CONTENT or
        MSG5_CONTENT layout depending on the message type, and appends the
        communication-state bits for types 1,2,3.
        """
        payload = misc.int_to_bits(type, bits_size=6) + misc.int_to_bits(3, bits_size=2)
        content = MSG123_CONTENT if type in [1, 2, 3] else MSG5_CONTENT

        for elt in content:
            payload += misc.int_to_bits(self.boat.get_parameter(elt[0]), bits_size=elt[2]) if elt[1] == "int" else misc.str_to_bits(self.boat.get_parameter(elt[0]), bits_size=elt[2])

        if type in [1, 2, 3]:
            payload += self.build_communication_state(type, keep_flag, offset, slots_nbr)

        return payload
            
    
    def build(self, type: int, keep_flag: bool, offset: int, slots_nbr: int) -> str:
        """Build a full frame (ramp/sync/flags/payload/crc/buffer).

        Returns the full bitstring ready for ASCII encoding and transmission.
        """
        payload = self.build_payload(type, keep_flag, offset, slots_nbr)
        return self.ramp_up_bits + self.sync_sequence + self.start_flag + payload + self.crc_handler.compute_crc(payload) + self.end_flag + self.buffer
    
    
    def parse(self, msg: str) -> dict:
        """Parse a received message bitstring into a dictionary of fields.

        The function extracts the payload and CRC depending on the
        identified message type (1,2,3 or 5). If the CRC check passes the
        payload is parsed according to the corresponding template and a
        dictionary of decoded fields is returned. On CRC failure or an
        unsupported message type an Exception is raised and the event is
        logged.

        Parameters
        ----------
        msg : str
            Complete received bitstring (including ramp/sync/flags).

        Returns
        -------
        dict
            Parsed message fields (including 'mmsi' and message-specific
            communication state fields).
        """
        type = self.type(msg)
        content: dict
        payload: str
        crc: str
        sub_message: str

        match type:
            case 1 | 2 | 3:
                content = MSG123_CONTENT
                # For types 1/2/3 the payload occupies bits 40..207
                # (inclusive) so we slice msg[40:208]. CRC follows
                # directly after the payload (208..223). The submessage
                # used by SOTDMA/ITDMA decoding lives inside the payload
                # at payload[154:168]. These offsets are specific to the
                # simplified frame layout used by this project.
                payload = msg[40:208]
                crc = msg[208:224]
                sub_message = payload[154:168]
            case 5:
                content = MSG5_CONTENT
                # Type 5 uses a longer payload range (40..463) and a CRC
                # immediately after (464..479).
                payload = msg[40:464]
                crc = msg[464:480]
            case _:
                raise Exception("Invalid message type")
        if self.crc_handler.verify_crc(payload, crc):
            parsed_data = {
                "message_id": misc.bits_to_int(payload[:6]),
                "repeat_indicator": misc.bits_to_int(payload[6:8])
            }
            start_i = 8

            for elt in content:
                parsed_data[elt[0]] = misc.bits_to_int(payload[start_i:start_i + elt[2]]) if elt[1] == "int" else misc.bits_to_str(payload[start_i:start_i + elt[2]])
                start_i += elt[2]

            if type == 5:
                # no additional communication-state fields for type 5 in this
                # project's simplified model
                pass
            elif type in [1, 2]:
                # communication-state fields for 1/2 are located near the
                # end of the standard payload area; the indices below map
                # to the 2-bit sync state and 3-bit slot_timeout.
                parsed_data["sync_state"] = misc.bits_to_int(payload[149:151])
                parsed_data["slot_timeout"] = misc.bits_to_int(payload[151:154])

                match parsed_data["slot_timeout"]:
                    case 0:
                        # offset-based submessage (14 bits)
                        parsed_data["slot_offset"] = misc.bits_to_int(sub_message)
                    case 1:
                        # UTC hour/minute encoded inside the 14-bit submessage
                        parsed_data["utc_hour"] = misc.bits_to_int(sub_message[:8])
                        parsed_data["utc_minute"] = misc.bits_to_int(sub_message[8:])
                    case 2 | 4 | 6:
                        # submessage holds an explicit slot number
                        parsed_data["slot_number"] = misc.bits_to_int(sub_message)
                    case 3 | 5 | 7:
                        # submessage holds a count of received stations
                        parsed_data["received_stations"] = misc.bits_to_int(sub_message)
            elif type == 3:
                # ITDMA-specific communication-state layout: the slot
                # increment is 13 bits followed by a 3-bit slots count and
                # the 1-bit keep_flag.
                parsed_data["sync_state"] = misc.bits_to_int(payload[149:151])
                parsed_data["slot_increment"] = misc.bits_to_int(payload[151:164])
                parsed_data["number_of_slots"] = misc.bits_to_int(payload[164:167])
                parsed_data["keep_flag"] = misc.bits_to_int(payload[167:168])
            else:
                raise Exception("Unkown message type")
            return parsed_data
        else:
            raise Exception("Corrupted message")
        