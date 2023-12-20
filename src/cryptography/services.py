from Crypto.Cipher import DES, PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad


def encrypt_message(input_message: str, key: bytes, iv: bytes) -> bytes:
    cipher = DES.new(key, DES.MODE_CBC, iv)
    message = input_message.encode('utf-8')
    ecrypted_message = b''
    for i in range(0, len(message), 8):
        block = message[i:i+8]
        if len(block) == 0:
            break
        elif len(block) % 8 != 0:
            block = pad(block, 8)
        encrypted_block = cipher.encrypt(block)
        ecrypted_message += encrypted_block
    return ecrypted_message


def decrypt_message(input_message: bytes, key: bytes, iv: bytes) -> str:
    cipher = DES.new(key, DES.MODE_CBC, iv)
    decrypted_message = b''
    for i in range(0, len(input_message), 8):
        block = input_message[i:i + 8]
        if len(block) == 0:
            break
        decrypted_block = cipher.decrypt(block)
        try:
            unpadded_block = unpad(decrypted_block, 8)
            decrypted_message += unpadded_block
        except ValueError:
            decrypted_message += decrypted_block
    return decrypted_message.decode('utf-8')


def create_keys():
    rsa = RSA.generate(2048)
    public_key = rsa.publickey().export_key()
    private_key = rsa.export_key()

    des = get_random_bytes(8)
    iv = get_random_bytes(8)
    encrypted_des_key = PKCS1_OAEP.new(RSA.import_key(public_key)).encrypt(des)
    encrypted_des_iv = PKCS1_OAEP.new(RSA.import_key(public_key)).encrypt(iv)
    return public_key, private_key, encrypted_des_key, encrypted_des_iv
