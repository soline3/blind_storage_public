from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, session, send_file
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
import boto3
from botocore.exceptions import ClientError
from config_google import ConfigGoogle
from google.cloud import storage
import os
from datetime import timedelta
import sqlite3
from charm.toolbox.pairinggroup import PairingGroup, ZR, G1
from database import db
from chiffrement_upload import encrypt_file, re_encrypt
import io
import base64
import json
import requests
from s2_api import get_global_g, generate_and_register_keys, get_public_key


group = PairingGroup('SS512')


def get_db_connection():
    conn = sqlite3.connect("users.db")  # Connexion à la base SQLite
    conn.row_factory = sqlite3.Row  # Permet d'accéder aux colonnes par nom
    return conn


app = Flask(__name__)
app.secret_key = 'SECRETKEY'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config.from_object(ConfigGoogle)

app.config['SESSION_COOKIE_SECURE'] = False  # Désactive pour le dev local
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

app.config['SESSION_TYPE'] = 'filesystem'


# Initialisation
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"  # Redirige vers cette page si l'utilisateur n'est pas connecté

from model_SQLAlchemy import UserKeys, GlobalParameters


# Initialisation du client Google Cloud Storage
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = app.config['GOOGLE_APPLICATION_CREDENTIALS']
storage_client = storage.Client()

print("Projet :", os.getenv('GOOGLE_CLOUD_PROJECT'))
print("Bucket :", os.getenv('GOOGLE_CLOUD_BUCKET'))
print("Fichier JSON :", os.getenv('GOOGLE_APPLICATION_CREDENTIALS'))

# Modèle utilisateur
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Route de base
@app.route('/')
def home():
    return render_template('login.html')

# Route d'inscription
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        if User.query.filter_by(username=username).first():
            flash('Le nom d\'utilisateur est déjà pris.')
            return redirect(url_for('register'))

        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        generate_and_register_keys(username)
        flash('Compte créé avec succès ! Vous pouvez maintenant vous connecter.', 'success')
        
        return redirect(url_for('login'))

    return render_template('register.html')

        

# Route de connexion
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            session['username'] = username
            flash('Connexion réussie.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Nom d\'utilisateur ou mot de passe incorrect.', 'erreur')

    return render_template('login.html')


# Route pour le tableau de bord
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', name=current_user.username)
 

# Route pour téléverser un fichier sur GSC
@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'GET':
        return render_template('upload.html')

    print("Requête reçue :", request.method)  # DEBUG

    print("Session actuelle :", session)
    if 'username' not in session:
        print("Erreur : utilisateur non authentifié")
        return jsonify({'error': 'Utilisateur non authentifié'}), 401

    if 'file' not in request.files:
        print("Erreur : Pas de fichier envoyé")
        return jsonify({'error': 'Pas de fichier envoyé'}), 400

    file = request.files['file']
    if file.filename == '':
        print("Erreur : Nom de fichier vide")
        return jsonify({'error': 'Nom de fichier vide'}), 400


    try:
        # Initialiser le client Google Cloud Storage
        storage_client = storage.Client()
        bucket_name = app.config['GOOGLE_CLOUD_BUCKET']
        bucket = storage_client.bucket(bucket_name)

        username = session['username']
        unique_filename = get_unique_filename(bucket, username, file.filename)
        file_key = f"{username}/{unique_filename}"

        #Chiffrer le fichier avant l'upload
        file_contents = file.read()
        file_stream = io.BytesIO(file_contents)
        encrypted_file = encrypt_file(username, file_stream)

        # Créer un blob et téléverser le fichier
        blob = bucket.blob(file_key)
        blob.upload_from_file(encrypted_file)

        print(f"Fichier enregistré : {file.filename} - Propriétaire : {username}") #Debug
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO fichiers (fichier, owner) VALUES (?, ?)", (unique_filename, username))
        conn.commit()
        conn.close()

        # Générer une URL pré-signée
        file_url = blob.generate_signed_url(expiration=timedelta(days=1), method='GET')

        print("Fichier téléversé avec succès :", file_url)
        return jsonify({'message': 'Fichier téléversé avec succès', 'url': file_url}), 200

    except Exception as e:
        print("Erreur serveur :", str(e))  # DEBUG
        return jsonify({'error': str(e)}), 500

# Pour éviter les conflits de noms identiques de fichiers    
def get_unique_filename(bucket, username, filename):
    original_name, ext = os.path.splitext(filename)
    new_filename = filename
    index = 1

    while bucket.blob(f"{username}/{new_filename}").exists():
        new_filename = f"{original_name}_{index}{ext}"
        index += 1

    return new_filename
    

# Route pour partager un document
@app.route('/share', methods=['POST'])
def share_file():
    print("Session actuelle :", session)  # Debug
    if 'username' not in session:
        return jsonify({'error': 'Utilisateur non authentifié'}), 401

    data = request.json
    fichier = data.get('fichier')  # Nom du fichier à partager
    shared_with = data.get('shared_with')  # Utilisateur avec qui partager
    print("Données reçues :", data)  # Ajout du log

    # Vérifier si le fichier appartient bien à l'utilisateur
    owner = session['username']
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM fichiers WHERE fichier = ? AND owner = ?", (fichier, owner))
    fichier_id = cursor.fetchone()


    if not fichier_id:
        print(f"Problème : Le fichier '{fichier}' n'appartient pas à {owner}")
        conn.close()
        return jsonify({'error': 'Fichier non trouvé ou accès refusé'}), 403

    # Ajouter le partage dans la base de données
    cursor.execute("INSERT INTO partages (fichier_id, shared_with) VALUES (?, ?)", (fichier_id[0], shared_with))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Fichier partagé avec succès !'})


