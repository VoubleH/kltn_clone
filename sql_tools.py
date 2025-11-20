# sql_tools.py
from typing import List, Optional, Dict, Any
from sqlalchemy import and_
from sqlalchemy.orm import Session

from db import SessionLocal
from models import Book, UserProfile, UserFact, Conversation, Message


# ---------- BOOK TOOLS ----------

def find_books_by_filter(
    shop_id: str,
    genre: Optional[str] = None,
    budget_max: Optional[int] = None,
    page_min: Optional[int] = None,
    page_max: Optional[int] = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """
    Lọc sách theo thể loại / ngân sách / số trang – dùng cho tool find_products.
    (tạm thời chưa dùng shop_id cho books, vì bạn mới có 1 shop sách.
     Sau này thêm cột shop_id vào books thì filter thêm.)
    """
    db: Session = SessionLocal()
    try:
        q = db.query(Book)

        if genre:
            q = q.filter(Book.genres_primary.ilike(f"%{genre}%"))

        if budget_max is not None:
            q = q.filter(Book.price_vnd <= budget_max)

        if page_min is not None:
            q = q.filter(Book.pages >= page_min)
        if page_max is not None:
            q = q.filter(Book.pages <= page_max)

        q = q.order_by(Book.rating_avg.desc().nullslast(), Book.price_vnd.asc())
        books = q.limit(limit).all()

        return [
            {
                "book_id": b.id,
                "title": b.title,
                "authors": b.authors,
                "genres_primary": b.genres_primary,
                "pages": b.pages,
                "price_vnd": b.price_vnd,
                "stock": b.stock,
                "rating_avg": float(b.rating_avg) if b.rating_avg is not None else None,
            }
            for b in books
        ]
    finally:
        db.close()


def get_book_by_id(book_id: str) -> Optional[Dict[str, Any]]:
    db = SessionLocal()
    try:
        b = db.get(Book, book_id)
        if not b:
            return None
        return {
            "book_id": b.id,
            "title": b.title,
            "authors": b.authors,
            "genres_primary": b.genres_primary,
            "pages": b.pages,
            "price_vnd": b.price_vnd,
            "stock": b.stock,
            "rating_avg": float(b.rating_avg) if b.rating_avg is not None else None,
            "short_summary": b.short_summary,
        }
    finally:
        db.close()


# ---------- USER PROFILE & FACTS ----------

def get_or_create_user_profile(shop_id: str, user_id: str) -> UserProfile:
    db = SessionLocal()
    try:
        profile = (
            db.query(UserProfile)
            .filter_by(shop_id=shop_id, user_id=user_id)
            .first()
        )
        if not profile:
            profile = UserProfile(shop_id=shop_id, user_id=user_id)
            db.add(profile)
            db.commit()
            db.refresh(profile)
        return profile
    finally:
        db.close()


def upsert_user_profile(
    shop_id: str,
    user_id: str,
    budget_min: Optional[int] = None,
    budget_max: Optional[int] = None,
    fav_genres: Optional[str] = None,
    fav_authors: Optional[str] = None,
    page_min: Optional[int] = None,
    page_max: Optional[int] = None,
    content_avoid: Optional[str] = None,
):
    db = SessionLocal()
    try:
        profile = (
            db.query(UserProfile)
            .filter_by(shop_id=shop_id, user_id=user_id)
            .first()
        )
        if not profile:
            profile = UserProfile(shop_id=shop_id, user_id=user_id)

        if budget_min is not None:
            profile.budget_min = budget_min
        if budget_max is not None:
            profile.budget_max = budget_max
        if fav_genres is not None:
            profile.fav_genres = fav_genres
        if fav_authors is not None:
            profile.fav_authors = fav_authors
        if page_min is not None:
            profile.page_min = page_min
        if page_max is not None:
            profile.page_max = page_max
        if content_avoid is not None:
            profile.content_avoid = content_avoid

        db.merge(profile)
        db.commit()
        print("✅ Saved user_profile", shop_id, user_id)
    finally:
        db.close()


def add_user_fact(
    shop_id: str,
    user_id: str,
    fact_type: str,
    fact_value: str,
    confidence: float = 1.0,
):
    db = SessionLocal()
    try:
        fact = UserFact(
            shop_id=shop_id,
            user_id=user_id,
            fact_type=fact_type,
            fact_value=fact_value,
            confidence=confidence,
        )
        db.add(fact)
        db.commit()
        print("✅ Added user_fact", shop_id, user_id, fact_type, fact_value)
    finally:
        db.close()


def get_user_facts(shop_id: str, user_id: str) -> List[Dict[str, Any]]:
    db = SessionLocal()
    try:
        facts = (
            db.query(UserFact)
            .filter_by(shop_id=shop_id, user_id=user_id)
            .all()
        )
        return [
            {
                "fact_type": f.fact_type,
                "fact_value": f.fact_value,
                "confidence": float(f.confidence),
            }
            for f in facts
        ]
    finally:
        db.close()


# ---------- CONVERSATION TOOLS (history) ----------

def start_or_get_conversation(shop_id: str, user_id: Optional[str], session_id: str) -> Conversation:
    db = SessionLocal()
    try:
        conv = (
            db.query(Conversation)
            .filter_by(shop_id=shop_id, session_id=session_id)
            .first()
        )
        if not conv:
            conv = Conversation(
                shop_id=shop_id,
                user_id=user_id,
                session_id=session_id,
            )
            db.add(conv)
            db.commit()
            db.refresh(conv)
        return conv
    finally:
        db.close()


def add_message(conversation_id: int, role: str, content: str, turn_index: int):
    db = SessionLocal()
    try:
        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            turn_index=turn_index,
        )
        db.add(msg)
        db.commit()
    finally:
        db.close()


def get_last_messages(conversation_id: int, limit: int = 5) -> List[Dict[str, Any]]:
    db = SessionLocal()
    try:
        msgs = (
            db.query(Message)
            .filter_by(conversation_id=conversation_id)
            .order_by(Message.id.desc())
            .limit(limit)
            .all()
        )
        # đảo lại cho đúng thứ tự cũ
        msgs = list(reversed(msgs))
        return [
            {"role": m.role, "content": m.content, "turn_index": m.turn_index}
            for m in msgs
        ]
    finally:
        db.close()
