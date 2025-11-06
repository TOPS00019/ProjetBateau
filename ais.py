from antenna import Antenna
from threading import Thread
from misc import (
    log,
    encode_string,
    decode_string,
    get_timestamp,
    SLOTS_PER_MINUTE,
    SLEEP_TIME,
)
from os import _exit
from time import sleep
from slot import Slot
from message import Message
from slots_map import SlotsMap
from boats_registry import BoatsRegistry
from random import choice, uniform, randint
from typing import Literal


class AIS:
    def __init__(self, boat) -> None:
        """Initialize the AIS subsystem for a Boat instance.

        The AIS object manages two Antenna objects (one per channel), a
        local SlotsMap and a boats registry. It also manages the SOTDMA
        station state machine (initialization, network entry, first
        frame and continuous operation) via a background thread.

        Parameters
        ----------
        boat
            The Boat instance to which this AIS belongs. The Boat is used
            as a source of parameters when building messages.
        """
        log("Début initialisation bateau.")
        self.boat = boat
        self.antenna_87b: Antenna = Antenna(161975000, self)  # 87B
        self.antenna_88b: Antenna = Antenna(162025000, self)  # 88B
        self.slots_map: SlotsMap = SlotsMap(boat)
        self.boats_registry: BoatsRegistry = BoatsRegistry()
        self.msg_handler: Message = Message(boat, self, self.slots_map)

        # Communication and timing state
        self.recv_stations: int = 0
        self.sync_state: int = 0
        self.last_msg5_timestamp: int = None

        # SOTDMA internal state
        self.SOTDMA_NSS: Slot | None = None
        self.SOTDMA_NS: Slot | None = None
        self.SOTDMA_NTS: Slot | None = None
        self.SOTDMA_RI: int = 10
        self.SOTDMA_Rr: float = 60 / self.SOTDMA_RI
        self.SOTDMA_NI: int = int(SLOTS_PER_MINUTE / self.SOTDMA_Rr)
        self.SOTDMA_SI: int = int(0.2 * self.SOTDMA_NI)
        self.SOTDMA_TMO_MIN: Literal[0, 1, 2, 3, 4, 5, 6, 7] = 3
        self.SOTDMA_TMO_MAX: Literal[0, 1, 2, 3, 4, 5, 6, 7] = 7
        self.SOTDMA_t_counter: int = 0

        # Message classification sets used by the SOTDMA station logic
        self.SOTDMA_COM_STATE_MSG_TYPES = [1, 2, 4, 9, 11, 18, 26]
        self.ITDMA_COM_STATE_MSG_TYPES = [3, 9, 18, 26]
        self.NO_COM_STATE_MSG_TYPES = [
            5,
            6,
            7,
            8,
            10,
            12,
            13,
            14,
            15,
            16,
            17,
            19,
            20,
            21,
            22,
            23,
            24,
            25,
            27,
        ]

        # Developer menu thread (daemon) and SOTDMA station thread
        self.dev_menu_thread: Thread = Thread(target=self.dev_menu, daemon=True)
        self.SOTDMA_station_thread: Thread = Thread(
            target=self.SOTDMA_station, daemon=True
        )
        self.dev_menu_thread.start()

        log("Initialisation bateau terminée.")

        self.SOTDMA_station_thread.start()

    def wait_for_slot(self, slot: Slot) -> None:
        """Block until the provided slot becomes the current slot.

        The function sleeps in short intervals to avoid burning CPU while
        waiting for the wall-clock to reach the requested slot index.
        """
        while not slot.is_current():
            sleep(SLEEP_TIME)

    def wait_for_NTS(self) -> None:
        """Block until the currently selected NTS becomes active."""
        self.wait_for_slot(self.SOTDMA_NTS)

    def set_initial_NSS_and_NS(self) -> None:
        """Choose an initial NSS (starting slot) using RATDMA selection.

        A channel is chosen randomly and a starting slot is selected via
        RATDMA_slot_selection. NSS and NS are initialized to that slot.
        """
        start_chn = choice(["87B", "88B"])
        self.SOTDMA_NSS = self.RATDMA_slot_selection(start_chn, 1)
        self.SOTDMA_NS = self.SOTDMA_NSS

    def set_next_NS(self) -> None:
        """Advance the SOTDMA 'NS' to the next computed value.

        This method computes the next NS using :meth:`get_next_NS` and
        stores the resulting :class:`Slot` object in
        ``self.SOTDMA_NS``. It does not return a value; its purpose is
        to update the instance state.
        """
        self.SOTDMA_NS = self.get_next_NS()

    def get_next_NS(self, rank: int = 0) -> Slot:
        """Compute and return the NS (Next Slot) for the given rank.

        The NS (Next Slot) is computed from the current NSS (NSS is the
        initial starting slot chosen during network entry), the internal
        time counter ``SOTDMA_t_counter`` and the configured interval
        ``SOTDMA_NI``. The formula mirrors the SOTDMA specification used
        by this simulation: the NS index is
        ``(NSS.number + (t_counter + rank) * NI) mod SLOTS_PER_MINUTE``.

        Parameters
        ----------
        rank : int, optional
            An optional look-ahead rank (default 0). When ``rank`` is
            greater than zero the function computes the NS value that
            will be in effect ``rank`` steps in the future (useful to
            probe upcoming NS values without changing state).

        Returns
        -------
        Slot
            The :class:`Slot` object corresponding to the computed
            NS index inside ``self.slots_map``. The returned Slot will
            be on the first channel half (87B) unless the computed
            index falls in the second half by wrapping logic used above.

        Raises
        ------
        AttributeError
            If ``SOTDMA_NSS`` or ``slots_map`` are not initialized on
            this AIS instance.
        """
        NS_i = int(
            (self.SOTDMA_NSS.number + (self.SOTDMA_t_counter + rank) * self.SOTDMA_NI)
            % SLOTS_PER_MINUTE
        )
        return self.slots_map.slots[NS_i]

    def set_next_NTS(self) -> Slot:
        """Reserve and return the next NTS (next transmission slot).

        The algorithm scans a window of size SI around the current NS for
        free slots and chooses one at  If no candidate is found it
        waits a short time and retries.
        """
        rsv_chn = None
        start_si = int((self.SOTDMA_NS.number - self.SOTDMA_SI // 2) % SLOTS_PER_MINUTE)

        if self.SOTDMA_NTS is not None:
            rsv_chn = "87B" if self.SOTDMA_NTS.channel == "88B" else "88B"

        available_NTS = self.slots_map.scan_for_free_slots(
            length=self.SOTDMA_SI, ref_si=start_si, chn=rsv_chn
        )

        while available_NTS == []:
            sleep(SLEEP_TIME)
            available_NTS = self.slots_map.scan_for_free_slots(
                length=self.SOTDMA_SI, ref_si=start_si, chn=rsv_chn
            )

        next_NTS = choice(available_NTS)
        next_NTS.book(
            self.boat.mmsi, timeout=randint(self.SOTDMA_TMO_MIN, self.SOTDMA_TMO_MAX)
        )
        return next_NTS

    def get_next_NTS(self, rank: int = 0) -> Slot | None:
        """Return a randomly chosen NTS (Next Transmission Slot) owned by this boat.

        The method computes a search window centered on the NS value for
        the given ``rank`` and then asks the local ``SlotsMap`` for the
        currently-owned slots in that window. From the available owned
        slots, one is randomly chosen and returned.

        Parameters
        ----------
        rank : int, optional
            A look-ahead rank forwarded to :meth:`get_next_NS` to compute
            the reference NS. Default is 0 which returns the NTS
            associated with the immediate next NS.

        Returns
        -------
        Slot
            A :class:`Slot` object that is owned by ``self.boat`` and
            lies inside the SI-length search window around the computed
            NS. The returned slot is chosen at random from the available
            owned candidates.

        Raises
        ------
        IndexError
            If there are no owned slots in the computed search window
            (this mirrors the behaviour of :func:`choice`).
        """
        start_si = int(
            (self.get_next_NS(rank).number - self.SOTDMA_SI // 2) % SLOTS_PER_MINUTE
        )
        avail_ss = self.slots_map.scan_for_owned_slots(
            length=self.SOTDMA_SI, ref_si=start_si
        )
        try:
            return choice(avail_ss)
        except:
            return None

    def send(
        self,
        msg_type: int,
        keep_flag: bool = False,
        offset: int = None,
        slots_nbr: int = 1,
    ) -> None:
        """Transmit a message of the given type using the NTS and its antenna.

        Parameters
        ----------
        msg_type : int
            AIS message type to send (e.g. 1,2,3,5).
        keep_flag : bool, optional
            For ITDMA messages, the keep_flag value to set in the
            communication state.
        offset : int | None, optional
            Offset value for communication-state fields (when used).
        slots_nbr : int, optional
            Number of slots carried by ITDMA transmissions.
        """
        ant = self.antenna_87b if self.SOTDMA_NTS.channel == "87B" else self.antenna_88b
        msg = self.msg_handler.build(msg_type, keep_flag, offset, slots_nbr)
        ant.send(encode_string(msg))
        log(f"Message {msg_type} envoyé avec succès sur le slot {self.SOTDMA_NTS}.")
        sleep(SLEEP_TIME)

    def RATDMA_slot_selection(self, chn: str, lme_rtpri: int) -> Slot:
        """Select a slot using the RATDMA selection algorithm.

        This simplified implementation chooses a candidate randomly from
        available slots in a window (computed as an offset of 150 slots)
        then applies a probabilistic selection loop based on randomly
        sampled thresholds. The function returns a selected Slot object.
        """
        start_s = (
            self.slots_map.current_slots(0)
            if chn == "87B"
            else self.slots_map.current_slots(1)
        )
        lme_rtes = self.slots_map.compute_offset_slot(start_s, 150)

        candidates = self.slots_map.extract_available_slots(
            self.slots_map.compute_slots_range(chn, start_s.number, lme_rtes.number)
        )
        candidate = choice(candidates)

        lme_rtcsc = len(candidates)
        lme_rta = 0

        lme_rtps = 100 / lme_rtes.number
        lme_rtp1 = uniform(0, 100)
        lme_rtp2 = lme_rtps
        lme_rtpi = (100 - lme_rtp2) / lme_rtcsc

        while lme_rtp1 > lme_rtp2:
            lme_rtp2 += lme_rtpi
            lme_rtcsc -= 1
            lme_rta += 1
            lme_rtpi = (100 - lme_rtp2) / lme_rtcsc
            candidates.remove(candidate)
            candidate = choice(candidates)

        return candidate

    def ITDMA(
        self, t_s: Slot, msg_type: int, lme_itinc: int, lme_itsl: int, lme_itkp: bool
    ) -> None:
        """Perform an ITDMA transmission on the provided slot.

        If the message type is one that carries communication-state fields
        the function will call send() with the provided offset/keep_flag
        and number-of-slots. Otherwise it sends a plain message.
        """
        if msg_type in self.ITDMA_COM_STATE_MSG_TYPES:
            self.wait_for_slot(t_s)
            self.send(
                msg_type, offset=lme_itinc, keep_flag=lme_itkp, slots_nbr=lme_itsl
            )
            t_s.use()
        elif msg_type in self.NO_COM_STATE_MSG_TYPES:
            self.wait_for_slot(t_s)
            self.send(msg_type)
            t_s.use()

    def SOTDMA_init(self) -> None:
        """Placeholder for any initialization steps required by SOTDMA."""
        sleep(0)

    def SOTDMA_net_entry(self) -> None:
        """Perform network entry procedure for SOTDMA.

        The method selects initial NSS/NS and reserves the first NTS,
        retrying if the computed offset is larger than the NI window.
        """
        self.set_initial_NSS_and_NS()
        self.SOTDMA_NTS = self.set_next_NTS()
        while self.slots_map.compute_slot_offset(self.SOTDMA_NTS) > self.SOTDMA_NI:
            self.set_initial_NSS_and_NS()
            self.SOTDMA_NTS = self.set_next_NTS()
        log(f"Premier NTS réservé : {self.SOTDMA_NTS}")
        self.wait_for_NTS()

    def SOTDMA_first_frame(self) -> None:
        """Perform the SOTDMA first-frame procedure used to synchronize.

        The method advances NS/T counters and transmits provisional ITDMA
        messages (type 3) until the computed offset becomes zero which
        ends the initial negotiation.
        """
        # The initial frame procedure tries successive provisional ITDMA
        # transmissions (type 3) to negotiate an offset that synchronizes
        # our station on the network. We loop until the computed offset
        # becomes zero which indicates successful negotiation.
        offset = None
        self.SOTDMA_t_counter += 1
        ref_NTS = self.SOTDMA_NTS
        while offset is None or offset != 0:
            self.set_next_NS()
            next_NTS = self.set_next_NTS()
            # Only compute an offset if the candidate NTS is sufficiently
            # far from the reference (outside the SI window), otherwise
            # treat the offset as zero.
            offset = (
                self.slots_map.compute_slot_offset(next_NTS, self.SOTDMA_NTS)
                if self.slots_map.compute_absolute_slot_distance(next_NTS, ref_NTS)
                >= self.SOTDMA_SI
                else 0
            )
            self.ITDMA(self.SOTDMA_NTS, 3, lme_itinc=offset, lme_itkp=True, lme_itsl=1)
            self.SOTDMA_t_counter += 1
            log(f"NTS réservé pour le prochain message 3 : {next_NTS}.")
            if offset != 0:
                # Keep the provisional reservation as our next NTS
                self.SOTDMA_NTS = next_NTS
            else:
                # The negotiation succeeded: free the provisional slot
                next_NTS.release()
                self.SOTDMA_NTS = ref_NTS
                self.SOTDMA_t_counter -= 1
            # print(self.slots_map.get_owned_slots())

    def SOTDMA_continuous(self, msg_type: int) -> None:
        """Handle continuous SOTDMA operation for a single frame.

        Depending on the next NTS offset and the message type the method
        may detect missing NTS slots, perform replacement reservations,
        send messages with appropriate communication-state fields and
        advance internal counters.
        """
        # Continuous operation per-frame handling. Several cases are
        # considered: missing NTS (we need to reserve a replacement),
        # message types that carry no communication-state, and types
        # that require SOTDMA communication-state handling.
        if self.get_next_NTS() is None:
            self.SOTDMA_t_counter += 1
            self.set_next_NS()
            next_NTS = self.set_next_NTS()
            offset = self.slots_map.compute_slot_offset(next_NTS, self.SOTDMA_NTS)
            log(
                f"NTS manquant détecté. Réservation du NTS {next_NTS} pour le remplacer."
            )
            # Wait until our currently selected NTS becomes active and
            # send an ITDMA (type 3) informing of the replacement offset
            # to the network, then adopt the newly reserved NTS.
            self.wait_for_NTS()
            self.ITDMA(self.SOTDMA_NTS, 3, lme_itinc=offset, lme_itkp=True, lme_itsl=1)
            self.SOTDMA_NTS = next_NTS
        elif msg_type in self.NO_COM_STATE_MSG_TYPES:
            self.wait_for_NTS()
            self.send(msg_type)
            self.SOTDMA_NTS.use()
            self.SOTDMA_t_counter += 1
            self.set_next_NS()
            self.SOTDMA_NTS = self.get_next_NTS()
        elif msg_type in self.SOTDMA_COM_STATE_MSG_TYPES:
            self.wait_for_NTS()
            if self.SOTDMA_NTS.timeout == 0:
                start_si = int(
                    (self.SOTDMA_NS.number - self.SOTDMA_SI // 2) % SLOTS_PER_MINUTE
                )
                available_NTS = self.slots_map.scan_for_free_slots(
                    length=self.SOTDMA_SI, ref_si=start_si, chn=self.SOTDMA_NTS.channel
                )
                while available_NTS == []:
                    sleep(SLEEP_TIME)
                    available_NTS = self.slots_map.scan_for_free_slots(
                        length=self.SOTDMA_SI,
                        ref_si=start_si,
                        chn=self.SOTDMA_NTS.channel,
                    )
                new_NTS = choice(available_NTS)
                log(
                    f"NTS {self.SOTDMA_NTS} arrivé à expiration : remplacement par le slot {new_NTS} après le prochain message."
                )
                offset = self.slots_map.compute_slot_offset(new_NTS)
                self.send(msg_type, offset=offset)
                self.SOTDMA_NTS.use()
                self.SOTDMA_t_counter += 1
                self.set_next_NS()
                next_NTS = self.get_next_NTS()
                self.SOTDMA_NTS = next_NTS
                new_NTS.book(
                    self.boat.mmsi,
                    timeout=randint(self.SOTDMA_TMO_MIN, self.SOTDMA_TMO_MAX),
                )
            else:
                self.send(msg_type)
                self.SOTDMA_NTS.use()
                self.SOTDMA_t_counter += 1
                self.set_next_NS()
                self.SOTDMA_NTS = self.get_next_NTS()
        # print(self.slots_map.get_owned_slots())

    def SOTDMA_change_Rr(self, new_RI: int) -> None:  # !!! UNTESTED !!!
        """Planned hook to change the repetition rate (RR) of transmissions.

        Intended behavior : change the SOTDMA
        repetition rate ``RR`` (and any derived timing parameters)
        according to local configuration or network conditions. Typical
        effects of this call in a full implementation would include:

        - Recomputing ``SOTDMA_Rr`` and ``SOTDMA_NI`` from a new RR
            value so that slot scheduling uses the updated repetition
            cadence.
        - Optionally notifying or retransmitting updated communication
            state (ITDMA/SOTDMA fields) so other stations can adapt.
        - Validating that the new RR is within the allowed bounds for
            the current operating mode and adjusting ``SOTDMA_TMO_MIN`` /
            ``SOTDMA_TMO_MAX`` if necessary.

        Notes
        -----
        - The method is intentionally left as a no-op in this simplified
            simulation to avoid changing runtime behavior. It exists as an
            extension point for future enhancements where dynamic RR
            adaptation is required (e.g. congestion control).
        - When implementing this method ensure any changes to timing
            parameters remain thread-safe with respect to the station
            thread and slot reservation logic.
        """
        self.wait_for_NTS()
        log(
            f"Changement d'intervalle d'émission : passage de {self.SOTDMA_RI} à {new_RI} transmissions par minute."
        )
        self.SOTDMA_NSS = self.SOTDMA_NS
        self.SOTDMA_RI = new_RI
        self.SOTDMA_Rr: float = 60 / self.SOTDMA_RI
        self.SOTDMA_NI: int = int(SLOTS_PER_MINUTE / self.SOTDMA_Rr)
        self.SOTDMA_SI: int = int(0.2 * self.SOTDMA_NI)

        offset = None
        self.SOTDMA_t_counter += 1
        ref_NTS = self.SOTDMA_NTS
        while offset is None or offset != 0:
            self.set_next_NS()
            start_si = int(
                (self.get_next_NS().number - self.SOTDMA_SI // 2) % SLOTS_PER_MINUTE
            )
            avail_ss = self.slots_map.scan_for_owned_slots(
                length=self.SOTDMA_SI, ref_si=start_si
            )
            next_NTS: Slot
            if avail_ss:
                next_NTS = choice(avail_ss)
            else:
                next_NTS = self.set_next_NTS()
            offset = (
                self.slots_map.compute_slot_offset(next_NTS, self.SOTDMA_NTS)
                if self.slots_map.compute_absolute_slot_distance(next_NTS, ref_NTS)
                >= self.SOTDMA_SI
                else 0
            )
            self.ITDMA(self.SOTDMA_NTS, 3, lme_itinc=offset, lme_itkp=True, lme_itsl=1)
            self.SOTDMA_t_counter += 1
            log(f"NTS réservé pour le prochain message 3 : {next_NTS}.")
            if offset != 0:
                self.SOTDMA_NTS = next_NTS
            else:
                next_NTS.release()
                self.SOTDMA_NTS = ref_NTS
                self.SOTDMA_t_counter -= 1

    def SOTDMA_station(self) -> None:
        """Main SOTDMA state machine executed in a background thread.

        The station goes through initialization, network entry and first
        frame phases and then enters a continuous loop that alternates
        between sending type 5 messages (periodic static information)
        and type 1 messages as appropriate.
        """
        log(f"Début d'initialisation du SOTDMA...")
        self.SOTDMA_init()
        log(f"Initialisation du SOTDMA terminée.")

        if self.SOTDMA_RI <= 120:
            log(f"Entrée sur le réseau du SOTDMA...")
            self.SOTDMA_net_entry()
            log(f"Entrée sur le réseau du SOTDMA terminée.")
            log(f"Début de la première frame du SOTDMA...")
            self.SOTDMA_first_frame()
            log(f"Fin de la première frame du SOTDMA.")
            log(f"Début de la phase continue du SOTDMA.")
            while True:
                if (
                    self.last_msg5_timestamp is None
                    or get_timestamp() - self.last_msg5_timestamp >= 356
                ):
                    self.last_msg5_timestamp = get_timestamp()
                    self.SOTDMA_continuous(5)
                else:
                    self.SOTDMA_continuous(1)
                sleep(SLEEP_TIME)

    def handle_transmission(self, t: str, chn: str) -> None:
        """Handle an incoming transmission received by an Antenna.

        Decode the ASCII-encoded bitstring received from the network,
        parse it into structured fields and update local state (boats
        registry and slot reservations) according to the message type
        and communication-state fields. The function intentionally
        ignores messages originating from this boat (by comparing
        the parsed MMSI) to avoid processing our own transmissions.

        Notes on behaviour
        - Incoming data is first decoded from the ASCII bitstring
          representation and then parsed by :class:`Message`.
        - Depending on the message type (1,2,3,5) the method will
          update the boats registry and perform slot bookkeeping
          (book/release/use) on the receiving slot.

        Parameters
        ----------
        t : str
            ASCII-encoded bitstring received from the network.
        chn : str
            Channel where the message was received ('87B' or '88B').
        """
        t_ss = self.slots_map.current_slots()
        t_s = t_ss[0] if chn == "87B" else t_ss[1]
        # decode incoming ASCII bitstring into the project's internal
        # six-bit text representation before handing it to the parser
        decoded_t = decode_string(t)
        parsed_data: str

        # The message parser raises Exceptions for unsupported types or
        # corrupted payloads. The original implementation uses string
        # literals in the except clauses; we preserve that behaviour
        # here and simply log the outcome so the listener thread keeps
        # running even on malformed frames.
        try:
            parsed_data = self.msg_handler.parse(decoded_t)
        except "Unkown message type":
            log(f"Message de type inconnu reçu et ignoré.")
        except "Corrupted message":
            log(f"Message corrompu reçu et ignoré.")
        except:
            log(f"Erreur inconnue lors de la réception d'une transmission.")

        # Ignore our own transmissions to avoid self-processing
        if parsed_data["mmsi"] != self.boat.mmsi:
            if parsed_data["message_id"] in [1, 2, 3, 5]:
                if self.boats_registry.has_boat(parsed_data["mmsi"]):
                    self.boats_registry.update_boat(parsed_data["mmsi"], parsed_data)
                else:
                    self.boats_registry.add_boat(parsed_data)

                # Slot bookkeeping policy summary:
                # - If the receiving slot is unowned or already owned by
                #   the sender, update usage counters and reservation
                #   fields according to the message communication state.
                # - Message types 1/2: SOTDMA communication-state may
                #   include timeout/offset or other submessage variants.
                # - Message type 3: ITDMA - has keep_flag and slot
                #   increment fields that cause booking/release behavior.
                if t_s.owner is None or t_s.owner == parsed_data["mmsi"]:
                    # If a timeout is set we consume one unit of it; if
                    # timeout is None we only mark the slot as recently
                    # used (no automatic expiration counting).
                    if t_s.timeout is not None:
                        t_s.use()
                    else:
                        t_s.mark_as_used()

                    # Handle SOTDMA message types (1,2)
                    if parsed_data["message_id"] in [1, 2]:
                        # Booking logic based on slot_timeout semantics
                        if t_s.owner is None and parsed_data["slot_timeout"] > 0:
                            t_s.book(
                                parsed_data["mmsi"], timeout=parsed_data["slot_timeout"]
                            )
                        elif t_s.timeout is None and parsed_data["slot_timeout"] > 0:
                            # If we previously had an infinite reservation
                            # (timeout is None) we set a numeric timeout
                            t_s.timeout = parsed_data["slot_timeout"]
                        elif t_s.timeout is None and parsed_data["slot_timeout"] == 0:
                            # A timeout==0 in the communication state means
                            # the reservation has been released
                            t_s.release()

                        # A slot_timeout==0 may also carry an explicit
                        # offset that requests a reservation on another
                        # minute-scale slot; compute and apply it.
                        if parsed_data["slot_timeout"] == 0:
                            rsv_s = self.slots_map.compute_offset_slot(
                                t_s, parsed_data["slot_offset"]
                            )
                            rsv_s.book(
                                parsed_data["mmsi"], timeout=parsed_data["slot_timeout"]
                            )
                            t_s.release()

                    # Handle ITDMA messages (type 3)
                    elif parsed_data["message_id"] == 3:
                        if not parsed_data["keep_flag"]:
                            # keep_flag false => relinquish the slot
                            t_s.release()
                        elif t_s.owner is None and parsed_data["keep_flag"]:
                            # keep_flag true and slot unowned => book it
                            t_s.book(parsed_data["mmsi"])

                        # If a slot increment is provided, compute the
                        # absolute index and book that slot for the sender
                        if parsed_data["slot_increment"] > 0:
                            rsv_s = int(
                                (parsed_data["slot_increment"] + t_s.number)
                                % SLOTS_PER_MINUTE
                            )

                            if t_s.channel == "87B":
                                rsv_s += SLOTS_PER_MINUTE

                            self.slots_map.slots[rsv_s].book(parsed_data["mmsi"])

                    # Type 5 contains static information that does not
                    # impact local slot reservations in this simplified
                    # simulation. It's parsed and stored elsewhere.
                    elif parsed_data["message_id"] == 5:
                        pass
            log(
                f"Message {parsed_data["message_id"]} reçu du navire {parsed_data["mmsi"]} : {parsed_data}"
            )
            # print(self.slots_map.get_owned_slots())

    def dev_menu(self) -> None:
        """Small developer interactive menu used when running the boat.

        The menu allows sending an ad-hoc message to the server or quitting
        the process. This function runs in a daemon thread started at
        initialization so it won't block normal operation.
        """
        while True:
            choice = int(
                input("\n1 - Envoyer un message au serveur.\n2 - Quitter.\n\n")
            )
            match choice:
                case 1:
                    self.send("87B", str(input("Entrez le message : ")))
                case 2:
                    _exit(1)
