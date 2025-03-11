import socket
import time

# Create the server socket
server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
server.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
server.settimeout(0.2)  # Set timeout to avoid blocking forever
server.bind(("", 12321))  # Bind the socket to port 44444

message = b"Server IP message"  # The message we will broadcast

while True:
    # Broadcast the message to all IPs on the LAN
    server.sendto(message, ("<broadcast>", 37020))
    print("Broadcasting message...")
    time.sleep(1)  # Send the message every second
