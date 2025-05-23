# Simple Working Encryption for Laser Tag
# Compatible with both PC and MicroPython

import time

# Secret key - change this to anything you want
ENCRYPTION_KEY = "MyLaserTagSecret2024"

def encrypt_message(message, key=ENCRYPTION_KEY):
    """
    Encrypt a message using XOR + timestamp
    message: string or bytes
    returns: encrypted bytes
    """
    if isinstance(message, str):
        message = message.encode('utf-8')
    
    # Add timestamp to prevent replay attacks
    timestamp = int(time.time())
    
    # Convert timestamp to 4 bytes
    timestamp_bytes = []
    for i in range(4):
        timestamp_bytes.append((timestamp >> (i * 8)) & 0xFF)
    
    # XOR encrypt the message
    encrypted = []
    for i, byte in enumerate(message):
        key_byte = ord(key[i % len(key)])
        encrypted.append(byte ^ key_byte)
    
    # Return: timestamp (4 bytes) + encrypted message
    return bytes(timestamp_bytes + encrypted)

def decrypt_message(encrypted_data, key=ENCRYPTION_KEY):
    """
    Decrypt encrypted data
    encrypted_data: bytes from network
    returns: decrypted bytes
    """
    if len(encrypted_data) < 4:
        raise ValueError("Invalid encrypted data")
    
    # Extract timestamp (first 4 bytes)
    timestamp = 0
    for i in range(4):
        timestamp |= encrypted_data[i] << (i * 8)
    
    # Check if message is not too old (within 5 minutes)
    current_time = int(time.time())
    if abs(current_time - timestamp) > 300:  # 5 minutes
        raise ValueError("Message too old or clock mismatch")
    
    # Decrypt the message part
    encrypted_message = encrypted_data[4:]
    decrypted = []
    for i, byte in enumerate(encrypted_message):
        key_byte = ord(key[i % len(key)])
        decrypted.append(byte ^ key_byte)
    
    return bytes(decrypted)

def test_encryption():
    """Test the encryption"""
    test_message = "Hello Laser Tag!"
    print(f"Original: {test_message}")
    
    encrypted = encrypt_message(test_message)
    print(f"Encrypted: {len(encrypted)} bytes")
    
    decrypted = decrypt_message(encrypted)
    result = decrypted.decode('utf-8')
    print(f"Decrypted: {result}")
    
    success = test_message == result
    print(f"Test {'PASSED' if success else 'FAILED'}")
    return success

if __name__ == "__main__":
    test_encryption()