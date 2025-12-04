# scripts/import_data.py
import os
import sys
import csv
from decimal import Decimal

# ---- chỉnh sys.path để import được db, models ----
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.append(BASE_DIR)

from db import SessionLocal
from models import Book, UserProfile, UserFact


DATA_DIR = os.path.join(BASE_DIR, "data")  # nơi bạn để CSV của Huy


def to_int(v):
    if v is None:
        return None
    v = str(v).strip()
    return int(v) if v else None


def import_books(csv_path: str | None = None):
    """
    Import đúng data books_master_template.csv của Huy.
    - Đặt file ở: data/books_master_template.csv
    - Hoặc truyền đường dẫn custom vào csv_path.
    """
    if csv_path is None:
        csv_path = os.path.join(DATA_DIR, "book_master_template.csv")

    db = SessionLocal()
    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                book_id = row.get("book_id") or row.get("id")
                if not book_id:
                    continue

                book = db.get(Book, book_id)
                if not book:
                    book = Book(id=book_id)

                book.title = row.get("title", "")
                book.authors = row.get("authors", "")
                book.genres_primary = row.get("genres_primary", "")
                book.pages = to_int(row.get("pages"))
                book.year = to_int(row.get("year"))
                book.publisher = row.get("publisher", "")
                book.introduction = row.get("introduction", "").strip()
                book.age_rating = to_int(row.get("age_rating"))
                book.short_summary = row.get("short_summary", "")
                book.price_vnd = to_int(row.get("price_vnd"))
                book.stocks = to_int(row.get("stocks"))
                rating = row.get("rating_avg")
                book.rating_avg = Decimal(str(rating)) if rating else None

                db.merge(book)

        db.commit()
        print(f"✅ Import books xong từ {csv_path}.")
    finally:
        db.close()


def import_user_profiles(csv_path: str | None = None, shop_id: str = "shop_books_1"):
    """
    Import đúng file user_profiles_examples.csv của Huy.
    - Đặt file ở: data/user_profiles_examples.csv
    """
    if csv_path is None:
        csv_path = os.path.join(DATA_DIR, "user_profiles_examples.csv")

    db = SessionLocal()
    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                user_id = row["user_id"]
                profile = (
                    db.query(UserProfile)
                    .filter_by(shop_id=shop_id, user_id=user_id)
                    .first()
                )
                if not profile:
                    profile = UserProfile(shop_id=shop_id, user_id=user_id)

                profile.budget_min = to_int(row.get("budget_min"))
                profile.budget_max = to_int(row.get("budget_max"))
                profile.fav_genres = row.get("fav_genres", "")
                profile.fav_authors = row.get("fav_authors", "")
                profile.page_min = to_int(row.get("page_min"))
                profile.page_max = to_int(row.get("page_max"))
                profile.content_avoid = row.get("content_avoid", "")

                db.merge(profile)

        db.commit()
        print(f"✅ Import user_profiles xong từ {csv_path}.")
    finally:
        db.close()


def import_user_facts(csv_path: str | None = None, shop_id: str = "shop_books_1"):
    """
    Import đúng file user_facts_examples.csv của Huy.
    - Đặt file ở: data/user_facts_examples.csv
    """
    if csv_path is None:
        csv_path = os.path.join(DATA_DIR, "user_facts_examples.csv")

    db = SessionLocal()
    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                fact = UserFact(
                    shop_id=shop_id,
                    user_id=row["user_id"],
                    fact_type=row["fact_type"],
                    fact_value=row["fact_value"],
                    confidence=Decimal(str(row.get("confidence") or "1.0")),
                )
                db.add(fact)

        db.commit()
        print(f"✅ Import user_facts xong từ {csv_path}.")
    finally:
        db.close()


if __name__ == "__main__":
    import_books()
    import_user_profiles()
    import_user_facts()
