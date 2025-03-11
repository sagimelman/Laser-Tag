class NetworkEntity:
    def __init__(self, entity_type: str, device_name: str, ip_address: str, port: int, connected: bool):
        self.entity_type = entity_type
        self.device_name = device_name
        self.ip_address = ip_address
        self.port = port
        self.connected = connected

    # Manually enforce abstract methods by raising NotImplementedError with method name
    def accept_connections(self):
        raise NotImplementedError(f"Subclasses must implement the 'accept_connections' method.")

    def handle_client(self, client_socket):
        raise NotImplementedError(f"Subclasses must implement the 'handle_client' method.")

    def send_message(self, client_socket, message):
        raise NotImplementedError(f"Subclasses must implement the 'send_message' method.")

    def broadcast_message(self, message):
        raise NotImplementedError(f"Subclasses must implement the 'broadcast_message' method.")

    def disconnect_client(self, client_socket):
        raise NotImplementedError(f"Subclasses must implement the 'disconnect_client' method.")
