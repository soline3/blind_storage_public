import requests
from charm.toolbox.pairinggroup import PairingGroup, ZR, G1
import base64

group = PairingGroup('SS512')
S2_BASE_URL = "http://localhost:5001"  


def get_global_g():
    try:
        response = requests.get(f"{S2_BASE_URL}/get_g")
        response.raise_for_status()
        g_str = response.json()['g']
        return group.deserialize(g_str.encode())
    except Exception as e:
        raise RuntimeError(f"Erreur récupération de g : {e}")

def get_public_key(username):
    try:
        response = requests.get(f"{S2_BASE_URL}/get_public_key/{username}")
        response.raise_for_status()
        pk_str = response.json()['public_key']
        return group.deserialize(pk_str.encode())
    except Exception as e:
        raise RuntimeError(f"Erreur récupération de clé publique : {e}")

def generate_and_register_keys(username):
    try:
        response = requests.post(f"{S2_BASE_URL}/generate_keypair/{username}")
        response.raise_for_status()
        data = response.json()
        public_key  = group.deserialize(data['public_key'].encode())
        return public_key
    except Exception as e:
        raise RuntimeError(f"Erreur génération des clés pour {username} : {e}")
    

def get_rekey(sender, recipient):
    url = f"{S2_BASE_URL}/get_rekey"
    params = {'from': sender, 'to': recipient}
    response = requests.get(url, params=params)

    if response.status_code == 200:
        rk_serialized = response.json()['rk']
        rk = group.deserialize(rk_serialized.encode())
        return rk
    else:
        raise Exception(f"Erreur {response.status_code} : {response.text}")
    
def call_remote_decrypt(username, owner, file_bytes):
    url = f"{S2_BASE_URL}/decrypt_file"
    data = {
        'username': username,
        'owner': owner,
        'encrypted_data': file_bytes
    }
    response = requests.post(url, json=data)
    response.raise_for_status()
    result = response.json()
    return base64.b64decode(result['plaintext'])
