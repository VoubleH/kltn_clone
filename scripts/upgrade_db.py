# upgrade_db.py
from db import engine
from models import Base

if __name__ == "__main__":
    print("Creating missing tables (if any)...")
    Base.metadata.create_all(bind=engine)
    print("✅ Done.")
