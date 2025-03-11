from NetworkEntity import NetworkEntity
import socket
import threading

class Server(NetworkEntity):
    def __init__(self, device_name: str, ip_address: str, port: int):
        # Pass 'False' for the 'connected' argument
        super().__init__("Server", device_name, ip_address, port, connected=False)
        self.clients = []  # List to store connected player clients
        self.server_socket = None

    def connect(self):
        """Method to connect the server to the network (optional in this case)."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.ip_address, self.port))
        self.server_socket.listen(5)  # Maximum of 5 players in this example
        self.connected = True
        print(f"Server listening on {self.ip_address}:{self.port}...")

    def disconnect(self):
        """Disconnect the server (stop listening and close the socket)."""
        self.connected = False
        if self.server_socket:
            self.server_socket.close()
        print(f"Server {self.device_name} disconnected.")
    
    def accept_connections(self):
        """Start accepting connections from player clients."""
        self.connect()  # Connect to the network (bind the socket and listen)
        
        while True:
            try:
                client_socket, client_address = self.server_socket.accept()
                print(f"New connection from {client_address}")

                # Add the client to the list of connected clients
                self.clients.append(client_socket)

                # Start a new thread to handle this client's communication
                client_thread = threading.Thread(target=self.handle_client, args=(client_socket,))
                client_thread.daemon = True
                client_thread.start()

            except Exception as e:
                print(f"Error accepting connection: {e}")

    def handle_client(self, client_socket):
        """Handle communication with an individual client."""
        client_address = client_socket.getpeername()  # Get client's (IP, port)
        print(f"New client connected: {client_address[0]}:{client_address[1]}")

        try:
            while True:
                message = self.receive_message(client_socket)  # Use the receive function
                if message is None:
                    break  # Client disconnected

                print(f"Received from {client_address[0]}:{client_address[1]} -> {message}")

                # Optionally, send a response back (Example: Echoing the message)
                self.send_message(client_socket, f"Server received: {message}")

        except Exception as e:
            print(f"Error handling client {client_address[0]}:{client_address[1]} - {e}")
        finally:
            self.disconnect_client(client_socket)

    def receive_message(self, client_socket):
        """Receive a message from a client and return it."""
        try:
            message = client_socket.recv(1024).decode("utf-8")
            if not message:
                print(f"Client {client_socket.getpeername()[0]}:{client_socket.getpeername()[1]} disconnected.")
                self.disconnect_client(client_socket)
                return None  # Client disconnected
            return message
        except Exception as e:
            print(f"Error receiving message: {e}")
            return None

    def send_message(self, client_socket, message):
        """Send a message to a specific client."""
        try:
            client_socket.send(message.encode("utf-8"))
            print(f"Sent to {client_socket.getpeername()[0]}:{client_socket.getpeername()[1]} -> {message}")
        except Exception as e:
            print(f"Error sending message to {client_socket.getpeername()[0]}:{client_socket.getpeername()[1]} - {e}")

    def broadcast_message(self, message):
        """Broadcast a message to all connected clients."""
        for client_socket in self.clients:
            try:
                client_socket.send(message.encode("utf-8"))
            except Exception as e:
                print(f"Error sending message to client: {e}")

    def disconnect_client(self, client_socket):
        """Disconnect a client and remove them from the client list."""
        try:
            client_socket.close()
            self.clients.remove(client_socket)
            print(f"Client {client_socket.getpeername()[0]}:{client_socket.getpeername()[1]} disconnected.")
        except Exception as e:
            print(f"Error disconnecting client: {e}")

def main():
    serverSock = Server("Main Server", "192.168.56.1", 52525)
    serverSock.accept_connections()

if __name__ == "__main__":
    main()
