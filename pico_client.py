from client import Client
import network
import socket
import time
import json
import machine
from machine import Pin

# Import your hardware components
from button import Button
from ir_receiver import IRReceiver
from ir_transmitter import IRTransmitter

class PicoClient(Client):
    def __init__(self, player_name, ssid, password, server_ip, server_port=9999):
        super().__init__()
        self.player_name = player_name
        self.ssid = ssid
        self.password = password
        self.server_ip = server_ip
        self.server_port = server_port
        
        # Player state
        self.player_id = None
        self.health = 100
        self.is_alive = True
        self.game_active = False
        
        # Network state
        self.wlan = None
        self.sock = None
        self.connected = False
        
        # Set up hardware pins - adjust based on your actual connections
        self.trigger_pin = 15  # Pin for trigger button
        self.ir_receiver_pin = 16  # Pin for IR receiver
        self.ir_transmitter_pin = 17  # Pin for IR transmitter
        self.status_led_pin = 18  # Pin for status LED
        
        # Initialize hardware components
        self.setup_hardware()
    
    def setup_hardware(self):
        """Initialize hardware components"""
        # Setup button with callback
        self.trigger = Button(Pin(self.trigger_pin, Pin.IN, Pin.PULL_UP))
        self.trigger.set_callback(self.on_trigger_pressed)
        
        # Setup IR receiver with callback
        self.ir_receiver = IRReceiver(Pin(self.ir_receiver_pin, Pin.IN))
        self.ir_receiver.set_callback(self.on_ir_received)
        
        # Setup IR transmitter
        self.ir_transmitter = IRTransmitter(Pin(self.ir_transmitter_pin, Pin.OUT))
        
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
            addr = socket.getaddrinfo(self.server_ip, self.server_port)[0][-1]
            self.sock = socket.socket()
            self.sock.connect(addr)
            self.sock.settimeout(0.1)  # Short timeout for non-blocking operation
            print("Connected to server")
            
            # Register with server
            self.send_message("register", {"player_name": self.player_name})
            
            self.connected = True
            return True
        except Exception as e:
            print(f"Server connection failed: {e}")
            return False
    
    def send_message(self, msg_type, data=None):
        """Send a message to the server"""
        if not self.connected or not self.sock:
            return False
        
        message = {
            "type": msg_type,
            "player_id": self.player_id,
            "player_name": self.player_name,
            "data": data or {}
        }
        
        try:
            self.sock.send(json.dumps(message).encode('utf-8') + b'\n')
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
            data = self.sock.recv(1024)
            if data:
                return json.loads(data.decode('utf-8'))
        except Exception:
            # Timeout or other error - just continue
            pass
        
        return None
    
    def on_message_received(self, message):
        """Process a message from the server"""
        if not message:
            return
        
        msg_type = message.get("type")
        
        if msg_type == "welcome":
            self.player_id = message.get("player_id")
            print(f"Registered with server as Player {self.player_id}")
            self.flash_led(3, 0.2)  # Flash LED 3 times
        
        elif msg_type == "game_start":
            self.game_active = True
            self.health = 100
            self.is_alive = True
            print("Game started!")
            self.flash_led(3, 0.2)  # Flash LED to indicate game start
        
        elif msg_type == "game_end":
            self.game_active = False
            print("Game ended!")
            winner = message.get("winner_name", "Unknown")
            print(f"Winner: {winner}")
            self.flash_led(5, 0.1)  # Flash LED to indicate game end
            
        elif msg_type == "hit":
            # We've been hit!
            if self.game_active and self.is_alive:
                self.health = message.get("health", self.health)
                if self.health <= 0:
                    self.is_alive = False
                    print("You've been eliminated!")
                    self.flash_led(5, 0.1)  # Show death animation on LED
                else:
                    print(f"Hit! Health: {self.health}")
                    self.flash_led(1, 0.1)  # Quick LED flash for hit
        
        elif msg_type == "respawn":
            self.is_alive = True
            self.health = message.get("health", 100)
            print(f"Respawned! Health: {self.health}")
            self.flash_led(2, 0.3)  # Show respawn animation
    
    def on_ir_received(self, shooter_id):
        """Called when IR receiver detects a signal"""
        if self.game_active and self.is_alive:
            print(f"Hit by player {shooter_id}!")
            # Send hit information to server
            self.send_message("hit_report", {
                "target_id": self.player_id,  # I was hit
                "shooter_id": shooter_id  # Player who shot me
            })
    
    def on_trigger_pressed(self):
        """Called when trigger button is pressed"""
        if self.game_active and self.is_alive:
            print("Firing!")
            # Transmit our player ID via IR
            self.ir_transmitter.transmit(self.player_id)
            # Report shot to server for stats
            self.send_message("shot_fired", {})
    
    def flash_led(self, count, duration):
        """Flash the status LED"""
        for _ in range(count):
            self.status_led.value(1)
            time.sleep(duration)
            self.status_led.value(0)
            time.sleep(duration)
    
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
        try:
            while True:
                # Check for messages from server
                message = self.receive_message()
                if message:
                    self.on_message_received(message)
                
                # Send heartbeat every 5 seconds
                current_time = time.time()
                if current_time - last_heartbeat >= 5:
                    self.send_message("heartbeat", {"health": self.health})
                    last_heartbeat = current_time
                
                # Small delay to prevent 100% CPU usage
                time.sleep(0.01)
        except Exception as e:
            print(f"Fatal error: {e}")
            # Show error pattern on LED
            while True:
                self.flash_led(3, 0.1)
                time.sleep(1)


# Example usage for main.py on the Pico W
if __name__ == "__main__":
    # Configuration (should be customized for your network)
    PLAYER_NAME = "Player1"
    WIFI_SSID = "YourWiFiNetwork"
    WIFI_PASSWORD = "YourWiFiPassword"
    SERVER_IP = "192.168.1.XXX"  # Replace with your server's IP address
    
    # Create and run the client
    client = PicoClient(PLAYER_NAME, WIFI_SSID, WIFI_PASSWORD, SERVER_IP)
    client.run()
