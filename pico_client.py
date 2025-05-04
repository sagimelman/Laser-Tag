from NetworkEntity import NetworkEntity
import network
import socket
import time
import json
import machine
from machine import Pin
from button import Button

class PicoClient(NetworkEntity):
    def __init__(self, player_name, ssid, password, server_ip, server_port=9999):
        # Initialize with NetworkEntity parameters
        super().__init__(
            entity_type="client",
            device_name=player_name,
            ip_address=server_ip,
            port=server_port,
            connected=False
        )
        
        self.player_name = player_name
        self.ssid = ssid
        self.password = password
        
        # Player state
        self.player_id = None
        
        # Network state
        self.wlan = None
        self.sock = None
        
        # Set up hardware - we'll just use one button for simplicity
        self.button_pin = 17  # Pin for the button
        self.status_led_pin = 15  # Pin for status LED
        
        # Initialize hardware components
        self.setup_hardware()
    
    def setup_hardware(self):
        """Initialize hardware components"""
        # Setup button with internal pulldown
        self.button = Button(
            self.button_pin, 
            rest_state=False, 
            internal_pulldown=True
        )
        
        # Setup status LED
        self.status_led = Pin(self.status_led_pin, Pin.OUT)
    
    def connect_wifi(self):
        """Connect to WiFi network"""
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        
        print(f"Connecting to {self.ssid}...")
        self.wlan.connect(self.ssid, self.password)
        
        # Wait for connection with timeout
        max_wait = 10
        while max_wait > 0:
            if self.wlan.status() < 0 or self.wlan.status() >= 3:
                break
            max_wait -= 1
            print("Waiting for connection...")
            time.sleep(1)
        
        if self.wlan.status() != 3:
            print("Network connection failed")
            return False
        
        status = self.wlan.ifconfig()
        print(f"Connected to WiFi. IP: {status[0]}")
        return True
    
    def connect_to_server(self):
        """Connect to the game server"""
        try:
            addr = socket.getaddrinfo(self.ip_address, self.port)[0][-1]
            self.sock = socket.socket()
            # Socket is set to blocking mode by default
            self.sock.connect(addr)
            print("Connected to server")
            
            # Set connected flag first
            self.connected = True
            
            # Then register with server
            registration_success = self.send_message("register", {"player_name": self.player_name})
            
            if not registration_success:
                print("Failed to register with server")
                self.connected = False
                return False
                
            print("Registration message sent to server")
            return True
        except Exception as e:
            print(f"Server connection failed: {e}")
            self.connected = False
            return False
    
    def send_message(self, msg_type, data=None):
        """Send a message to the server"""
        if not self.connected or not self.sock:
            print("Not connected - can't send message")
            return False
        
        if data is None:
            data = {}
        
        # Create base message
        message = {"type": msg_type}
        
        # Add player info if available
        if self.player_id is not None:
            message["player_id"] = self.player_id
        
        if self.player_name:
            message["player_name"] = self.player_name
        
        # Add any additional data
        message.update(data)
        
        try:
            # Convert to JSON and add newline
            json_message = json.dumps(message).encode('utf-8') + b'\n'
            print(f"Sending message: {message}")
            
            # Send the data with blocking socket
            bytes_sent = self.sock.send(json_message)
            
            # Check if all bytes were sent
            if bytes_sent != len(json_message):
                print(f"Warning: Only sent {bytes_sent} of {len(json_message)} bytes")
                
            return True
        except Exception as e:
            print(f"Send error: {e}")
            self.connected = False
            return False
    
    def receive_message(self):
        """Try to receive a message from the server"""
        if not self.connected or not self.sock:
            return None
        
        try:
            # Use non-blocking receive with a manual timeout approach
            self.sock.setblocking(False)
            try:
                data = self.sock.recv(1024)
                
                if data:
                    try:
                        # Print raw data for debugging
                        print(f"Received raw data: {data}")
                        
                        # Try to parse JSON message(s)
                        messages = []
                        for line in data.decode('utf-8').strip().split('\n'):
                            if line:
                                messages.append(json.loads(line))
                        
                        if messages:
                            # Reset to blocking mode
                            self.sock.setblocking(True)
                            return messages[0]  # Return first message for now
                    except json.JSONDecodeError as e:
                        print(f"JSON decode error: {e}")
            except OSError as e:
                # This is the expected exception when no data is available
                # Don't print anything for this case
                pass
            
            # Reset to blocking mode
            self.sock.setblocking(True)
        except Exception as e:
            print(f"Receive error: {e}")
            # Don't change connection status here, let the main loop handle reconnections
        
        return None
    
    def on_message_received(self, message):
        """Process a message from the server"""
        if not message:
            return
        
        print(f"Processing message: {message}")
        
        msg_type = message.get("type")
        
        if msg_type == "welcome":
            self.player_id = message.get("player_id")
            print(f"Registered with server as Player {self.player_id}")
            self.flash_led(3, 0.2)  # Flash LED 3 times
    
    def check_button(self):
        """Check if button is pressed and send message if so"""
        # Update button state
        self.button.update()
        
        # Check if button is active (pressed)
        if self.button.read():
            print("Button pressed! Sending to server...")
            self.flash_led(1, 0.1)  # Quick flash to indicate button press
            
            # Send button press message to server
            self.send_message("button_press", {
                "button_pin": self.button_pin,
                "player_name": self.player_name
            })
            
            # Small delay to prevent multiple triggers
            time.sleep(0.2)
    
    def flash_led(self, count, duration):
        """Flash the status LED"""
        for _ in range(count):
            self.status_led.value(1)
            time.sleep(duration)
            self.status_led.value(0)
            time.sleep(duration)
    
    # Override NetworkEntity abstract methods
    def accept_connections(self):
        """Not used in client"""
        pass
        
    def handle_client(self, client_socket):
        """Not used in client"""
        pass
        
    def broadcast_message(self, message):
        """Not used in client"""
        pass
        
    def disconnect_client(self, client_socket):
        """Not used in client"""
        pass
    
    def run(self):
        """Main loop for the client"""
        # Connect to WiFi
        if not self.connect_wifi():
            # Blink LED to show wifi connection error
            while True:
                self.flash_led(1, 0.5)
                time.sleep(0.5)
        
        # Connect to server
        if not self.connect_to_server():
            # Blink LED differently to show server connection error
            while True:
                self.flash_led(2, 0.2)
                time.sleep(1)
        
        # Main loop
        last_heartbeat = time.time()
        last_reconnect_attempt = 0
        reconnect_interval = 5  # seconds between reconnection attempts
        
        try:
            while True:
                # First check if we're still connected
                if not self.connected:
                    current_time = time.time()
                    if current_time - last_reconnect_attempt >= reconnect_interval:
                        print("Attempting to reconnect to server...")
                        if self.connect_to_server():
                            print("Reconnected to server!")
                            self.flash_led(3, 0.2)
                        last_reconnect_attempt = current_time
                    # Skip the rest of the loop if we're not connected
                    time.sleep(0.1)
                    continue
                
                # Check for messages from server
                message = self.receive_message()
                if message:
                    self.on_message_received(message)
                
                # Check button
                self.check_button()
                
                # Send heartbeat every 5 seconds
                current_time = time.time()
                if current_time - last_heartbeat >= 5:
                    print("Sending heartbeat...")
                    if not self.send_message("heartbeat", {}):
                        print("Failed to send heartbeat - connection may be lost")
                        self.connected = False
                    last_heartbeat = current_time
                
                # Small delay to prevent 100% CPU usage
                time.sleep(0.01)
        except Exception as e:
            print(f"Fatal error: {e}")
            # Show error pattern on LED
            while True:
                self.flash_led(3, 0.1)
                time.sleep(1)


# Main execution
if __name__ == "__main__":
    # Configuration (customize for your network)
    PLAYER_NAME = "Player1"
    WIFI_SSID = "Melmany"  # Replace with your WiFi name
    WIFI_PASSWORD = "Melmansan2012"  # Replace with your WiFi password
    SERVER_IP = "192.168.1.221"  # Replace with your server's IP address
    
    # Create and run the client
    client = PicoClient(PLAYER_NAME, WIFI_SSID, WIFI_PASSWORD, SERVER_IP)
    client.run()