# Route pour consulter ses fichiers
@app.route('/files', methods=['GET'])
def files():
    if 'username' not in session:
        return jsonify({'error': 'Utilisateur non authentifié'}), 401

    username = session['username']
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("SELECT fichier FROM fichiers WHERE owner = ?", (username,))
    fichiers = [{'fichier': row[0]} for row in cursor.fetchall()]

    conn.close()

    return render_template('files.html', fichiers=fichiers)


# Route pour consulter les fichiers obtenus par partage
@app.route('/shared_files', methods=['GET'])
def shared_files():
    if 'username' not in session:
        return jsonify({'error': 'Utilisateur non authentifié'}), 401

    username = session['username']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT fichiers.fichier, fichiers.owner 
    FROM fichiers
    JOIN partages ON fichiers.id = partages.fichier_id
    WHERE partages.shared_with = ?
""", (username,))
    fichiers_partages = [{'fichier': row[0]} for row in cursor.fetchall()]
    conn.close()

    return render_template('shared_files.html', fichiers=fichiers_partages)


# Route pour télécharger un fichier
@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    if 'username' not in session:
        return jsonify({'error': 'Utilisateur non authentifié'}), 401

    username = session['username']
    conn = get_db_connection()
    cursor = conn.cursor()

    # Vérifie si l'utilisateur est propriétaire
    cursor.execute("SELECT owner FROM fichiers WHERE fichier = ?", (filename,))
    owner_row = cursor.fetchone()
    is_owner = False
    if owner_row:
        owner = owner_row[0]
        is_owner = (owner == username)
    else:
        # Vérifie le partage
        cursor.execute("""
            SELECT fichiers.owner 
            FROM fichiers
            JOIN partages ON fichiers.id = partages.fichier_id
            WHERE fichiers.fichier = ? AND partages.shared_with = ?
        """, (filename, username))
        owner_row = cursor.fetchone()
        if owner_row:
            owner = owner_row[0]
        else:
            conn.close()
            return jsonify({'error': 'Vous ne possédez pas les droits d accès à ce document'}), 403
    conn.close()

    try:
        # Télécharger depuis GCS
        storage_client = storage.Client()
        bucket = storage_client.bucket(app.config['GOOGLE_CLOUD_BUCKET'])
        blob = bucket.blob(f"{owner}/{filename}")

        encrypted_file_bytes = blob.download_as_bytes()
        print("Fichier chiffré récupéré depuis GCS.")

        # Lire contenu JSON pour analyse
        encrypted_data = json.loads(encrypted_file_bytes.decode())
        is_owner = (username == owner)

        # Si pas propriétaire, effectuer le rechiffrement proxy sur S1
        if not is_owner:
            print(f"{username} n'est pas propriétaire. Début re-chiffrement proxy...")
            updated_encrypted_data = re_encrypt(encrypted_data, delegate=owner, deleguee=username)
        else:
            updated_encrypted_data = encrypted_data  # inchangé si propriétaire

        # Appel à S2 pour déchiffrement (clé privée)
        decrypt_url = 'http://localhost:5001/decrypt_file'
        response = requests.post(decrypt_url, json={
            'username': username,
            'owner': owner,
            'encrypted_data': updated_encrypted_data
        })

        if response.status_code != 200:
            raise Exception(f"Erreur de déchiffrement via S2 : {response.text}")

        # Récupération et retour du contenu déchiffré
        plaintext_b64 = response.json()['plaintext']
        plaintext_bytes = base64.b64decode(plaintext_b64)

        print("Fichier déchiffré avec succès.")
        return send_file(io.BytesIO(plaintext_bytes), as_attachment=True, download_name=f"decrypted_{filename}")
    
    except Exception as e:
        print(f"Erreur lors du téléchargement/déchiffrement : {str(e)}")
        return jsonify({'error': f'Erreur serveur : {str(e)}'}), 500



# Route pour supprimer un fichier
@app.route('/delete/<filename>', methods=['GET'])
def delete_file(filename):
    if 'username' not in session:
        return jsonify({'error': 'Utilisateur non authentifié'}), 401

    username = session['username']
    conn = get_db_connection()
    cursor = conn.cursor()

    # Vérifier si le fichier appartient à l'utilisateur
    cursor.execute("SELECT * FROM fichiers WHERE fichier = ? AND owner = ?", (filename, username))
    file_entry = cursor.fetchone()

    if not file_entry:
        conn.close()
        return jsonify({'error': 'Accès refusé ou fichier introuvable'}), 403

    try:
        # Supprimer du Google Cloud Storage
        storage_client = storage.Client()
        bucket = storage_client.bucket(app.config['GOOGLE_CLOUD_BUCKET'])
        blob = bucket.blob(f"{username}/{filename}")

        if blob.exists():
            blob.delete()
        else:
            conn.close()
            return jsonify({'error': 'Fichier non trouvé sur le cloud'}), 404

        # Supprimer de la base de données
        cursor.execute("DELETE FROM fichiers WHERE fichier = ? AND owner = ?", (filename, username))
        conn.commit()
        conn.close()

        return jsonify({'message': 'Fichier supprimé avec succès'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500



# Route de déconnexion
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('login'))



# Lancement de l'app
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Crée la base de données dans le contexte de l'application
    app.run(debug=True)


