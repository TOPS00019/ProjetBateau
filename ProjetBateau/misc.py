from dotenv import load_dotenv
from os import getenv


def complete_bits(target_size: int, bits: str) -> str:
    for _ in range(target_size - len(bits)):
        bits = f"0{bits}"
    return bits


def int_to_bin(nbr) -> str: # Accepte le nombre en int ou en str
    return str(bin(int(nbr)))[2:]


def bin_to_int(nbr: str) -> int:
    return int(nbr, 2)


def bin_to_str(binary_code: str) -> str:
    bytes = [""]
    for bit in binary_code:
        if len(bytes[-1]) >= 8:
            bytes.append("")
        bytes[-1] = bytes[-1] + bit
    bytes = [chr(bin_to_int(byte)) for byte in bytes]
    return "".join(bytes)


def str_to_bin(msg: str) -> str:
    out = []
    for char in msg:
        out.append(int_to_bin(ord(char)))
        out[-1] = complete_bits(8, out[-1])
    return "".join(out)


def bin_to_bytes(bin: str) -> bytes:
    ...


def bytes_to_bin(msg: bytes) -> str:
    pass


def encode_message(msg: str) -> bytes:
    return str_to_bin(msg).encode("ascii")


def decode_message(msg: bytes) -> str:
    return bin_to_str(msg.decode("ascii").strip())


def get_ip() -> str:
    load_dotenv()
    return getenv("IP")


def get_server_ip() -> str:
    load_dotenv()
    return getenv("SERVER_IP")


def get_server_broadcast_ip() -> str:
    load_dotenv()
    return getenv("SERVER_BROADCAST_IP")


def get_server_port() -> int:
    load_dotenv()
    return int(getenv("SERVER_PORT"))


def get_server_broadcast_port() -> int:
    load_dotenv()
    return int(getenv("SERVER_BROADCAST_PORT"))
