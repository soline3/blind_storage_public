from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from charm.toolbox.pairinggroup import PairingGroup, ZR, G1
from app import app, db
from model_SQLAlchemy import GlobalParameters, UserKeys  # Import du modèle correct

group = PairingGroup('SS512')


""" N'EST PLUS APPELE PAR S1 MAIS S2, OBSELETE """

def initialize_g():
    with app.app_context():
        existing_g = GlobalParameters.query.first()
        if not existing_g:
            g = group.random(G1)  # Génère g
            new_g = GlobalParameters(g_value=group.serialize(g).decode())  # Stocke en base
            db.session.add(new_g)
            db.session.commit()
            print("Paramètre g initialisé et enregistré en base.")
        else:
            print("g existe déjà en base.")

def generate_keys_for_existing_users():
    with app.app_context():
        g_entry = GlobalParameters.query.first()
        if not g_entry:
            print("Erreur : g n'a pas été initialisé.")
            return

        g = group.deserialize(g_entry.g_value.encode())

        users = db.session.execute(db.text("SELECT username FROM User")).fetchall()

        for user in users:
            username = user[0]  # Récupérer le nom d'utilisateur depuis le tuple
            if not UserKeys.query.filter_by(username=username).first():  # Vérifie si la clé existe déjà
                private_key = group.random(ZR)
                public_key = g ** private_key

                new_key_entry = UserKeys(username=username,
                                         private_key=group.serialize(private_key).decode(),
                                         public_key=group.serialize(public_key).decode())
                db.session.add(new_key_entry)

        db.session.commit()
        print("Clés des utilisateurs existants générées avec succès.")

if __name__ == "__main__":
    initialize_g()
    generate_keys_for_existing_users()
