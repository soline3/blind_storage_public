import sqlite3

def create_tables():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS partage")

    # Table pour stocker les fichiers
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fichiers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fichier TEXT NOT NULL,
        owner TEXT NOT NULL,
        FOREIGN KEY(owner) REFERENCES users(username)
    )
    """)

    # Table de partage des fichiers
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS partages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fichier_id INTEGER NOT NULL,
        shared_with TEXT NOT NULL,
        FOREIGN KEY(fichier_id) REFERENCES fichiers(id) ON DELETE CASCADE,
        FOREIGN KEY(shared_with) REFERENCES users(username)
    )
    """)


    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_tables()
    print("Tables mises à jour")
