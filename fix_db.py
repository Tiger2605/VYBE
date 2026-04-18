from app import app, db
from sqlalchemy import text

def add_columns():
    with app.app_context():
        # Liste des colonnes qu'on soupçonne manquantes d'après ton erreur
        queries = [
            "ALTER TABLE video ADD COLUMN IF NOT EXISTS description VARCHAR(500);",
            "ALTER TABLE video ADD COLUMN IF NOT EXISTS category VARCHAR(100);",
            "ALTER TABLE video ADD COLUMN IF NOT EXISTS tags VARCHAR(200);",
            "ALTER TABLE video ADD COLUMN IF NOT EXISTS views INTEGER DEFAULT 0;",
            "ALTER TABLE video ADD COLUMN IF NOT EXISTS cover_url VARCHAR(500);"
        ]
        
        for query in queries:
            try:
                db.session.execute(text(query))
                print(f"Exécuté : {query}")
            except Exception as e:
                print(f"Erreur sur {query} : {e}")
        
        db.session.commit()
        print("Mise à jour de la base terminée !")

if __name__ == "__main__":
    add_columns()