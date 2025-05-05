import machine
from machine import Pin, PWM
import time
from IRComponent import IRComponent

class IRTransmitter(IRComponent):
    """
    IR Transmitter class for encoding and sending IR signals.
    """
    def __init__(self, pin, frequency=38000):
        """
        Initialize the IR transmitter.
        
        :param pin: GPIO pin number the IR LED is connected to
        :param frequency: IR carrier frequency in Hz (default: 38kHz)
        """
        super().__init__(pin, Pin.OUT, frequency)
        self.is_enabled = True
        self.pwm = None
        self._setup_pwm()
    
    def _setup_pwm(self):
        """Set up the PWM for the IR LED"""
        try:
            self.pwm = PWM(self.pin)
            self.pwm.freq(self.frequency)
            self.pwm.duty_u16(0)  # Start with PWM off
        except Exception as e:
            print(f"Error setting up PWM: {e}")
    
    def _carrier_on(self):
        """Turn on the IR carrier signal"""
        if self.pwm:
            self.pwm.duty_u16(32768)  # 50% duty cycle (32768 is half of 65535)
    
    def _carrier_off(self):
        """Turn off the IR carrier signal"""
        if self.pwm:
            self.pwm.duty_u16(0)
    
    def send_code(self, code):
        """
        Send an IR code.
        
        :param code: The code to transmit (player ID or command)
        :return: True if successful, False otherwise
        """
        if not self.is_enabled or not self.pwm:
            return False
        
        # Encode the code into raw timing data
        raw_data = self.encode(code)
        if not raw_data:
            return False
        
        # Transmit the encoded signal
        self._transmit_signal(raw_data)
        return True
    
    def _transmit_signal(self, raw_data):
        """
        Transmit the encoded IR signal using the raw timing data.
        
        :param raw_data: List of pulse durations in microseconds
        """
        # Disable IRQs during transmission for more accurate timing
        irq_state = machine.disable_irq()
        
        try:
            # Simplified transmission protocol:
            # - Each element in raw_data represents a pulse duration
            # - Even indices (0, 2, 4...) are carrier ON durations
            # - Odd indices (1, 3, 5...) are carrier OFF durations
            
            for i, duration in enumerate(raw_data):
                if i % 2 == 0:
                    # Even index - turn carrier on
                    self._carrier_on()
                else:
                    # Odd index - turn carrier off
                    self._carrier_off()
                
                # Wait for the specified duration
                # Convert microseconds to smaller units for more precise timing
                if duration > 0:
                    start = time.ticks_us()
                    while time.ticks_diff(time.ticks_us(), start) < duration:
                        pass
            
            # Ensure carrier is off when done
            self._carrier_off()
        finally:
            # Re-enable IRQs
            machine.enable_irq(irq_state)
    
    def encode(self, code):
        """
        Encode a code into raw IR data format.
        
        :param code: The code to encode (player ID or command)
        :return: List of pulse durations in microseconds
        """
        if not isinstance(code, int):
            try:
                code = int(code)
            except ValueError:
                print("Error: Code must be an integer or convertible to integer")
                return None
        
        # Create a simple encoding scheme for laser tag
        # Start with a header pulse
        raw_data = [3000, 1000]  # 3ms on, 1ms off as header
        
        # Encode each bit of the code
        for i in range(8):  # Assuming 8-bit codes for simplicity
            bit = (code >> i) & 1
            if bit == 1:
                # Long pulse for 1
                raw_data.extend([1000, 500])  # 1ms on, 0.5ms off
            else:
                # Short pulse for 0
                raw_data.extend([500, 500])  # 0.5ms on, 0.5ms off
        
        # Add a stop bit
        raw_data.append(500)  # 0.5ms final pulse
        
        return raw_data
    
    def decode(self, raw_data):
        """
        Not typically used for transmitters, but implemented for completeness.
        
        :param raw_data: Raw IR data to decode
        :return: Decoded integer value or None if invalid
        """
        # We'll implement a simple version here, but it's not the primary
        # function of a transmitter
        if not raw_data or len(raw_data) < 3:
            return None
        
        # Skip header (first two timings)
        data_pulses = raw_data[2:-1]  # Skip header and stop bit
        
        if len(data_pulses) < 16:  # Need at least 16 pulses for 8 bits (on/off pairs)
            return None
        
        result = 0
        for i in range(0, min(16, len(data_pulses)), 2):
            # Check if the ON pulse is long (representing 1) or short (representing 0)
            if data_pulses[i] > 750:  # Threshold between short and long pulses
                bit_value = 1
            else:
                bit_value = 0
            
            # Add this bit to our result
            bit_position = i // 2
            result |= (bit_value << bit_position)
        
        return result
    
    # Implement Component's abstract methods
    def enable(self):
        """Enable the IR transmitter"""
        self.is_enabled = True
    
    def disable(self):
        """Disable the IR transmitter"""
        self.is_enabled = False
        self._carrier_off()  # Ensure IR is off when disabled
    
    def read(self):
        """Not typically used for transmitters"""
        raise NotImplementedError("Cannot read from an output IR transmitter")
    
    def write(self, value):
        """Send a code (same as send_code)"""
        return self.send_code(value)
