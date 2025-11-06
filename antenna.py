import socket
import threading
import misc
from typing import Literal


class Antenna:
    def __init__(self, freq: int, ais) -> None:
        """UDP 'antenna' abstraction used by a Boat's AIS instance.

        The Antenna creates a UDP socket bound to the local (boat) broadcast
        port and connected to the server listening port so it can both send
        and receive messages. A background listener thread is started to
        dispatch incoming packets to the parent AIS instance.

        Parameters
        ----------
        freq : int
            Radio frequency used to determine the logical channel (87B/88B).
        ais
            AIS instance that will receive incoming transmissions via
            its handle_transmission() method.
        """
        self.freq: int = freq
        self.ais = ais
        self.channel: Literal["87B", "88B"] = "87B" if freq == 161975000 else "88B"
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # bind to the local broadcast port used by boats for this channel
        # Bind the socket to the boat's local IP and the broadcast port
        # for this channel so we can receive broadcasts. We also connect
        # the UDP socket to the server's reception address which is a
        # convenient way to set the default send target (it does not
        # create a TCP connection; UDP 'connect' simply records the
        # peer address for send()).
        self.sock.bind((misc.get_ip(), misc.get_server_broadcast_port(self.channel)))
        self.sock.connect((misc.get_server_ip(), misc.get_server_port(self.channel)))
        self.listener_thread = threading.Thread(target=self.listen)
        self.listener_thread.start()

    def listen(self) -> None:
        """Listener loop that receives UDP datagrams and forwards them.

        Received packets are handed to the parent AIS via
        :meth:`AIS.handle_transmission`. Any exceptions are swallowed to
        keep the listening thread alive.
        """
        misc.log(f"Antenne en écoute sur le canal {self.channel}.")
        while True:
            try:
                msg, addr = self.sock.recvfrom(5096)
                self.ais.handle_transmission(msg, self.channel)
            except:
                # keep listening despite individual errors
                pass

    def send(self, msg: str) -> None:
        """Send raw bytes via the antenna's UDP socket.

        Parameters
        ----------
        msg : str
            Raw bytes or ASCII bitstring that will be sent to the
            connected server address.
        """
        self.sock.send(msg)
