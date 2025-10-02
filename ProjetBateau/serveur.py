import socket
import time

HOST = "0.0.0.0"
PORT = 10110

class Frequency:
    def __init__(self, freq):
        self.freq = freq
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((HOST, PORT))
        
    def handle_reception(msg):
        pass
        
    def send(self, dest_ip, dest_port, msg):
        self.sock.sendto(msg, (dest_ip, dest_port))
    
    def inject_error(self, err_deg):
        pass
    
    def bin_to_str(self, binary_code):
        bytes = [""]
        for bit in binary_code[:]:
            if len(bytes[-1]) >= 8:
                bytes.append("")
            bytes[-1] = bytes[-1] + bit
        bytes = [chr(int(byte, 2)) for byte in bytes]
        return "".join(bytes)
            
    def listen(self):
        print(f"Serveur en écoute sur {HOST}:{PORT}\n")
        while True:
            msg, addr = self.sock.recvfrom(1024)
            print(msg.decode("ascii").strip())
            print(self.bin_to_str(msg.decode("ascii").strip()))
            
            time.sleep((1/self.freq)*1000)
            
if __name__=="__main__":
    frq = Frequency(160000000)
    frq.listen()