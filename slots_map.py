import random
import slot
import misc
import threading
import time


class SlotsMap:
    def __init__(self, boat) -> None:
        """Container for all time slots and helper operations.

        Parameters
        ----------
        boat
            Reference to the owning boat object; used by some selection
            logic and for possible future callbacks.
        """
        self.slots: list[slot.Slot] = [slot.Slot(i) for i in range(2 * misc.SLOTS_PER_MINUTE)]
        self.boat = boat
        # Background thread that periodically expires old/unreferenced slots
        self.cleanup_thread = threading.Thread(target=self.cleanup, daemon=True)
        self.cleanup_thread.start()
        

    def __str__(self) -> str:
        """Return a short human readable representation.

        The original implementation returned an attribute that does not
        exist; keep a short summary instead.
        """
        # keep representation compact to avoid large prints
        owned = len([s for s in self.slots if s.owner is not None])
        return f"SlotsMap(total={len(self.slots)}, owned={owned})"
    
        
    def __repr__(self) -> str:
        """Return the canonical string representation for debugging.

        This method delegates to :meth:`__str__` and exists to provide
        a concise textual representation of the SlotsMap that's useful
        in debugging, logging and interactive sessions. The string is
        intentionally compact and reports only the total number of
        slots and how many are currently owned.

        Returns
        -------
        str
            A short representation, for example ``"SlotsMap(total=120, owned=3)"``.
        """
        return self.__str__()
    
    
    def reset(self) -> None:
        """Reset the map creating fresh Slot instances for all indices.

        This will drop any existing reservations.
        """
        self.slots: list[slot.Slot] = [slot.Slot(i) for i in range(2 * misc.SLOTS_PER_MINUTE)]
    
    
    def cleanup(self) -> None:
        """Background cleanup loop.

        On each minute tick the function iterates over all slots and updates
        the frames_since_last_use counter. If a slot has never been used
        (frames_since_last_use is None) and it still has an owner, it will
        be released. If frames_since_last_use reaches 3 the slot is also
        released. The loop sleeps briefly to avoid CPU spin.
        """
        last_update_minute = misc.get_current_datetime().minute
        while True:
            if misc.get_current_datetime().minute != last_update_minute:
                last_update_minute = misc.get_current_datetime().minute
                for s in self.slots:
                    match s.frames_since_last_use:
                        case None:
                            if s.owner is not None:
                                s.release()
                        case 3:
                            s.release()
                        case _:
                            s.frames_since_last_use += 1
            time.sleep(0.001)
                    
    
    def current_slots(self, i: int = None) -> list[slot.Slot,slot.Slot] | slot.Slot:
        """Return the current active slot(s) according to the wall clock.

        Parameters
        ----------
        i : int, optional
            If provided, must be 0 or 1 and returns the specific slot for
            that channel. If omitted, a generator yielding both the 87B
            and 88B slot is returned.
        """
        return [self.slots[s_i] for s_i in misc.datetime_to_slots_idx()] if i is None else self.slots[misc.datetime_to_slots_idx()[i]]
        
                       
    def compute_slot_offset(self, s1: slot.Slot, s0: slot.Slot = None) -> int:
        """Compute the offset in slots between s0 and s1.

        If s0 is omitted it defaults to the current slot on the channel
        corresponding to s1. The result is always a non-negative integer
        representing how many slots after s0 the slot s1 occurs (wrapping
        at SLOTS_PER_MINUTE).
        """
        if s0 is None:
            s0 = self.current_slots(0)

        return int((s1.number % misc.SLOTS_PER_MINUTE - s0.number % misc.SLOTS_PER_MINUTE) % misc.SLOTS_PER_MINUTE)
    

    def compute_absolute_slot_distance(self, s0: slot.Slot, s1: slot.Slot = None) -> int:
        """Compute the absolute difference in slot indices between two slots.

        The absolute slot distance is computed using the slot numbers
        modulo ``misc.SLOTS_PER_MINUTE`` so channel boundaries (the two
        halves of the internal slots list) are collapsed to a single
        circular minute-scale index when calculating the numeric
        difference. The result is the non-negative integer difference of
        the two indices on the minute scale.

        Parameters
        ----------
        s0 : slot.Slot
            First slot to compare (may be on either channel).
        s1 : slot.Slot, optional
            Second slot to compare. If omitted, the current 87B slot
            returned by :meth:`current_slots` is used.

        Returns
        -------
        int
            Non-negative integer representing the absolute difference
            between the minute-scale indices of ``s0`` and ``s1``.

        Notes
        -----
        - This is a symmetric distance; it does not take channel
          boundaries into account other than wrapping indices modulo
          ``SLOTS_PER_MINUTE``. It is useful for heuristics that only
          need the numeric proximity of two slots within the minute
          cycle.
        """
        if s1 is None:
            s1 = self.current_slots(0)

        return int(abs(s0.number % misc.SLOTS_PER_MINUTE - s1.number % misc.SLOTS_PER_MINUTE))
           
            
    def compute_offset_slot(self, s: slot.Slot, offset: int) -> slot.Slot:
        """Return the slot found by applying an offset to slot ``s``.

        The returned slot respects channel boundaries: when the source
        slot belongs to 88B the computed index will be shifted into the
        second half of the slots array.
        """
        s_i = int((s.number + offset) % misc.SLOTS_PER_MINUTE)

        if s.channel == "88B":
            s_i += misc.SLOTS_PER_MINUTE

        return self.slots[s_i]
    
    
    def compute_slots_range(self, chn: str, start_si: int, end_si: int) -> list[slot.Slot]:
        """Return a list of Slot objects spanning the index range.

        Parameters
        ----------
        chn : str
            Channel name: '87B' or '88B'.
        start_si : int
            Start index (slot number modulo SLOTS_PER_MINUTE).
        end_si : int
            End index (slot number modulo SLOTS_PER_MINUTE).

        Returns
        -------
        list[slot.Slot]
            Slots in the requested range. The end index is exclusive when
            start_si <= end_si. If the range wraps around the function
            concatenates the two intervals.
        """
        start_si, end_si = int(start_si % misc.SLOTS_PER_MINUTE), int(end_si % misc.SLOTS_PER_MINUTE)
        ssi_range: list[slot.Slot]
        if chn == "88B":
            start_si += misc.SLOTS_PER_MINUTE
            end_si += misc.SLOTS_PER_MINUTE
        ssi_range = list(range(start_si, end_si)) if start_si <= end_si else list(range(start_si, misc.SLOTS_PER_MINUTE)) + list(range(end_si + 1))
        return [self.slots[si] for si in ssi_range]
    
    
    def extract_available_slots(self, ss: list[slot.Slot]) -> list[slot.Slot]:
        """Return the subset of slots from ``ss`` that are currently free."""
        return list(filter(lambda s: s.owner is None, ss))
        
        
    def get_owned_slots(self, mmsis: list[int] = []) -> dict:
        """Return a mapping owner -> list[Slot] for current reservations.

        Parameters
        ----------
        mmsis : list[int], optional
            If provided, only return slots owned by MMSIs present in this
            list. If empty (default) sockets for all owners are returned.
        """
        ss_dict = {}
        for s in self.slots:
            if (s.owner is not None) and (s.owner in mmsis or mmsis == []):
                if s.owner not in ss_dict:
                    ss_dict[s.owner] = []
                ss_dict[s.owner].append(s)

        for b in ss_dict:
            ss_dict[b] = sorted(ss_dict[b], key=lambda s: s.number if s.channel == "87B" else s.number - misc.SLOTS_PER_MINUTE)

        return ss_dict
    
    
    def scan_for_free_slots(self, length: int = 1, ref_si: int = None, s_cnt: int = 1, chn: str = None) -> list[slot.Slot]:
        """Scan and return contiguous free slots meeting constraints.

        Parameters
        ----------
        length : int
            Length in slots to consider around the reference slot.
        ref_si : int, optional
            Reference slot index. If omitted the current slot is used.
        s_cnt : int
            Number of contiguous slots requested.
        chn : str, optional
            Preferred channel.

        Returns
        -------
        list[slot.Slot]
            A sorted list of selected free slots. If no candidate block is
            found an empty list is returned.
        """
        sel_ss = []
        
        if ref_si is None:
            ref_si = self.current_slots(0).number
        else:
            ref_si = int(ref_si % misc.SLOTS_PER_MINUTE)
            
        end_si = int((ref_si + length) % misc.SLOTS_PER_MINUTE)
        
        available_ss = [self.extract_available_slots(self.compute_slots_range("87B", ref_si, end_si)),
                        self.extract_available_slots(self.compute_slots_range("88B", ref_si, end_si))]
        available_chns = [i for i in (0,1) if len(available_ss[i]) >= max(s_cnt,4)]
        if available_chns:
            chosen_chn: int
            if chn is not None and chn == "87B" and 0 in available_chns:
                chosen_chn = 0
            elif chn is not None and chn == "88B" and 1 in available_chns:
                chosen_chn = 1
            else:
                chosen_chn = random.choice(available_chns)
            ref_si = random.randrange(len(available_ss[chosen_chn])-s_cnt-1)
            sel_ss = available_ss[chosen_chn][ref_si:ref_si+s_cnt]
            
        return sorted(sel_ss, key=lambda s: s.number)
    
    
    def scan_for_owned_slots(self, length: int = 1, ref_si: int = None) -> list[slot.Slot]:
        """Return slots owned by this boat inside a search window.

        The function looks up slots in both channels within a window of
        size ``length`` starting at the index ``ref_si`` (wrapping at
        ``SLOTS_PER_MINUTE``). If ``ref_si`` is omitted the current
        87B slot index is used as the reference. The returned list
        contains only slots whose ``owner`` matches ``self.boat.mmsi``.

        Parameters
        ----------
        length : int
            Number of minute-scale slots to include in the window. A
            small value (e.g. 1) narrows the search to a tight region
            around the reference.
        ref_si : int, optional
            Reference slot index (minute-scale). May be any integer;
            it will be reduced modulo ``SLOTS_PER_MINUTE`` before use.
            If omitted the current 87B slot index is used.

        Returns
        -------
        list[slot.Slot]
            A list of :class:`slot.Slot` objects owned by this boat in the
            search window. The list may be empty if no owned slots are
            found.

        Notes
        -----
        - The search covers both channels by concatenating the results
          of the 87B and 88B ranges computed for the same minute-scale
          window. This means the returned slots may belong to either
          channel but will be within the minute-scale indices covered
          by ``ref_si``..``ref_si+length``.
        """
        if ref_si is None:
            ref_si = self.current_slots(0).number
        else:
            ref_si = int(ref_si % misc.SLOTS_PER_MINUTE)
            
        end_si = int((ref_si + length) % misc.SLOTS_PER_MINUTE)
        
        owned_ss = list(filter(lambda s: s.owner is not None and s.owner == self.boat.mmsi, self.compute_slots_range("87B", ref_si, end_si) + self.compute_slots_range("88B", ref_si, end_si)))
        
        return owned_ss
    