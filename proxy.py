from charm.toolbox.pairinggroup import PairingGroup, ZR, G1, G2, GT, pair


""" -----------PREMIERE VERSION DU PROXY, FAUSSE CAR ON FAIT g^(b-a) AU LIEU DE g^(b/a) ---------------"""

group = PairingGroup('SS512') 

# KeyGen
a = group.random(ZR)  
b = group.random(ZR)

g = group.random(G1)  # generation de g
pk_A = g ** a         # 
pk_B = g ** b         # 

print("a =", a, "\nb =", b, "\ng =", g, "\npk_A =", pk_A, "\npk_B =", pk_B)

# ReKeyGen
rk_A_to_B = pk_B / pk_A   # g^(b-a)
print("rk_A_to_B =", rk_A_to_B)

# Chiffrement
message = group.random(GT)            # Message dans le groupe GT
r = group.random(ZR)                  # aléa aléatoire
ciphertext_A = (g ** r, message * pair(g, pk_A) ** r) 
print("message =", message, "\nr =", r, "\nciphertext_A =", ciphertext_A)

# Re-chiffrement par le proxy
ciphertext_B = (ciphertext_A[0], ciphertext_A[1] * pair(rk_A_to_B, ciphertext_A[0]))
print("ciphertext_B =", ciphertext_B)

# Déchiffrement
decrypt_B = ciphertext_B[1] / pair(ciphertext_B[0], pk_B)
print("decrypt_B =", decrypt_B)

# Vérification
assert decrypt_B == message, "Le déchiffrement a échoué"
print("Le message a été correctement re-chiffré et déchiffré par Bob.")
