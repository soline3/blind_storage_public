from charm.toolbox.pairinggroup import PairingGroup, pair, ZR, G1, GT
from model_SQLAlchemy import db, UserKeys, GlobalParameters
import base64, io, json, os
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Protocol.KDF import HKDF
from Crypto.Hash import SHA256
from Crypto.Util.Padding import unpad
from s2_api import get_global_g, get_public_key, get_rekey
import time

group = PairingGroup('SS512')

def encrypt_file(username, file_stream):
    start = time.perf_counter()
    # Lecture du fichier
    data = file_stream.read()

    # Setup : Récupération des params
    g = get_global_g()

    # KeyGen : Récupération des clés utilisateur (pub/priv)
    pk_A = get_public_key(username)

    # Génération de m ∈ GT + clé AES
    m       = group.random(GT)
    aes_key = HKDF(group.serialize(m), 32, None, SHA256)

    # Enc : Chiffrement symétrique avec AES‑GCM
    cipher_aes = AES.new(aes_key, AES.MODE_GCM)
    ct, tag    = cipher_aes.encrypt_and_digest(data)

    # AFGH : chiffrement de m
    r  = group.random(ZR)
    Z  = pair(g, g)
    C0 = (Z ** r) * m             # dans GT
    C1 = pk_A ** (r)          # dans G1

    payload = {
      'aes': {
        'nonce':      cipher_aes.nonce.hex(),
        'tag':        tag.hex(),
        'ciphertext': ct.hex()
      },
      'proxy_re': {
        'c0': group.serialize(C0).hex(),
        'c1': group.serialize(C1).hex()
      }
    }
    end = time.perf_counter()

    print(f"Temps de chiffrement : {end - start:.6f} secondes")
    return io.BytesIO(json.dumps(payload).encode())


def re_encrypt(encrypted_data, delegate, deleguee):
    
    # Re‑encryption key = pk_B^(1/a)
    rk = get_rekey(delegate, deleguee)

    start = time.perf_counter()
    # Extraction des C0, C1
    C0 = group.deserialize(bytes.fromhex(encrypted_data['proxy_re']['c0']))
    C1 = group.deserialize(bytes.fromhex(encrypted_data['proxy_re']['c1']))

    # Transformation AFGH : C1' = e(C1, rk)
    C1p = pair(C1, rk)  # dans GT

    encrypted_data['proxy_re']['c0'] = group.serialize(C0).hex()
    encrypted_data['proxy_re']['c1'] = group.serialize(C1p).hex()

    end = time.perf_counter()

    print(f"Temps de re-chiffrement : {end - start:.6f} secondes")
    return encrypted_data


# N'EST PLUS UTILISE DANS S1 MAIS S2
"""
def decrypt_file(username, encrypted_file_stream, owner):
    # Récupération clé pr𝚒vée et g
    user = UserKeys.query.filter_by(username=username).first()
    if not user: raise ValueError("Clés utilisateur non trouvées")
    sk = group.deserialize(user.private_key.encode())

    g_entry = GlobalParameters.query.first()
    if not g_entry: raise ValueError("g non initialisé")
    g = group.deserialize(g_entry.g_value.encode())

    # Chargement JSON
    raw  = encrypted_file_stream.read()
    data = json.loads(raw.decode())
    aes  = data['aes']
    pr   = data['proxy_re']

    C0_raw = bytes.fromhex(pr['c0'])
    C1_raw = bytes.fromhex(pr['c1'])

    C0 = group.deserialize(C0_raw)
    C1 = group.deserialize(C1_raw)

    # 3) Récupération de m selon cas
    # si C1 ∈ G1 → original, sinon → re‑encrypté
    if owner==True:
        # test du type en forçant pairing sur G1 : échoue si C1 ∈ GT
        _ = pair(C1, g)
        # -- cas original (C1=g^(r·a)) --
        r_g    = C1 ** (1 / sk)          # g^r
        Zr     = pair(r_g, g)            # Z^r
        m      = C0 / Zr
      
    else:
        # -- cas re‑encrypté (C1 ∈ GT = Z^(r·b)) --
        Zr     = C1 ** (1 / sk)          # (Z^(r·b))^(1/b) = Z^r
        m      = C0 / Zr

    # 4) Dérivation AES & déchiffrement
    aes_key = HKDF(group.serialize(m), 32, None, SHA256)
    nonce   = bytes.fromhex(aes['nonce'])
    tag     = bytes.fromhex(aes['tag'])
    ct      = bytes.fromhex(aes['ciphertext'])

    cipher = AES.new(aes_key, AES.MODE_GCM, nonce=nonce)
    pt     = cipher.decrypt_and_verify(ct, tag)

    return io.BytesIO(pt)
"""