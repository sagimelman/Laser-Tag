from abc import ABC, abstractmethod
from NetworkEntity import NetworkEntity
# Abstract Client class
class Client(NetworkEntity, ABC):
    def __init__(self, device_name: str, ip_address: str, port: int, connected: bool):
        super().__init__("Client", device_name, ip_address, port, connected)
        self.socket = None
        self.type = None  # Will be overridden by subclasses
        self.connected = connected  # Track the connection status

    def connect(self):
        raise NotImplementedError("Subclasses must implement this connect method.")

    def send_data(self, data):
        raise NotImplementedError("Subclasses must implement this send_data method.")

    def receive_data(self):
        raise NotImplementedError("Subclasses must implement this receive_data method.")

    def disconnect(self):
        if self.socket:
            self.socket.close()
            self.connected = False
            print(f"{self.device_name} disconnected.")
