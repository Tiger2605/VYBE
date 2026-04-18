from sqlalchemy import text

def add_columns(db):
    """
    On passe 'db' en argument pour éviter d'importer 'app' ici 
    et risquer une erreur d'importation circulaire.
    """
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
            print(f"Succès : {query}")
        except Exception as e:
            print(f"Info : {query} n'a pas pu être exécutée (normal si déjà là) : {e}")
    
    db.session.commit()
    print("Patch de base de données VYBE terminé.")