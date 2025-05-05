import network
import socket
import time
import json
from machine import Pin
from button import Button  # Import your Button class

# Configuration 
PLAYER_NAME = "Player1"
WIFI_SSID = "Melmany"  # Your WiFi name
WIFI_PASSWORD = "Melmansan2012"  # Your WiFi password
SERVER_IP = "192.168.1.221"  # Your server's IP address
SERVER_PORT = 9999

# Setup basic hardware
button_pin = 16  # Pin for the button
status_led_pin = 25  # Pin for status LED

# Use your Button class with internal pulldown
button = Button(button_pin, rest_state=False, internal_pulldown=True)
status_led = Pin(status_led_pin, Pin.OUT)

# Global variables
connected = False
sock = None

def flash_led(count, duration):
    """Flash the built-in status LED on the Raspberry Pi Pico"""
    for _ in range(count):
        status_led.value(1)  # Turn LED on
        time.sleep(duration)
        status_led.value(0)  # Turn LED off
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
            "player_name": PLAYER_NAME
        }
        
        json_message = json.dumps(message).encode('utf-8')
        sock.send(json_message)
        print("Registration message sent to server")
        
        return True
    except Exception as e:
        print(f"Server connection failed: {e}")
        connected = False
        return False

def shoot():
    """Send a shoot message to the server"""
    global connected, sock
    
    if not connected or not sock:
        print("Not connected - can't send message")
        return False
    
    message = {
        "type": "shoot",
        "player_name": PLAYER_NAME
    }
    
    try:
        json_message = json.dumps(message).encode('utf-8')
        print("Sending shoot message:", message)
        
        # Send the data
        bytes_sent = sock.send(json_message)
        
        # Flash LED to confirm
        flash_led(1, 0.1)
        
        return True
    except Exception as e:
        print(f"Send error: {e}")
        connected = False
        return False

# Main execution
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
        
        # Check if button is active (pressed) using your Button class's read method
        if button.read():
            print("Button pressed! Shooting...")
            shoot()
            # Small delay to prevent multiple triggers
            time.sleep(0.2)
        
        # Small delay to prevent 100% CPU usage
        time.sleep(0.01)
except Exception as e:
    print(f"Error in main loop: {e}")
