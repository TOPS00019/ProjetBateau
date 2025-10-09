import socket
import os
import misc
import threading

class Frequency:
    def __init__(self, freq: int) -> None:
        self.freq = freq
        self.clients = []
        self.boats = {}
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((misc.get_server_ip(), int(os.getenv("SERVER_PORT"))))
        self.listening_thread = threading.Thread(target=self.listen)
        self.dev_menu_thread = threading.Thread(target=self.dev_menu, daemon=True)
        self.listening_thread.start()
        self.dev_menu_thread.start()
        
    def handle_reception(self, msg: str) -> None:
        try:
            print(misc.decode_message(msg))
        except:
            pass
    
    def inject_error(self, err_deg: float) -> None:
        pass
        
    def broadcast(self, msg: bytes) -> None:
        self.sock.sendto(msg, (misc.get_server_broadcast_ip(), misc.get_server_broadcast_port()))
        
    def update_boats_list(self) -> None:
        pass
            
    def listen(self) -> None:
        print(f"Serveur en écoute sur {misc.get_server_ip()}:{misc.get_server_port()}\n")
        while True:
            msg, addr = self.sock.recvfrom(2048)
            self.handle_reception(msg)
            
    def dev_menu(self) -> None:
        while True:
            choice = int(input("\n1 - Broadcast.\n2 - Quitter.\n\n"))
            match choice:
                case 1:
                    self.broadcast(misc.encode_message(str(input("Entrez le message broadcast : "))))
                case 2:
                    os._exit(1)
            
            
if __name__=="__main__":
    frq = Frequency(160000000)
