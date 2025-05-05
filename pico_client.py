import network
import socket
import time
import json
import machine
from machine import Pin
from button import Button  # Import your Button class
from IRTransmitter import IRTransmitter  # Import the IR Transmitter class
from IRReceiver import IRReceiver  # Import the IR Receiver class

# Configuration 
PLAYER_NAME = "Player1"
PLAYER_ID = 1  # Unique ID for this player
WIFI_SSID = "Melmany"  # Your WiFi name
WIFI_PASSWORD = "Melmansan2012"  # Your WiFi password
SERVER_IP = "192.168.1.221"  # Your server's IP address
SERVER_PORT = 9999
PLAYER_HEALTH = 3  # Start with 3 lives
PLAYER_STATUS = "alive"  # Status: "alive" or "eliminated"

# Global variables
connected = False
sock = None
last_shoot_time = 0
last_hit_time = 0  # For debouncing hit detection

# Setup hardware
button_pin = 16  # Pin for the button
status_led_pin = 15  # Pin for status LED
ir_led_pin = 14  # Pin for IR LED transmitter
shoot_led_pin = 13  # Pin for visible LED that shows when IR is active
ir_receiver_pin = 17  # Pin for IR receiver

# Define your custom class first before using it
class CustomIRTransmitter(IRTransmitter):
    """Extended IR Transmitter with visible LED indication"""
    
    def __init__(self, pin, led_pin=None, frequency=38000):
        """
        Initialize the IR transmitter with visible LED indicator.
        
        :param pin: GPIO pin number the IR LED is connected to
        :param led_pin: GPIO pin for visible LED (None if not used)
        :param frequency: IR carrier frequency in Hz (default: 38kHz)
        """
        super().__init__(pin, frequency)
        
        # Set up visible LED if provided
        self.led_pin = None
        if led_pin is not None:
            self.led_pin = Pin(led_pin, Pin.OUT)
            self.led_pin.value(0)  # Make sure LED is off initially
    
    def _carrier_on(self):
        """Turn on the IR carrier signal and visible LED"""
        if self.pwm:
            self.pwm.duty_u16(32768)  # 50% duty cycle
        
        # Also turn on visible LED if available
        if self.led_pin:
            self.led_pin.value(1)
    
    def _carrier_off(self):
        """Turn off the IR carrier signal and visible LED"""
        if self.pwm:
            self.pwm.duty_u16(0)
        
        # Also turn off visible LED if available
        if self.led_pin:
            self.led_pin.value(0)

def flash_led(count, duration):
    """Flash the status LED"""
    for _ in range(count):
        status_led.value(1)
        time.sleep(duration)
        status_led.value(0)
        time.sleep(duration)

def connect_wifi():
    """Connect to WiFi network"""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    print(f"Connecting to {WIFI_SSID}...")
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    
    # Wait for connection with timeout
    max_wait = 10
    while max_wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        max_wait -= 1
        print("Waiting for connection...")
        time.sleep(1)
    
    if wlan.status() != 3:
        print("Network connection failed")
        return False
    
    status = wlan.ifconfig()
    print(f"Connected to WiFi. IP: {status[0]}")
    return True

def connect_to_server():
    """Connect to the game server"""
    global connected, sock
    try:
        addr = socket.getaddrinfo(SERVER_IP, SERVER_PORT)[0][-1]
        sock = socket.socket()
        # Socket is set to blocking mode by default
        sock.connect(addr)
        print("Connected to server")
        
        # Set connected flag
        connected = True
        
        # Register with server
        message = {
            "type": "register",
            "player_name": PLAYER_NAME,
            "player_id": PLAYER_ID
        }
        
        json_message = json.dumps(message).encode('utf-8')
        sock.send(json_message)
        print("Registration message sent to server")
        
        return True
    except Exception as e:
        print(f"Server connection failed: {e}")
        connected = False
        return False

def update_health_display():
    """Update visual feedback based on current health"""
    if PLAYER_STATUS == "eliminated":
        # Eliminated: rapid continuous flashing
        for _ in range(10):  # Flash several times to indicate elimination
            status_led.value(1)
            time.sleep(0.1)
            status_led.value(0)
            time.sleep(0.1)
    else:
        # Show remaining health with LED flashes
        for _ in range(PLAYER_HEALTH):
            status_led.value(1)
            time.sleep(0.2)
            status_led.value(0)
            time.sleep(0.2)

