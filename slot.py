from misc import datetime_to_slots_idx, SLOTS_PER_MINUTE
from threading import Lock
from typing import Literal


class Slot:
    """Representation of a time slot used by the AIS simulation.

    Attributes
    ----------
    number : int
        Absolute slot number in the 2*SLOTS_PER_MINUTE space.
    channel : Literal['87B','88B']
        Channel this slot belongs to determined from the number.
    assigned : bool
        Whether the slot was explicitly assigned.
    owner : str | None
        MMSI (or identifier) of the owner that reserved the slot.
    timeout : int | None
        Remaining timeout steps for the reservation (0..7) or None.
    frames_since_last_use : int | None
        Small counter used by cleanup logic to expire unused slots.
    lock : Lock
        Lock protecting concurrent updates to this slot.
    """

    def __init__(self, number: int):
        """Initialize a new Slot.

        Parameters
        ----------
        number : int
            Slot index in the combined two-channel space.
        """
        self.number: int = number
        self.channel: Literal["87B", "88B"] = (
            "87B" if number < SLOTS_PER_MINUTE else "88B"
        )
        self.assigned: bool = False
        self.owner: str = None
        self.timeout: Literal[0, 1, 2, 3, 4, 5, 6, 7] = None
        self.frames_since_last_use: Literal[-1, 0, 1, 2, 3] | None = None
        self.lock = Lock()

    def __str__(self) -> str:
        """Return a compact string representation used for debugging."""
        return f"[{self.number}, {self.owner}, {self.timeout}]"

    def __repr__(self) -> str:
        """Same as :meth:`__str__` - helpful in interactive prints."""
        return self.__str__()

    def is_current(self) -> bool:
        """Return True if this slot corresponds to the current slot index.

        The function compares the slot number against the pair returned by
        :func:`datetime_to_slots_idx`.
        """
        # We hold the lock to avoid races with transient updates to the
        # slot's number/channel fields (though those are immutable in
        # the current design). The function tests membership inside the
        # tuple (slot_87b_idx, slot_88b_idx) returned by the helper.
        with self.lock:
            return self.number in datetime_to_slots_idx()

    def mark_as_used(self) -> None:
        """Mark the slot as recently used (reset the frames counter).

        This does not modify reservation timeout; it only resets the
        frames_since_last_use counter so the background cleanup thread
        knows it was active recently.
        """
        with self.lock:
            self.frames_since_last_use = -1

    def book(self, mmsi: str, timeout: int = None, assigned: bool = False) -> None:
        """Reserve this slot for a given MMSI.

        The reservation is only performed if the slot is currently free
        (owner is None). The method is thread-safe and will set the
        initial frames_since_last_use to -1 to mark recent usage.

        Parameters
        ----------
        mmsi : str
            Owner identifier to book the slot for.
        timeout : int, optional
            Timeout field to attach to the reservation.
        assigned : bool, optional
            Whether the slot should be flagged as assigned.
        """
        with self.lock:
            if self.owner is None:
                self.owner = mmsi
                self.timeout = timeout
                self.assigned = assigned
                self.frames_since_last_use = -1

    def use(self) -> None:
        """Consume one usage cycle of the slot.

        Behavior:
        - mark the slot as used
        - if timeout is None do nothing (unlimited)
        - if timeout == 0 release the slot
        - otherwise decrement the timeout value in a thread-safe way
        """
        self.mark_as_used()
        if self.timeout is None:
            pass
        elif self.timeout == 0:
            self.release()
        elif self.timeout is not None:
            # Decrement the timeout in a thread-safe manner. Note that
            # timeout semantics: None == infinite reservation; numeric
            # values count down until 0 which triggers a release on next
            # use(). We protect the mutation with the slot's lock.
            with self.lock:
                self.timeout -= 1

    def release(self) -> None:
        """Release any reservation on this slot and reset state.

        This operation is thread-safe.
        """
        with self.lock:
            self.owner = None
            self.timeout = None
            self.assigned = False
            self.frames_since_last_use = None
