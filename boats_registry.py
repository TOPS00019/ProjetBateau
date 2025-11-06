from boat import Boat, BOAT_INFO_KEYS, MODIFIABLE_BOAT_INFO_KEYS


class BoatsRegistry:
    def __init__(self) -> None:
        """Simple registry of Boat objects indexed by MMSI.

        The BoatsList stores instantiated Boat objects and provides
        convenience methods to add, remove and update entries. The
        stored Boat instances are expected to implement set_parameter()
        and other domain methods.
        """
        self.boats: dict = {}
        
    
    def __str__(self) -> str:
        """Return a multiline string describing all registered boats."""
        return "\n".join(str(b) for b in self.boats.values())
    
    
    def __repr__(self) -> str:
        """Same as :meth:`__str__` for interactive display."""
        return self.__str__()
        
        
    def has_boat(self, mmsi: int) -> bool:
        """Return True if a boat with the given MMSI is registered.

        Parameters
        ----------
        mmsi : int
            Numeric MMSI identifier.
        """
        return mmsi in self.boats
        
        
    def add_boat(self, boat_info: dict) -> None:
        """Create and register a new Boat from a parameter dictionary.

        Only keys listed in ``BOAT_INFO_KEYS`` are applied to the
        new Boat instance. The boat_info dictionary must contain an
        "mmsi" key used as the registry key.
        """
        new_boat = Boat()
        for param in boat_info:
            if param in BOAT_INFO_KEYS:
                new_boat.set_parameter(param, boat_info[param])
        self.boats[boat_info["mmsi"]] = new_boat
    
    
    def remove_boat(self, mmsi: int) -> None:
        """Remove a boat by MMSI from the registry.

        Raises KeyError if the MMSI is not present.
        """
        del self.boats[mmsi]
    
    
    def update_boat(self, mmsi: int, new_boat_info: dict) -> None:
        """Update mutable fields of an existing registered boat.

        Only parameter keys listed in ``MODIFIABLE_BOAT_INFO_KEYS``
        will be applied; other keys are ignored.
        """
        for param in new_boat_info:
            if param in MODIFIABLE_BOAT_INFO_KEYS:
                self.boats[mmsi].set_parameter(param, new_boat_info[param])
