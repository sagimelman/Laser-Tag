from machine import Pin

class Component:
    def __init__(self, pin: int, mode=None):
        """
        Base component class for all connected components.
        
        :param pin: GPIO pin number the component is connected to.
        :param mode: The mode to configure the GPIO pin (optional, e.g. IN/OUT).
        If mode is None, the pin is not configured (not useful for some components).
        """
        self.pin = Pin(pin, mode) if mode is not None else None  # Assign pin only if mode is provided

        # Check if abstract methods are implemented in the child class
        if type(self) is Component:
            raise TypeError("Can't instantiate abstract class 'Component' directly")

    def enable(self):
        raise NotImplementedError("Subclasses must implement enable()")

    def disable(self):
        raise NotImplementedError("Subclasses must implement disable()")

    def write(self, value):
        raise NotImplementedError("Subclasses must implement write()")

    def read(self):
        raise NotImplementedError("Subclasses must implement read()")





