from charm.toolbox.pairinggroup import PairingGroup, G1, GT, pair

# Initialisation du groupe bilinéaire
group = PairingGroup('SS512')

#  Setup
g = group.random(G1)
time_period = "2025-04"
h = group.hash(time_period, G1)  # h dérivé de la période

#  Clés d'Alice 
a0 = group.random()    
a_r = group.random()

pk_A = (g ** a0, g ** a_r)  #(g^a0, g^ar)
sk_A = (a0, a_r)

# Clé de Bob
b = group.random()  # secret de Bob
h_b = h ** b       # Bob publie h^b

# Chiffrement par Alice (niveau 2)
k = group.random()  #k aléa
u = g ** k      
m = group.random(GT)  #m dans GT
E = m * (pair(g, h) ** a_r) # E = m * e(g, h)^{a_r}
# Le ciphertext transmis est (u, E)

#  ReKeyGen par Alice
rk = h_b ** (a_r / a0) # rk = (h^b)^(a_r / a0)

#  Re-chiffrement par le proxy
E_prime = E / (pair(u, rk))


#  Déchiffrement par Bob
adjustment = pair(u, h) ** (a_r * b / a0)  #facteur d'ajustement à partir de u et b
m_recovered = (E_prime * adjustment) / (pair(g, h) ** a_r)  #recupération de m


print("Message original   :", m)
print("Message récupéré   :", m_recovered)
assert m == m_recovered, "Le message récupéré ne correspond pas au message original"
