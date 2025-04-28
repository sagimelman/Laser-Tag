from machine import Pin, PWM
import time
from IRcomponent import IRComponent

class IRTransmitter(IRComponent):
    """
    IR Transmitter class for sending IR signals.
    """
    def __init__(self, pin, frequency=38000):
        """
        Initialize the IR transmitter.
        
        :param pin: GPIO pin number the IR transmitter is connected to
        :param frequency: IR carrier frequency in Hz (default: 38kHz)
        """
        super().__init__(pin, Pin.OUT, frequency)
        self.is_enabled = True
        self.pwm = None
        
        # For laser tag, we'll use simple codes with these parameters
        self.header_pulse = 5000  # 5ms header pulse
        self.bit_pulse_short = 500  # 0.5ms for short pulse (0 bit)
        self.bit_pulse_long = 1500  # 1.5ms for long pulse (1 bit)
        self.gap = 500  # 0.5ms gap between pulses
        
    def _setup_pwm(self):
        """Set up PWM for IR carrier frequency"""
        if self.pwm is None:
            self.pwm = PWM(self.pin)
            self.pwm.freq(self.frequency)
            
    def _send_carrier(self, duration_us):
        """
        Send IR carrier signal for the specified duration.
        
        :param duration_us: Duration in microseconds
        """
        self._setup_pwm()
        
        # 50% duty cycle (32767 is 50% of 65535)
        self.pwm.duty_u16(32767)
        time.sleep_us(duration_us)
        self.pwm.duty_u16(0)
        
    def _send_space(self, duration_us):
        """
        Send IR space (no signal) for the specified duration.
        
        :param duration_us: Duration in microseconds
        """
        time.sleep_us(duration_us)
    
    def send_code(self, code):
        """
        Send an IR code using the transmitter.
        
        :param code: The code to transmit (integer)
        :return: True if successful, False otherwise
        """
        if not self.is_enabled:
            return False
            
        # Encode the code into pulse timings
        encoded_data = self.encode(code)
        
        # Send header pulse
        self._send_carrier(self.header_pulse)
        self._send_space(self.gap)
        
        # Send each bit of the code
        for bit_duration in encoded_data:
            self._send_carrier(bit_duration)
            self._send_space(self.gap)
            
        # Ensure carrier is turned off
        if self.pwm:
            self.pwm.duty_u16(0)
            
        return True
    
    def encode(self, code):
        """
        Encode a code into raw IR pulse/space timings.
        
        :param code: The code to encode (integer)
        :return: List of pulse durations in microseconds
        """
        # Convert to integer if not already
        try:
            code_int = int(code)
        except (ValueError, TypeError):
            raise ValueError("Code must be convertible to an integer")
            
        # Convert to binary and remove '0b' prefix
        binary = bin(code_int)[2:]
        
        # Pad with leading zeros to ensure minimum length (16 bits)
        # MicroPython may not have zfill, so using manual padding
        binary = '0' * (16 - len(binary)) + binary
        
        # Convert to pulse durations
        pulses = []
        for bit in binary:
            if bit == '0':
                pulses.append(self.bit_pulse_short)
            else:  # bit == '1'
                pulses.append(self.bit_pulse_long)
                
        return pulses
    
    def receive_code(self, timeout=None):
        """Not applicable for transmitters"""
        raise NotImplementedError("Transmitters cannot receive codes")
    
    def decode(self, raw_data):
        """Not typically needed for transmitters but could be implemented"""
        raise NotImplementedError("Decode not implemented for transmitters")
    
    def cleanup(self):
        """Clean up resources used by transmitter"""
        if self.pwm:
            self.pwm.deinit()
            self.pwm = None
    
    # Implement Component's abstract methods
    def enable(self):
        """Enable the IR transmitter"""
        self.is_enabled = True
    
    def disable(self):
        """Disable the IR transmitter"""
        self.is_enabled = False
        self.cleanup()
    
    def read(self):
        """Not typically used for transmitters"""
        return None
    
    def write(self, value):
        """Send the specified value as an IR code"""
        return self.send_code(value)
