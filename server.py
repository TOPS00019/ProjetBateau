import socket
import os
import misc
import threading

class Frequency:
    def __init__(self, freq: int) -> None:
        """Represent a UDP broadcast frequency used by the simulated server.

        Parameters
        ----------
        freq : int
            Frequency in Hz used to determine the channel and bind sockets.

        Behavior
        --------
        The constructor sets up a UDP socket configured for broadcast and
        starts a background thread that listens for incoming datagrams.
        """
        self.freq = freq
        self.clients = []
        self.boats = {}
        self.channel = "87B" if self.freq == 161975000 else "88B"
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((misc.get_server_ip(), misc.get_server_port(self.channel)))
        self.listening_thread = threading.Thread(target=self.listen)
        self.listening_thread.start()
        
    def handle_reception(self, msg: str) -> None:
        """Process a received message and re-broadcast it.

        The simple server implementation decodes and prints the received
        message (if decodable by :func:`misc.decode_string`) and then
        re-broadcasts the raw bytes to the broadcast address. Any
        exceptions are intentionally swallowed because the server should
        continue running even if a single message is malformed.

        Parameters
        ----------
        msg : str
            Raw bytes or byte-like message received by the server.
        """
        try:
            print(misc.decode_string(msg))
            self.broadcast(msg)
        except:
            # Intentionally ignore parse/broadcast errors to keep server alive
            pass
    
    def inject_error(self, err_deg: float) -> None:
        """Placeholder to simulate transmission errors.

        Parameters
        ----------
        err_deg : float
            Error degree or probability (semantics to be implemented).

        Note
        ----
        Currently unimplemented; present as an extension point for testing
        how noisy channels affect message integrity.
        """
        pass
        
    def broadcast(self, msg: bytes) -> None:
        """Send raw bytes to the configured broadcast address/port.

        Parameters
        ----------
        msg : bytes
            Raw message bytes to send.
        """
        self.sock.sendto(msg, (misc.get_server_broadcast_ip(), misc.get_server_broadcast_port(self.channel)))
        
    def update_boats_registry(self) -> None:
        """Update the internal boats registry.

        Placeholder for server-side bookkeeping that would track connected
        clients or boats; currently unimplemented.
        """
        pass
            
    def listen(self) -> None:
        """Main listener loop for incoming UDP datagrams.

        This method blocks in a loop calling recvfrom() and forwards each
        received packet to :meth:`handle_reception` for processing.
        """
        print(f"Serveur en écoute sur {misc.get_server_ip()}\n")
        while True:
            msg, addr = self.sock.recvfrom(5096)
            self.handle_reception(msg)
            
            
if __name__=="__main__":
    frq1 = Frequency(160000000)
    frq2 = Frequency(161975000)
    
