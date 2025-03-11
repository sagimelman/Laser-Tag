import time
import machine

# Set up the button with internal pull-down resistor
button_pin = machine.Pin(17, machine.Pin.IN, machine.Pin.PULL_DOWN)

# Variable to track the last button state
last_state = 0  # Button is not pressed (should be low with pull-down)
debounce_time = 0.05  # 50 milliseconds debounce time
last_time = time.ticks_ms()

while True:
    current_state = button_pin.value()  # Read the current state
    current_time = time.ticks_ms()

    # Only detect changes and handle debouncing
    if current_state != last_state and time.ticks_diff(current_time, last_time) > debounce_time * 1000:
        last_time = current_time  # Update the last debounced time
        last_state = current_state  # Update the last state

        if current_state == 1:  # Button pressed (active high)
            print("Button Pressed")
        else:
            print("Button Released")

    time.sleep(0.01)  # Small delay to prevent excessive CPU usage

