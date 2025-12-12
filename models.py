# models.py
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Numeric,
    UniqueConstraint,
    ForeignKey,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Book(Base):
    __tablename__ = "books"
    id = Column(String(32), primary_key=True, index=True)
    title = Column(Text, nullable=False)
    authors = Column(Text)
    genres_primary = Column(String(64))
    pages = Column(Integer)
    year = Column(Integer)
    publisher = Column(Text)
    age_rating = Column(Integer, nullable=True) 
    introduction = Column(Text, nullable=True)
    short_summary = Column(Text)
    price_vnd = Column(Integer)
    stock = Column(Integer)
    rating_avg = Column(Numeric(4, 2))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class UserProfile(Base):
    __tablename__ = "user_profiles"
    id = Column(Integer, primary_key=True, index=True)
    shop_id = Column(String(64), nullable=False)
    user_id = Column(String(64), nullable=False)

    budget_min = Column(Integer)
    budget_max = Column(Integer)
    fav_genres = Column(Text)
    fav_authors = Column(Text)
    page_min = Column(Integer)
    page_max = Column(Integer)
    content_avoid = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("shop_id", "user_id", name="uq_shop_user"),
    )

class UserFact(Base):
    __tablename__ = "user_facts"
    id = Column(Integer, primary_key=True, index=True)
    shop_id = Column(String(64), nullable=False)
    user_id = Column(String(64), nullable=False)
    fact_type = Column(Text, nullable=False)
    fact_value = Column(Text, nullable=False)
    confidence = Column(Numeric(3, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# ---------------- NEW: Lưu history chat ----------------

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    shop_id = Column(String(64), nullable=False)
    user_id = Column(String(64), nullable=True)   # khách vãng lai có thể null
    session_id = Column(String(128), nullable=False)  # từ frontend
    title = Column(Text, nullable=True)

    # tóm tắt ngắn của cuộc trò chuyện, dùng cho memory dài hạn
    last_summary = Column(Text, nullable=True)
    last_turn_index = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    messages = relationship("Message", back_populates="conversation")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)

    # "user" hoặc "assistant"
    role = Column(String(16), nullable=False)
    content = Column(Text, nullable=False)

    turn_index = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")

class FAQ(Base):
    __tablename__ = "faqs"
    id = Column(String(32), primary_key=True, index=True)
    title = Column(Text, nullable=False)
    text = Column(Text, nullable=False) # Map từ cột 'chunk_text' trong CSV
    created_at = Column(DateTime, default=datetime.utcnow)