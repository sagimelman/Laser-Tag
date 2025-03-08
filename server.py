from NetworkEntity import NetworkEntity
import socket
import threading

class Server(NetworkEntity):
    def __init__(self, device_name: str, ip_address: str, port: int, connected: bool):
        super().__init__("Server", device_name, ip_address, port, connected)
        self.clients = []  # List to store connected player clients
        self.server_socket = None

    def accept_connections(self):
        """Start accepting connections from player clients."""
        # Create the server socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.ip_address, self.port))
        self.server_socket.listen(5)  # Maximum of 5 players in this example

        print(f"Server listening on {self.ip_address}:{self.port}...")

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
        try:
            while True:
                message = client_socket.recv(1024)  # Receive a message from the client
                if not message:
                    break  # Client disconnected

                # Process the received message here (for example, relay it to the configurator client)
                print(f"Received message: {message.decode('utf-8')}")

                # TODO: Relay the message to the configurator client or broadcast to other players

        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            # Clean up the client connection when done
            self.disconnect_client(client_socket)

    def send_message(self, client_socket, message):
        """Send a message to a specific client."""
        try:
            client_socket.send(message.encode("utf-8"))
        except Exception as e:
            print(f"Error sending message to client: {e}")

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
            print("Client disconnected.")
        except Exception as e:
            print(f"Error disconnecting client: {e}")

