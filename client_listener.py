import socket
import time

server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
server.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
server.settimeout(0.2)  # Prevents the socket from blocking indefinitely
server.bind(("", 44444))  # Listen for responses on port 44444

message = b"Server Broadcast - Who is the Configurator?"
found_configurator = False  # Flag to stop broadcasting

while not found_configurator:
    # Broadcast the message
    server.sendto(message, ("<broadcast>", 37020))
    print("Broadcast message sent!")

    try:
        # Try receiving a response from the Configurator
        data, addr = server.recvfrom(1024)
        if data == b"I am the Configurator":
            found_configurator = True
            print(f"Configurator identified at {addr[0]}")
    except socket.timeout:
        pass  # No response yet, continue broadcasting
print("Stopped broadcasting. Configurator found!")