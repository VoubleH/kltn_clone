# scripts/create_db.py
import os
import sys

# Thêm thư mục gốc vào sys.path để import được các module
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.append(BASE_DIR)

from db import engine
# QUAN TRỌNG: Phải import tất cả các Models thì create_all mới nhận diện được để tạo bảng
from models import Base, Book, UserProfile, UserFact, Conversation, Message

def create_db():
    print("🔄 Đang tạo bảng trong database...")
    # Lệnh này sẽ tạo tất cả các bảng được define trong các model đã import
    Base.metadata.create_all(bind=engine)
    print("✅ Đã tạo xong các bảng: Book, UserProfile, UserFact, Conversation, Message.")

if __name__ == "__main__":
    create_db()