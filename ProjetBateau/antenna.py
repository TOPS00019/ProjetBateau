import socket
import threading
import misc


class Antenna:
    def __init__(self, freq: int, ais) -> None:
        self.freq = freq
        self.ais = ais
        self.channel = "87B" if freq == 161975000 else "88B"
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((misc.get_ip(), misc.get_server_broadcast_port()))
        self.sock.connect((misc.get_server_ip(), misc.get_server_port()))
        self.listening_thread = threading.Thread(target=self.listen)
        self.listening_thread.start()

    def listen(self) -> None:
        print(f"Antenne en écoute sur le canal {self.channel}\n")
        while True:
            msg, addr = self.sock.recvfrom(1024)
            self.ais.handle_transmission(msg, self.channel)
            # time.sleep((1/self.freq)*1000)

    def send(self, msg: str) -> None:
        self.sock.send(msg)
