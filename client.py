from NetworkEntity import NetworkEntity

# Abstract Client class
class Client(NetworkEntity):
    def __init__(self, device_name: str, ip_address: str, port: int, connected: bool):
        super().__init__("Client", device_name, ip_address, port, connected)
        self.socket = None
        self.type = None  # Will be overridden by subclasses
        self.connected = connected  # Track the connection status

    def connect(self):
        """Subclasses must implement this connect method."""
        raise Exception("connect() must be implemented in a subclass.")

    def send_data(self, data):
        """Subclasses must implement this send_data method."""
        raise Exception("send_data() must be implemented in a subclass.")

    def receive_data(self):
        """Subclasses must implement this receive_data method."""
        raise Exception("receive_data() must be implemented in a subclass.")

    def disconnect(self):
        if self.socket:
            self.socket.close()
            self.connected = False
            print(f"{self.device_name} disconnected.")
