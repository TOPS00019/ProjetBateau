import socket
import time


def send_data(port, data):
    host = '255.255.255.255'
    """Send data to a specified host and port using a TCP socket."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    message_bytes = data.encode('ascii')
    try:
        sock.sendto(message_bytes, (host, port))
        print(f"Envoyé: {data.strip()}")
    except Exception as e:
        print(f"Erreur d'envoi: {e}")
    finally:
        sock.close()



send_data(10110,"Hello World\n")
