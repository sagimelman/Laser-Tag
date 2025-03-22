from machine import Pin
from component import Component

class IRComponent(Component):
    """
    Abstract base class for IR-related components.
    Inherits from Component and adds IR-specific functionality.
    """
    def __init__(self, pin, mode=None, frequency=38000):
        """
        Initialize the IR component.
        
        :param pin: GPIO pin number the IR component is connected to
        :param mode: Pin mode (IN for receiver, OUT for transmitter)
        :param frequency: IR carrier frequency in Hz (default: 38kHz)
        """
        super().__init__(pin, mode)
        self.frequency = frequency
        
        # Ensure this class isn't instantiated directly
        if type(self) is IRComponent:
            raise TypeError("Can't instantiate abstract class 'IRComponent' directly")
    
    def send_code(self, code):
        """Send an IR code (for transmitters)"""
        raise NotImplementedError("Subclasses must implement send_code()")
    
    def receive_code(self, timeout=None):
        """Receive an IR code (for receivers)"""
        raise NotImplementedError("Subclasses must implement receive_code()")
    
    def decode(self, raw_data):
        """Decode raw IR data into a meaningful code"""
        raise NotImplementedError("Subclasses must implement decode()")
    
    def encode(self, code):
        """Encode a code into raw IR data format"""
        raise NotImplementedError("Subclasses must implement encode()")
    
    # Override Component's abstract methods
    def enable(self):
        raise NotImplementedError("Subclasses must implement enable()")
    
    def disable(self):
        raise NotImplementedError("Subclasses must implement disable()")
    
    def read(self):
        raise NotImplementedError("Subclasses must implement read()")
    
    def write(self, value):
        raise NotImplementedError("Subclasses must implement write()")
