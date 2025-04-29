from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from charm.toolbox.pairinggroup import PairingGroup, ZR, G1, pair
from app import app, db
from model_SQLAlchemy import GlobalParameters, UserKeys

group = PairingGroup('SS512')

def verify_user_keys():
    with app.app_context():
        g_entry = GlobalParameters.query.first()
        if not g_entry:
            print("Erreur : paramètre global g non trouvé.")
            return

        g = group.deserialize(g_entry.g_value.encode())
        all_keys = UserKeys.query.all()

        if not all_keys:
            print("Aucune clé utilisateur trouvée.")
            return

        print("🔍 Vérification des paires de clés...\n")

        for entry in all_keys:
            username = entry.username
            try:
                sk = group.deserialize(entry.private_key.encode())
                pk = group.deserialize(entry.public_key.encode())

                # Test de cohérence : pair(g, pk) == pair(g, g)^sk
                left = pair(g, pk)
                right = pair(g, g) ** sk

                if left == right:
                    print(f"{username} : paire de clés valide")
                else:
                    print(f"{username} : paire de clés invalide")

            except Exception as e:
                print(f"[Utilisateur] {username} : erreur pendant la vérification → {e}")

        print("\n Vérification terminée.")

        sk = group.random(ZR)
        print("1")
        g = group.random(G1)
        print("2")
        c1 = g ** 3
        print("pair test =", pair(c1, sk))  # ne devrait pas être [1, 0]

verify_user_keys()
