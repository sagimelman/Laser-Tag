from abc import ABC, abstractmethod
from machine import Pin

class Component(ABC):
    def __init__(self, pin: int, mode=None):
        """
        Base component class for all connected components.
        
        :param pin: GPIO pin number the component is connected to.
        :param mode: The mode to configure the GPIO pin (optional, e.g. IN/OUT).
        If mode is None, the pin is not configured (not useful for some components).
        """
        self.pin = Pin(pin, mode) if mode is not None else None  # Assign pin only if mode is provided

    @abstractmethod
    def enable(self):
        """Enable the component (make in child!)."""
        pass

    @abstractmethod
    def disable(self):
        """Disable the component (make in child!)."""
        pass

    @abstractmethod
    def write(self, value):
        """Write data to the component (make in child!)."""
        pass

    @abstractmethod
    def read(self):
        """Read data from the component (make in child!)."""
        pass