def handle_server_messages():
    """Non-blocking check for server messages"""
    global PLAYER_HEALTH, PLAYER_STATUS, connected, sock
    
    if not connected or not sock:
        return
    
    try:
        # Check if data is available to read (non-blocking)
        sock.setblocking(False)
        try:
            data = sock.recv(1024)
            if data:
                message = json.loads(data.decode('utf-8'))
                print("Received from server:", message)
                
                if message.get('type') == 'health_update':
                    PLAYER_HEALTH = message.get('health', PLAYER_HEALTH)
                    print(f"Health updated: {PLAYER_HEALTH} lives remaining")
                    update_health_display()
                
                elif message.get('type') == 'eliminated':
                    PLAYER_STATUS = "eliminated"
                    print("You have been eliminated!")
                    update_health_display()
                
                elif message.get('type') == 'game_start':
                    # Reset health when game starts
                    PLAYER_HEALTH = 3
                    PLAYER_STATUS = "alive"
                    print("Game started! Health reset to full.")
                    update_health_display()
        except:
            # No data available or connection issue
            pass
        
        # Restore blocking mode
        sock.setblocking(True)
    except Exception as e:
        print(f"Error reading from server: {e}")
        connected = False

def shoot():
    """Send a shoot message and IR signal"""
    global connected, sock, PLAYER_STATUS
    
    # Don't allow shooting if player is eliminated
    if PLAYER_STATUS == "eliminated":
        print("Cannot shoot - you are eliminated!")
        # Flash LED pattern to indicate cannot shoot
        for _ in range(2):
            status_led.value(1)
            time.sleep(0.05)
            status_led.value(0)
            time.sleep(0.05)
        return False
    
    print("Shooting!")
    
    # Create a quick pulse effect on the shoot LED
    for _ in range(3):  # Flash 3 times quickly
        shoot_led.value(1)
        time.sleep(0.05)
        shoot_led.value(0)
        time.sleep(0.05)
    
    # 1. Transmit IR signal with player ID
    shoot_led.value(1)  # Keep LED on during transmission
    ir_success = ir_transmitter.send_code(PLAYER_ID)
    time.sleep(0.1)  # Keep lit briefly after transmission
    shoot_led.value(0)
    
    if ir_success:
        print("IR signal transmitted")
    else:
        print("Failed to transmit IR signal")
    
    # 2. Send message to server if connected
    if connected and sock:
        message = {
            "type": "shoot",
            "player_name": PLAYER_NAME,
            "player_id": PLAYER_ID
        }
        
        try:
            json_message = json.dumps(message).encode('utf-8')
            print("Sending shoot message to server:", message)
            
            # Send the data
            bytes_sent = sock.send(json_message)
            
            # Flash status LED to confirm
            flash_led(1, 0.1)
            
            return True
        except Exception as e:
            print(f"Send error: {e}")
            connected = False
            return False
    else:
        print("Not connected to server - local IR shooting only")
        # Still flash status LED to confirm shot
        flash_led(1, 0.1)
        return ir_success

def handle_hit(shooter_id):
    """Handle being hit by another player"""
    global connected, sock, last_hit_time, PLAYER_HEALTH, PLAYER_STATUS
    
    # Debounce hits - ignore multiple hits within 3 seconds
    current_time = time.time()
    if current_time - last_hit_time < 3.0:
        print(f"Hit ignored (debounce): Player {shooter_id}")
        return False
    
    # Update last hit time
    last_hit_time = current_time
    
    print(f"HIT! You were shot by Player {shooter_id}")
    
    # Flash LED rapidly to indicate hit
    for _ in range(5):
        status_led.value(1)
        time.sleep(0.1)
        status_led.value(0)
        time.sleep(0.1)
    
    # Only process hits if player is still alive
    if PLAYER_STATUS == "eliminated":
        print("Hit ignored: You are already eliminated")
        return False
    
    # Send hit message to server if connected
    if connected and sock:
        message = {
            "type": "hit",
            "player_name": PLAYER_NAME,
            "player_id": PLAYER_ID,
            "shooter_id": shooter_id
        }
        
        try:
            json_message = json.dumps(message).encode('utf-8')
            print("Sending hit message to server:", message)
            
            # Send the data
            bytes_sent = sock.send(json_message)
            return True
        except Exception as e:
            print(f"Send error: {e}")
            connected = False
            return False
    else:
        print("Not connected to server - local hit processing only")
        # Handle local health tracking
        PLAYER_HEALTH -= 1
        if PLAYER_HEALTH <= 0:
            PLAYER_STATUS = "eliminated"
            print("You have been eliminated!")
        else:
            print(f"Health reduced to {PLAYER_HEALTH}")
        
        update_health_display()
        return True
