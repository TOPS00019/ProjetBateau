from dotenv import load_dotenv
from os import getenv
import datetime
import slots_map
import numpy as np
import datetime


"""Utility helpers used throughout the project.

This module provides small helpers for environment configuration, bit-encoding
and simple time/slot utilities used by the AIS simulation.

Notes
-----
Most functions are small, pure helpers and include type hints. The bit
encoding/decoding utilities implement a 6-bit character alphabet used by
the AIS-like messages in this project.
"""


SIX_BIT_ALPHABET = [char for char in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+/"]

SLOTS_PER_MINUTE = 2250
SLOTS_DURATION = 60 / SLOTS_PER_MINUTE


def get_ip() -> str:
    """Return the local IP for the boat from the environment.

    Loads environment variables from a .env file (via load_dotenv()) and
    returns the value of the "IP" variable.

    Returns
    -------
    str
        The configured IP address string or None if the variable is absent.

    Example
    -------
    >>> # with .env containing IP=127.0.0.1
    >>> get_ip()
    '127.0.0.1'
    """
    load_dotenv()
    return getenv("IP")


def get_server_ip() -> str:
    """Return the server IP address configured in the environment.

    See :func:`get_ip` for behavior of environment loading.
    """
    load_dotenv()
    return getenv("SERVER_IP")


def get_server_ip_netmask() -> str:
    """Return the server netmask (dotted decimal) from environment.

    This is used with :func:`get_server_ip` to compute the broadcast address.
    """
    load_dotenv()
    return getenv("SERVER_IP_NETMASK")


def get_server_broadcast_ip() -> str:
    """Compute and return the server broadcast IP.

    The function reads the server IP and its netmask from the environment
    and performs a bitwise computation to derive the broadcast address
    (IPv4 dotted-decimal string).

    Returns
    -------
    str
        Dotted-decimal IPv4 broadcast address (e.g. '192.168.1.255').
    """
    ip_int = sum(int(o) << 8 * (3 - i) for i, o in enumerate(get_server_ip().split(".")))
    mask_int = sum(int(o) << 8 * (3 - i) for i, o in enumerate(get_server_ip_netmask().split(".")))
    return ".".join(str((ip_int | ~mask_int & 0xFFFFFFFF) >> 8 * (3 - i) & 255) for i in range(4))


def get_server_port(chn: str) -> int:
    """Return the server listening port for a given channel.

    Parameters
    ----------
    chn : str
        Channel name expected to be '87B' or '88B'.

    Returns
    -------
    int
        The configured reception port for the server on the requested
        channel (from environment variables).
    """
    load_dotenv()
    return int(getenv("87B_CHANNEL_RECEPTION_PORT")) if chn == "87B" else int(getenv("88B_CHANNEL_RECEPTION_PORT"))


def get_server_broadcast_port(chn: str) -> int:
    """Return the server broadcast port for a given channel.

    Parameters
    ----------
    chn : str
        Channel name expected to be '87B' or '88B'.
    """
    load_dotenv()
    return int(getenv("87B_CHANNEL_BROADCAST_PORT")) if chn == "87B" else int(getenv("88B_CHANNEL_BROADCAST_PORT"))


def index6(char: str) -> int:
    """Return the index (0..63) of a 6-bit alphabet character.

    The project uses a 6-bit alphabet similar to AIS six-bit encoding. This
    helper returns the ordinal index for a character in that alphabet.

    Raises
    ------
    ValueError
        If the character is not part of the SIX_BIT_ALPHABET.
    """
    return SIX_BIT_ALPHABET.index(char)


def char6(ord: int) -> str:
    """Return the character corresponding to a 6-bit ordinal.

    Parameters
    ----------
    ord : int
        The ordinal in range 0..63.
    """
    return SIX_BIT_ALPHABET[ord]


def pad_left(bits: str, target_size: int) -> str:
    """Pad a bit string on the left with '0' to reach the target size.

    Parameters
    ----------
    bits : str
        The bit string to pad (e.g. '101').
    target_size : int
        Desired length of the returned string.
    """
    return bits.rjust(target_size, "0")


def int_to_bits(nbr, bits_size: int | str = None) -> str:
    """Convert an integer to its binary representation as a string.

    If bits_size is provided, the output is zero-padded to that width.

    Parameters
    ----------
    nbr
        The integer (or value convertible to int).
    bits_size : int | str, optional
        If provided, the width used for zero-padding.

    Returns
    -------
    str
        Binary representation (e.g. '1011' or '001011' when padded).
    """
    if bits_size is None:
        return format(int(nbr), "b")
    else:
        return format(int(nbr), f"0{bits_size}b")


def bits_to_int(nbr: str) -> int:
    """Parse a binary string and return its integer value.

    Parameters
    ----------
    nbr : str
        A string consisting of '0' and '1'.
    """
    return int(nbr, 2)


def bits_to_str(bits: str) -> str:
    """Convert a stream of bits (6-bit groups) into a 6-bit alphabet string.

    Leading groups equal to '000000' are dropped (consistent with the
    message encoding used in this project). The function groups bits in
    blocks of six, converts each to an ordinal, then maps to the alphabet.

    Parameters
    ----------
    bits : str
        A string of bits ('0'/'1').

    Returns
    -------
    str
        Decoded text using the SIX_BIT_ALPHABET.
    """
    # Drop leading null 6-bit groups which are used as padding in this
    # project's encoding scheme. Then collect bits into 6-bit groups
    # and translate them to characters using the SIX_BIT_ALPHABET.
    groups = [""]
    while bits[0:6] == "000000":
        bits = bits[6:]
    for bit in bits:
        if len(groups[-1]) >= 6:
            groups.append("")
        groups[-1] = groups[-1] + bit
    groups = [char6(bits_to_int(group)) for group in groups]
    return "".join(groups)


def str_to_bits(string: str, bits_size: int = None) -> str:
    """Encode a string (from SIX_BIT_ALPHABET) into a binary string.

    Each character is encoded as a six-bit value. If bits_size is provided
    the final concatenated bitstring is padded on the left to the
    requested length.
    """
    bits = []
    for char in string:
        bits.append(int_to_bits(index6(char), bits_size=6))
    if bits_size is None:
        return "".join(bits)
    return pad_left("".join(bits), bits_size)


def encode_string(string: str) -> bytes:
    """Return the ASCII-encoded bitstring for a given text string.

    This helper is a small convenience: it converts a SIX_BIT_ALPHABET
    string to its bit representation then returns it as ASCII bytes.
    """
    return str_to_bits(string).encode("ascii")


def decode_string(msg: bytes) -> str:
    """Decode a bytes object containing an ASCII bitstring to text.

    The input is expected to be an ASCII-encoded string composed of '0'
    and '1' characters which represent 6-bit groups. Trailing whitespace
    is trimmed before decoding.
    """
    return bits_to_str(msg.decode("ascii").strip())


def log(msg: str) -> None:
    """Append a timestamped message to 'logs.log' and print it.

    The log entry contains the current datetime plus the 'slot index'
    computed by :func:`datetime_to_slots_idx`.

    Parameters
    ----------
    msg : str
        Message text to persist to the log file.
    """
    curr_dt = get_current_datetime()
    with open("logs.log", "a", encoding="utf-8") as log_file:
        curr_s_idx = datetime_to_slots_idx(curr_dt)
        log_str = f"[{curr_dt.strftime("%d/%m/%Y à %H:%M:%S.%f")} | slots {curr_s_idx}]\n\t{msg}\n\n"
        log_file.write(log_str)
        print(log_str)
    


def degs_to_rads(degs: float) -> float:
    """Convert degrees to radians.

    Parameters
    ----------
    degs : float
        Angle in degrees.
    """
    return degs * (np.pi / 180)


def rads_to_degs(rads: float) -> float:
    """Convert radians to degrees.

    Parameters
    ----------
    rads : float
        Angle in radians.
    """
    return rads / (np.pi / 180)


def get_current_datetime() -> datetime.datetime:
    """Return the current datetime (datetime.datetime.now()).

    This wrapper exists to ease testing and to provide a single place to
    change time retrieval behavior if necessary.
    """
    return datetime.datetime.now()


def get_timestamp(dt: datetime.datetime = None) -> float:
    """Return a POSIX timestamp for a datetime object or for now.

    Parameters
    ----------
    dt : datetime.datetime, optional
        If provided, the timestamp of this datetime is returned. Otherwise
        the current time is used.
    """
    return get_current_datetime().timestamp() if dt is None else dt.timestamp()


def datetime_to_slots_idx(dt: datetime.datetime = None) -> tuple[int, int]:
    """Map a datetime to slot indices used by the simulator.

    The function computes the current slot index (0..SLOTS_PER_MINUTE-1)
    based on the seconds and milliseconds of the provided datetime. It
    returns a tuple (current_slot_index, current_slot_index +
    SLOTS_PER_MINUTE) allowing callers to retrieve the two parallel
    channel slots (87B/88B) used by the simulation.

    Parameters
    ----------
    dt : datetime.datetime, optional
        If omitted, the current datetime is used.

    Returns
    -------
    tuple[int,int]
        (slot_index_on_87B, slot_index_on_88B)
    """
    # Compute the minute-scale slot index by converting the current
    # time into milliseconds inside the current minute and dividing by
    # the per-slot duration expressed in milliseconds. The function
    # returns both channel indices: the 87B index and the 88B index
    # which is the 87B value offset by one full SLOTS_PER_MINUTE.
    eff_dt = get_current_datetime() if dt is None else dt
    # milliseconds elapsed in the current minute
    ms_in_minute = eff_dt.microsecond / 1000 + eff_dt.second * 1000
    s_i = int(ms_in_minute // ((60 / SLOTS_PER_MINUTE) * 1000))
    return (s_i, s_i + SLOTS_PER_MINUTE)
