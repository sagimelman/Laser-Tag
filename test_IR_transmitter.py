from machine import Pin
import time
from IRTransmitter import IRTransmitter

# Create an IR transmitter instance on pin 16
ir_transmitter = IRTransmitter(17)

# Use the same Pin 16, but let's not toggle it manually - it should work automatically with IR transmission
print("IR Laser Tag Transmitter Test")
print("============================")

try:
    # Define player ID or gun ID (1-15 for example)
    player_id = 5
    
    print(f"Configured as Player/Gun ID: {player_id}")
    print("Press CTRL+C to stop")
    
    while True:
        print(f"Sending IR signal (code: {player_id})...")
        
        # Send the IR code
        ir_transmitter.send_code(player_id)
        
        # Wait between transmissions
        time.sleep(2)
        
except KeyboardInterrupt:
    print("Program stopped by user")
    ir_transmitter.cleanup()

