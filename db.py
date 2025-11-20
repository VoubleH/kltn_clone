# db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# SQLite file nằm ngay trong thư mục dự án
DATABASE_URL = "sqlite:///./kltndb.sqlite3"

engine = create_engine(
    DATABASE_URL,
    echo=True,        # để debug, sau tắt đi cũng được
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
)

Base = declarative_base()
