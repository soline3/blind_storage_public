import os
from charm.toolbox.pairinggroup import PairingGroup, ZR, G1, GT, pair
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Protocol.KDF import HKDF
import hashlib
from Crypto.Hash import SHA256

""" -----------PREMIERE VERSION DU PROXY, FAUSSE CAR ON FAIT g^(b-a) AU LIEU DE g^(b/a) ---------------"""


group = PairingGroup('SS512')
g = group.random(G1)

def generate_keys():
    a = group.random(ZR)
    b = group.random(ZR)
    pk_A = g ** a
    pk_B = g ** b
    rk_A_to_B = pk_B / pk_A  # Clé de re-chiffrement
    return (a, pk_A), (b, pk_B), rk_A_to_B, g

def encrypt_file(input_file, output_file, pk_A):
    with open(input_file, 'rb') as f:
        plaintext = f.read()
    
    m = group.random(GT)
    aes_key = HKDF(group.serialize(m), 32, None, SHA256)
    
    cipher_aes = AES.new(aes_key, AES.MODE_GCM)
    ciphertext, tag = cipher_aes.encrypt_and_digest(plaintext)
    
    with open(output_file, 'wb') as f:
        f.write(cipher_aes.nonce + tag + ciphertext)
    
    r = group.random(ZR)
    ciphertext_A = (g ** r, m * pair(g, pk_A) ** r)
    
    return ciphertext_A

def re_encrypt(ciphertext_A, rk_A_to_B):
    return (ciphertext_A[0], ciphertext_A[1] * pair(rk_A_to_B, ciphertext_A[0]))

def decrypt_file(encrypted_file, decrypted_file, ciphertext_B, pk_B):
    m_rec = ciphertext_B[1] / pair(ciphertext_B[0], pk_B)
    aes_key_rec = HKDF(group.serialize(m_rec), 32, None, SHA256)
    
    with open(encrypted_file, 'rb') as f:
        nonce, tag, ciphertext = f.read(16), f.read(16), f.read()
    
    cipher_aes_rec = AES.new(aes_key_rec, AES.MODE_GCM, nonce)
    plaintext = cipher_aes_rec.decrypt_and_verify(ciphertext, tag)
    
    with open(decrypted_file, 'wb') as f:
        f.write(plaintext)

def main():
    input_file = "Hello.txt"
    encrypted_file = "document.enc"
    decrypted_file = "document_decrypted.txt"
    
    (sk_A, pk_A), (sk_B, pk_B), rk_A_to_B, g = generate_keys()
    
    ciphertext_A = encrypt_file(input_file, encrypted_file, pk_A)
    ciphertext_B = re_encrypt(ciphertext_A, rk_A_to_B)
    decrypt_file(encrypted_file, decrypted_file, ciphertext_B, pk_B)
    #decrypt_file(encrypted_file, decrypted_file, ciphertext_A, pk_A)
    
    print("Fichier déchiffré avec succès.")

if __name__ == "__main__":
    main()
