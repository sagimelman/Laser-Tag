from machine import Pin
import time
from IRComponent import IRComponent

class IRReceiver(IRComponent):
    """
    IR Receiver class for receiving and decoding IR signals.
    """
    def __init__(self, pin, frequency=38000):
        """
        Initialize the IR receiver.
        
        :param pin: GPIO pin number the IR receiver is connected to
        :param frequency: IR carrier frequency in Hz (default: 38kHz)
        """
        super().__init__(pin, Pin.IN, frequency)
        self.is_enabled = True
        self.last_code = None
        self.last_raw_data = None
    
    def receive_code(self, timeout=5000):
        """
        Wait for and receive an IR code.
        
        :param timeout: Maximum time to wait for a code (in ms), default 5000ms (5 seconds)
        :return: The received code, or None if timeout
        """
        if not self.is_enabled:
            return None
        
        # Capture raw IR signal
        raw_data = self._read_ir_signal(timeout)
        
        if raw_data and len(raw_data) > 5:  # Make sure we have enough data
            self.last_raw_data = raw_data
            # Try to decode the signal
            code = self.decode(raw_data)
            self.last_code = code
            return code
        return None
    
    def _read_ir_signal(self, timeout_ms=5000):
        """
        Read raw IR signal pulses and spaces.
        
        :param timeout_ms: Timeout in milliseconds
        :return: List of pulse durations in microseconds, or None if timeout
        """
        signal = []
        start_time = time.ticks_ms()
        last_time = time.ticks_us()
        
        # Wait for initial signal
        while time.ticks_diff(time.ticks_ms(), start_time) < timeout_ms:
            if self.pin.value() == 0:  # Signal detected (LOW)
                break
                
        # If no signal detected within timeout, return None
        if time.ticks_diff(time.ticks_ms(), start_time) >= timeout_ms:
            return None
            
        # Read signal
        while True:
            if self.pin.value() == 0:  # Signal LOW (pulse)
                pulse_start = time.ticks_us()
                
                # Wait until signal goes HIGH
                while self.pin.value() == 0:
                    # Check if we've timed out during this wait
                    if time.ticks_diff(time.ticks_ms(), start_time) >= timeout_ms:
                        break
                
                pulse_duration = time.ticks_diff(time.ticks_us(), pulse_start)
                signal.append(pulse_duration)
                last_time = time.ticks_us()
            
            # If signal has been idle too long or we have enough data
            if len(signal) > 3 and time.ticks_diff(time.ticks_us(), last_time) > 10000:
                break
                
            # Check overall timeout
            if time.ticks_diff(time.ticks_ms(), start_time) >= timeout_ms:
                break
        
        return signal if signal else None
    
    def decode(self, raw_data):
        """
        Decode raw IR pulse/space timings into a meaningful code.
        
        :param raw_data: Raw timing data to decode
        :return: Decoded IR code as integer
        """
        if not raw_data or len(raw_data) < 4:
            return None
            
        # Simple decoding logic - you'll want to customize this for your protocol
        # For laser tag, we might use a simple pulse width encoding
        # where short pulses (< 1000μs) are 0s and long pulses (> 1000μs) are 1s
        
        # Find the average pulse length to determine threshold
        avg_pulse = sum(raw_data) / len(raw_data)
        threshold = avg_pulse * 0.8  # 80% of average as threshold
        
        # Convert pulses to bits
        bits = []
        for pulse in raw_data:
            if pulse < threshold:
                bits.append(0)  # Short pulse = 0
            else:
                bits.append(1)  # Long pulse = 1
        
        # Convert bit array to integer
        result = 0
        for bit in bits:
            result = (result << 1) | bit
            
        return result
    
    def print_raw_data(self):
        """Print the last received raw IR data for debugging."""
        if self.last_raw_data:
            print("Raw IR signal:", self.last_raw_data)
        else:
            print("No IR data received yet")
    
    def send_code(self, code):
        """Not applicable for receivers"""
        raise NotImplementedError("Receivers cannot send codes")
    
    def encode(self, code):
        """Not typically needed for receivers but could be implemented"""
        raise NotImplementedError("Encode not implemented for receivers")
    
    # Implement Component's abstract methods
    def enable(self):
        """Enable the IR receiver"""
        self.is_enabled = True
    
    def disable(self):
        """Disable the IR receiver"""
        self.is_enabled = False
    
    def read(self):
        """Read the last received IR code"""
        return self.last_code
    
    def write(self, value):
        """Not applicable for receivers"""
        raise NotImplementedError("Cannot write to an input IR receiver")
