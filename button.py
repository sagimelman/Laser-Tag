from machine import Pin  # type: ignore
from time import ticks_ms, sleep
from component import Component  # Import the Component class

"""SOURCE CODE FROM GITHUB
SOURCE URL: https://github.com/ubidefeo/MicroPython-Button.git"""

class Button(Component):  # Make Button a child class of Component
    rest_state = False
    RELEASED = 'released'
    PRESSED = 'pressed'
    DEBOUNCE_TIME = 50
    
    def __init__(self, pin, rest_state = False, callback = None, internal_pullup = False, internal_pulldown = False, debounce_time = None):
        # Determine the pin mode
        mode = Pin.IN
        
        # Call the Component's __init__ method with pin and mode
        super().__init__(pin, mode)
        
        self.rest_state = rest_state
        self.previous_state = rest_state
        self.current_state = rest_state
        self.previous_debounced_state = rest_state
        self.current_debounced_state = rest_state
        self.last_check_tick = ticks_ms()
        self.debounce_time = debounce_time or Button.DEBOUNCE_TIME
        
        # Set up the pull resistor
        if internal_pulldown:
            self.internal_pull = Pin.PULL_DOWN
            self.rest_state = False
        elif internal_pullup:
            self.internal_pull = Pin.PULL_UP
            self.rest_state = True
        else:
            self.internal_pull = None
            
        # Configure the pin with the appropriate pull resistor
        self.pin = Pin(pin, mode=Pin.IN, pull=self.internal_pull)
        
        self.callback = callback
        self.active = False
        self.counter_pressed = 0  # Initialize counter_pressed attribute
        self.was_pressed = False  # Add flag to track if button was previously pressed
        self.is_enabled = True    # Track if button is enabled
    
    def debounce(self):
        """Debounce the button signal to prevent multiple triggers"""
        if not self.is_enabled:
            return
            
        ms_now = ticks_ms()
        self.current_state = self.pin.value()
        state_changed = self.current_state != self.previous_state
        if state_changed:
            self.last_check_tick = ms_now
        state_stable = (ms_now - self.last_check_tick) > self.debounce_time
        if state_stable and not state_changed:
            self.last_check_tick = ms_now
            self.current_debounced_state = self.current_state
        self.previous_state = self.current_state
    
    def check_debounce_state(self):
        """Check the debounced state and trigger callback if changed"""
        if not self.is_enabled:
            return
            
        if self.current_debounced_state != self.previous_debounced_state:
            if self.current_debounced_state != self.rest_state:
                # Button is pressed (rising edge)
                if not self.was_pressed:  # Only trigger if it wasn't already pressed
                    self.active = True
                    self.was_pressed = True
                    self.counter_pressed += 1  # Increment counter_pressed attribute
                    if self.callback != None:
                        self.callback(self.pin, Button.PRESSED)
            else:
                # Button is released (falling edge)
                self.active = False
                self.was_pressed = False  # Reset the pressed state
                if self.callback != None:
                    self.callback(self.pin, Button.RELEASED)
        
        self.previous_debounced_state = self.current_debounced_state
    
    def update(self):
        """Update the button state and check for changes"""
        if not self.is_enabled:
            return
            
        self.debounce()
        self.check_debounce_state()
    
    # Implement required Component methods
    def enable(self):
        """Enable the button to respond to changes"""
        self.is_enabled = True
    
    def disable(self):
        """Disable the button from responding to changes"""
        self.is_enabled = False
        self.active = False
    
    def write(self, value):
        """Not applicable for input buttons, but required by Component"""
        raise NotImplementedError("Cannot write to an input button")
    
    def read(self):
        """Read the current button state"""
        return self.active
    
    @staticmethod #Basically means that the method belongs to the class and not to objects!
    def test(pin_number=17):
        """
        Test function for the Button class.
        Creates a button on the specified pin and monitors its state.
        """
        # The callback function that will be invoked when button changes state
        def button_change(pin, event):
            if event == Button.PRESSED:
                # Only print for PRESSED events, not RELEASED
                print(f'Button {pin} has been pressed')
                print(f'Pressed {button.counter_pressed} times')
        
        # Create a Button object
        button = Button(pin_number, False, button_change, internal_pulldown=True)
        
        # Add a small delay to allow the button to settle down
        sleep(0.5)
        
        print(f"Button test started on pin {pin_number}")
        print("Press the button to see events...")
        
        # Main loop to keep checking the button
        while True:
            button.update()
            sleep(0.01)  # Small delay to prevent CPU hogging


# If this file is run directly (not imported), run the test
if __name__ == "__main__":
    Button.test(17)  # Test with button on pin 17
