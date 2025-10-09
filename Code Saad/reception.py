import socket

def receive_data(port):
    host = ''
    """Receive data on a specified host and port using a UDP socket."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    print(f"Listening on {host}:{port}")

    try:
        while True:
            data, addr = sock.recvfrom(1024)  # buffer size is 1024 bytes
            print(f"Reçu de {addr}: {data.decode('ascii').strip()}")
    except KeyboardInterrupt:
        print("Arrêt du serveur.")
    finally:
        sock.close()



receive_data(10110)

