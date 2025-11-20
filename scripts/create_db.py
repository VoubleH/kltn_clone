# create_db.py
from db import engine, Base
from models import Book, UserProfile, UserFact

def init_db():
    print("Creating tables in kltndb.sqlite3 ...")
    Base.metadata.create_all(bind=engine)
    print("✅ Done.")

if __name__ == "__main__":
    init_db()
