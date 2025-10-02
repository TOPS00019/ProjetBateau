import socket
import time

HOST = ""
PORT = 0

class Antenna:
    def __init__(self, freq, serv_ip, serv_port):
        self.freq = freq
        self.serv_ip = serv_ip
        self.serv_port = serv_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.connect((self.serv_ip, self.serv_port))
        
    def listen(self):
        print(f"Antenne en écoute sur {HOST}:{PORT}\n")
        while True:
            msg, addr = self.sock.recvfrom(1024)
            print(msg)
            time.sleep((1/self.freq)*1000)
            
    def str_to_bin(self, msg):
        out = []
        for char in msg:
            out.append(str(bin(ord(char)))[2:])
            for _ in range(8 - len(out[-1])):
                out[-1] = f"0{out[-1]}"
        return "".join(out)
    
    
    def send(self, msg):
        self.sock.send(self.str_to_bin(msg).encode("ascii"))
        
        
if __name__=="__main__":
    ant = Antenna(160000000, "192.168.43.255", 10110)
    ant.send(str(input("\nEntrez texte\n")))
    ant.sock.close()