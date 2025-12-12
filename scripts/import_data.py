# scripts/import_data.py
import os
import sys
import csv
from decimal import Decimal

# ---- chỉnh sys.path để import được db, models ----
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.append(BASE_DIR)

from db import SessionLocal
from models import Book, UserProfile, UserFact, FAQ


DATA_DIR = os.path.join(BASE_DIR, "data")  # nơi bạn để CSV của Huy


def to_int(v):
    if v is None:
        return None
    v = str(v).strip()
    return int(v) if v else None


def import_books(csv_path: str | None = None):
    if csv_path is None:
        csv_path = os.path.join(DATA_DIR, "book_master_template.csv")

    if not os.path.exists(csv_path):
        print(f"❌ Không tìm thấy file: {csv_path}")
        return

    db = SessionLocal()
    try:
        # encoding='utf-8-sig' để xử lý file CSV từ Excel (tránh lỗi ký tự lạ đầu file)
        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            
            count = 0
            for row in reader:
                # 1. Lấy ID và xử lý khoảng trắng
                book_id = (row.get("id") or row.get("book_id") or "").strip()
                if not book_id:
                    continue

                # 2. Tìm hoặc tạo mới Book
                book = db.get(Book, book_id)
                if not book:
                    book = Book(id=book_id)

                # 3. Map dữ liệu văn bản
                book.title = row.get("title", "").strip()
                book.authors = row.get("authors", "").strip()
                book.genres_primary = row.get("genres_primary", "").strip()
                book.publisher = row.get("publisher", "").strip()
                book.short_summary = row.get("short_summary", "").strip()
                
                # Các cột mới (nếu bạn đã thêm vào models.py)
                book.introduction = row.get("introduction", "").strip()
                book.age_rating = to_int(row.get("age_rating"))

                # 4. Map dữ liệu số
                book.pages = to_int(row.get("pages"))
                book.year = to_int(row.get("year"))
                book.price_vnd = to_int(row.get("price_vnd"))
                
                # QUAN TRỌNG: Cột trong CSV là 'stocks', trong Model là 'stock'
                book.stock = to_int(row.get("stocks")) 

                # 5. Xử lý Rating
                rating = row.get("rating_avg")
                if rating:
                    try:
                        book.rating_avg = Decimal(str(rating))
                    except:
                        book.rating_avg = None
                
                # --- Đã bỏ phần import created_at, updated_at ---
                # Database sẽ tự động điền giờ hiện tại (datetime.utcnow)

                db.merge(book)
                count += 1

        db.commit()
        print(f"✅ Import books xong từ {csv_path}. Đã xử lý {count} dòng.")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Lỗi khi import books: {e}")
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
        print(f"Import user_facts xong từ {csv_path}.")
    finally:
        db.close()

def import_faqs(csv_path: str | None = None):
    """
    Import file chunk_faq.csv vào bảng faqs
    """
    if csv_path is None:
        csv_path = os.path.join(DATA_DIR, "doc_trunks_faq.csv")

    if not os.path.exists(csv_path):
        print(f"Không tìm thấy file: {csv_path}")
        return

    db = SessionLocal()
    try:
        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                # Lấy ID
                faq_id = row.get("id", "").strip()
                if not faq_id:
                    continue

                # Kiểm tra xem FAQ đã có chưa để update
                faq = db.get(FAQ, faq_id)
                if not faq:
                    faq = FAQ(id=faq_id)

                # Map dữ liệu
                faq.title = row.get("title", "").strip()
                # Cột trong CSV là 'chunk_text', map vào model 'text'
                faq.text = row.get("chunk_text", "").strip()

                db.merge(faq)
                count += 1

        db.commit()
        print(f"Import FAQs xong từ {csv_path}. Đã xử lý {count} dòng.")
    except Exception as e:
        db.rollback()
        print(f"Lỗi khi import FAQs: {e}")
    finally:
        db.close()
        
if __name__ == "__main__":
    import_books()
    import_user_profiles()
    import_user_facts()
    import_faqs()