def check_for_hits():
    """Check if we've been hit by an IR signal"""
    # Non-blocking check for IR signal
    code = ir_receiver.receive_code(timeout=100)  # Short timeout for non-blocking
    
    if code is not None:
        print(f"Received IR code: {code}")
        
        # Check if this is a valid player ID (e.g., between 1-8 for 8 players)
        # Adjust the range based on how many players you have
        if 1 <= code <= 8:  # Valid player IDs are 1-8
            handle_hit(code)
            return True
        else:
            print(f"Ignoring invalid player ID: {code}")
    
    return False


def update_health_display():
    """Update visual feedback based on current health"""
    global PLAYER_HEALTH, PLAYER_STATUS, status_led
    
    if PLAYER_STATUS == "eliminated":
        # Eliminated: rapid continuous flashing
        for _ in range(10):  # Flash several times to indicate elimination
            status_led.value(1)
            time.sleep(0.1)
            status_led.value(0)
            time.sleep(0.1)
    else:
        # Show remaining health with LED flashes
        for _ in range(PLAYER_HEALTH):
            status_led.value(1)
            time.sleep(0.2)
            status_led.value(0)
            time.sleep(0.2)

def handle_server_messages():
    """Non-blocking check for server messages"""
    global PLAYER_HEALTH, PLAYER_STATUS, connected, sock
    
    if not connected or not sock:
        return
    
    try:
        # Check if data is available to read (non-blocking)
        sock.setblocking(False)
        try:
            data = sock.recv(1024)
            if data:
                message = json.loads(data.decode('utf-8'))
                print("Received from server:", message)
                
                if message.get('type') == 'health_update':
                    PLAYER_HEALTH = message.get('health', PLAYER_HEALTH)
                    print(f"Health updated: {PLAYER_HEALTH} lives remaining")
                    update_health_display()
                
                elif message.get('type') == 'eliminated':
                    PLAYER_STATUS = "eliminated"
                    print("You have been eliminated!")
                    update_health_display()
                
                elif message.get('type') == 'game_start':
                    # Reset health when game starts
                    PLAYER_HEALTH = 3
                    PLAYER_STATUS = "alive"
                    print("Game started! Health reset to full.")
                    update_health_display()
        except:
            # No data available or connection issue
            pass
        
        # Restore blocking mode
        sock.setblocking(True)
    except Exception as e:
        print(f"Error reading from server: {e}")
        connected = False



# Initialize components
button = Button(button_pin, rest_state=False, internal_pulldown=True)
status_led = Pin(status_led_pin, Pin.OUT)
shoot_led = Pin(shoot_led_pin, Pin.OUT)  # LED to indicate shooting
ir_transmitter = CustomIRTransmitter(ir_led_pin, shoot_led_pin)
ir_receiver = IRReceiver(ir_receiver_pin)  # Initialize IR receiver# Main execution
print("Starting Laser Tag client...")

# Connect to WiFi
if not connect_wifi():
    # Blink LED to show wifi connection error
    while True:
        flash_led(1, 0.5)
        time.sleep(0.5)

# Connect to server
if not connect_to_server():
    # Blink LED differently to show server connection error
    while True:
        flash_led(2, 0.2)
        time.sleep(1)

# Flash LED to show we're ready
flash_led(3, 0.2)

# Main loop - check button and send shoot message
print("Ready! Press the button to shoot.")

try:
    while True:
        # Update button state using your Button class's update method
        button.update()
        
        # Check for server messages
        handle_server_messages()
        
        # Check if button is active (pressed) using your Button class's read method
        if button.read():
            # Get current time
            current_time = time.time()
            
            # Only shoot if enough time has passed since the last shot
            if current_time - last_shoot_time > 0.5:  # 500ms debounce period
                print("Button pressed! Shooting...")
                shoot()
                # Update the last shoot time
                last_shoot_time = current_time
            else:
                print("Button press ignored (debounce)")
        
        # Check for hits from IR receiver
        check_for_hits()
        
        # Small delay to prevent 100% CPU usage
        time.sleep(0.01)
except Exception as e:
    print(f"Error in main loop: {e}")
