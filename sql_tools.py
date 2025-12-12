# sql_tools.py
from __future__ import annotations

from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session

from db import SessionLocal
from models import Book, UserProfile, UserFact, Conversation, Message


# --------------------------------------------------------
# BOOK TOOLS
# --------------------------------------------------------

def find_books_by_filter(
    shop_id: str,
    genre: Optional[str] = None,
    budget_max: Optional[int] = None,
    page_min: Optional[int] = None,
    page_max: Optional[int] = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """
    Tool: find_books
    Mục đích: Tìm sách theo tiêu chí lọc (thể loại, giá, số trang).
    """
    db: Session = SessionLocal()
    try:
        q = db.query(Book)
        
        if shop_id:
            q = q.filter(Book.shop_id == shop_id)

        # 1. Filter theo thể loại 
        if genre:
            q = q.filter(Book.genres_primary.ilike(f"%{genre}%"))

        # 2. Filter theo ngân sách (chỉ lọc nếu có giá trị hợp lệ)
        if budget_max is not None and budget_max > 0:
            q = q.filter(Book.price_vnd <= budget_max)

        # 3. Filter theo số trang
        if page_min is not None and page_min > 0:
            q = q.filter(Book.pages >= page_min)
        if page_max is not None and page_max > 0:
            q = q.filter(Book.pages <= page_max)

        # 4. Sắp xếp: Ưu tiên Rating cao, sau đó đến Giá thấp
        q = q.order_by(Book.rating_avg.desc(), Book.price_vnd.asc())

        # 5. Logic giới hạn an toàn, thêm chặn trên phòng trường hợp user đưa ttin limit mơ hồ, LLM bị hallucination
        # Nếu limit <= 0 hoặc None -> Mặc định 5
        # Nếu limit > 10 -> Cắt xuống 10 để tránh tràn Context Window của LLM
        if not limit or limit <= 0:
            actual_limit = 5
        else:
            actual_limit = min(limit, 10)

        books = q.limit(actual_limit).all()

        return [
            {
                "book_id": b.id,
                "title": b.title,
                "authors": b.authors,
                "genres": b.genres_primary,
                "pages": b.pages,
                "price_vnd": b.price_vnd,
                "stock": b.stock,
                "rating_avg": float(b.rating_avg) if b.rating_avg is not None else None,
                "summary": b.short_summary,
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


# --------------------------------------------------------
# USER PROFILE & FACTS
# --------------------------------------------------------

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


# --------------------------------------------------------
# CONVERSATION & MESSAGE TOOLS
# --------------------------------------------------------

def start_or_get_conversation(
    shop_id: str,
    user_id: Optional[str],
    session_id: str,
    title_hint: Optional[str] = None,
) -> Conversation:
    """
    Lấy conversation theo (shop_id, session_id). Nếu chưa có thì tạo mới.
    """
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
                title=title_hint,
                last_summary=None,
                last_turn_index=0,
            )
            db.add(conv)
            db.commit()
            db.refresh(conv)
        return conv
    finally:
        db.close()


def save_message(
    conversation_id: int,
    role: str,
    content: str,
) -> Message:
    """
    Lưu 1 message vào bảng messages và cập nhật last_turn_index trong conversations.
    """
    db = SessionLocal()
    try:
        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if conv is None:
            raise ValueError(f"Conversation {conversation_id} not found")

        next_turn = (conv.last_turn_index or 0) + 1

        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            turn_index=next_turn,
        )
        db.add(msg)

        conv.last_turn_index = next_turn
        conv.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(msg)
        return msg
    finally:
        db.close()


def get_last_messages(conversation_id: int, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Lấy lại các message gần nhất (role + content + turn_index) theo thứ tự thời gian.
    """
    db = SessionLocal()
    try:
        msgs = (
            db.query(Message)
            .filter_by(conversation_id=conversation_id)
            .order_by(Message.turn_index.desc())
            .limit(limit)
            .all()
        )
        msgs = list(reversed(msgs))
        return [
            {"role": m.role, "content": m.content, "turn_index": m.turn_index}
            for m in msgs
        ]
    finally:
        db.close()

# ========================================================
# HIGH-LEVEL TOOLS CHO LLM / ORCHESTRATOR
# ========================================================

def tool_get_book_detail(book_id: str) -> Optional[Dict[str, Any]]:
    """
    Tool: get_book_detail
    Mục đích: Lấy thông tin chi tiết đầy đủ của 1 cuốn sách.
    """
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
            "publisher": b.publisher,
            "year": b.year,
            # Lấy thêm introduction để LLM có thể trả lời sâu về nội dung
            "introduction": b.introduction, 
        }
    finally:
        db.close()


def tool_compare_books(book_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Tool: compare_books
    Mục đích: Lấy thông tin tóm tắt của nhiều sách để so sánh.
    """
    if not book_ids:
        return []

    db = SessionLocal()
    try:
        # AN TOÀN: nếu user ycau so sánh quá nhiều sách 1 lúc (10, 20 cuốn trở lên) thì cũng cắt input về ngưỡng min, có thể đưa ra note 
        # khi ng dùng ycau so sánh quá nhiều sách kiểu: để đưa ra kqua tốt nhất thì sẽ chỉ so sánh 5 cuốn đầu tiên hoặc bảo ng dùng chọn 5 cuốn để so sánh thôi
        safe_ids = book_ids[:5]
        
        books = (
            db.query(Book)
            .filter(Book.id.in_(safe_ids))
            .all()
        )
        
        result: List[Dict[str, Any]] = []
        for b in books:
            result.append(
                {
                    "book_id": b.id,
                    "title": b.title,
                    "authors": b.authors,
                    "genres_primary": b.genres_primary,
                    "pages": b.pages,
                    "price_vnd": b.price_vnd,
                    "rating_avg": float(b.rating_avg) if b.rating_avg is not None else None,
                }
            )
        return result
    finally:
        db.close()


def tool_get_user_profile(shop_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """
    Tool: get_user_profile
    Mục đích: Lấy lại profile user (ngân sách, fav_genres, tránh nội dung,...).
    """
    db = SessionLocal()
    try:
        prof = (
            db.query(UserProfile)
            .filter_by(shop_id=shop_id, user_id=user_id)
            .first()
        )
        if not prof:
            return None

        return {
            "user_id": prof.user_id,
            "shop_id": prof.shop_id,
            "budget_min": prof.budget_min,
            "budget_max": prof.budget_max,
            "fav_genres": prof.fav_genres,
            "fav_authors": prof.fav_authors,
            "page_min": prof.page_min,
            "page_max": prof.page_max,
            "content_avoid": prof.content_avoid,
        }
    finally:
        db.close()


def tool_add_user_fact(
    shop_id: str,
    user_id: str,
    fact_type: str,
    fact_value: str,
    confidence: float = 1.0,
) -> Dict[str, Any]:
    """
    Tool: add_user_fact
    Mục đích: Ghi nhớ thông tin mới về user vào DB (Upsert).
    """
    db = SessionLocal()
    try:
        # 1. Kiểm tra xem fact này đã tồn tại chưa (tránh spam/duplicate)
        existing_fact = db.query(UserFact).filter_by(
            shop_id=shop_id, 
            user_id=user_id, 
            fact_type=fact_type, 
            fact_value=fact_value
        ).first()

        if existing_fact:
            # Nếu đã có -> Update confidence và thời gian mới nhất
            existing_fact.confidence = confidence
            existing_fact.created_at = datetime.utcnow()
            db.commit()
            return {"status": "updated", "msg": f"Updated fact: {fact_value}"}

        # 2. Nếu chưa có -> Insert mới
        fact = UserFact(
            shop_id=shop_id,
            user_id=user_id,
            fact_type=fact_type,
            fact_value=fact_value,
            confidence=confidence,
        )
        db.add(fact)
        db.commit()
        return {"status": "added", "msg": f"Remembered: {fact_value}"}
        
    except Exception as e:
        db.rollback()
        return {"status": "error", "msg": str(e)}
    finally:
        db.close()