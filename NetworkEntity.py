from abc import ABC, abstractmethod

class NetworkEntity(ABC):
    def __init__(self, device_type : str, device_name : str, ip_address : str, port: int, connected : bool):
        self.device_type = device_type
        self.device_name = device_name
        self.ip_address = ip_address
        self.port = port
        self.connected = False

    @abstractmethod
    def connect(self):
        raise NotImplementedError("Subclasses must implement this method")

    @abstractmethod
    def disconnect(self): # disconnect from the network
        self.connected = False
        print(f"{self.device_name} disconnected.")
    
    @abstractmethod
    def send_message(self, message : str): # send a message to the network
        raise NotImplementedError("Subclasses must implement this method")
    
    @abstractmethod
    def receive_message(self):
        """Receive a message (to be implemented by subclasses)."""
        raise NotImplementedError("Subclasses must implement this method")
    

    def __str__(self): # print the network entity
        return f"[ {self.device_name} / {self.device_type}] IP: {self.ip_address}, Port: {self.port}, Connected: {self.connected}"