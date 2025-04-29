from flask_sqlalchemy import SQLAlchemy
from charm.toolbox.pairinggroup import PairingGroup, ZR, G1
from database import db

group = PairingGroup('SS512')

""" N'EST PLUS UTILISE PAR S1 MAIS S2, OBSELETE"""

class UserKeys(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    private_key = db.Column(db.Text, nullable=False)
    public_key = db.Column(db.Text, nullable=False)

class GlobalParameters(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    g_value = db.Column(db.Text, nullable=False)  # Stocke g sous forme de chaîne
