from machine import Pin
import time
from IRReceiver import IRReceiver

# Create an IR receiver instance on pin 17
ir_receiver = IRReceiver(17)

print("IR Laser Tag Receiver Test")
print("==========================")
print("Waiting for IR signals...")

try:
    while True:
        # Try to receive a code
        code = ir_receiver.receive_code(timeout=2000)  # 2-second timeout
        
        if code is not None:
            print(f"Received code: {code}")
            ir_receiver.print_raw_data()  # Print raw data for debugging
        
        time.sleep(0.1)  # Small delay to prevent CPU hogging

except KeyboardInterrupt:
    print("Program stopped by user")
