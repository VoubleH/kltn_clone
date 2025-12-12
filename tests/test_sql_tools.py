import sys
import os
import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal

# 1. Thêm đường dẫn gốc vào sys.path để import được modules ở root
# (Vì file test nằm trong thư mục tests/, cần nhảy ra ngoài 1 cấp)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Book, UserProfile, UserFact

# Import các hàm cần test
from sql_tools import (
    find_books_by_filter,
    tool_get_book_detail,
    tool_compare_books,
    tool_add_user_fact,
    tool_get_user_profile
)

# --- CẤU HÌNH DB ẢO CHO TEST (IN-MEMORY SQLITE) ---
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="function")
def db_session():
    """
    Fixture này tạo ra một Database ảo trong RAM mỗi khi chạy 1 test case.
    Chạy xong test case thì xóa sạch, đảm bảo không ảnh hưởng test khác.
    """
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Tạo bảng
    Base.metadata.create_all(bind=engine)
    
    session = TestingSessionLocal()
    yield session  # Trả về session cho hàm test dùng
    
    # Dọn dẹp
    session.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def mock_session_local(db_session):
    """
    Đây là phép thuật: Đánh tráo (Mock) cái SessionLocal trong file sql_tools.py
    thành cái db_session ảo của chúng ta.
    """
    with patch("sql_tools.SessionLocal") as mock:
        mock.return_value = db_session
        yield mock

# --- CHUẨN BỊ DỮ LIỆU GIẢ (SEED DATA) ---
@pytest.fixture
def seed_data(db_session):
    # Tạo vài cuốn sách giả
    b1 = Book(id="B001", title="Sách Test 1", price_vnd=50000, pages=100, genres_primary="Fiction", rating_avg=4.5, short_summary="Summary 1", introduction="Intro 1", stock=10)
    b2 = Book(id="B002", title="Sách Test 2", price_vnd=150000, pages=300, genres_primary="Fiction", rating_avg=4.0, short_summary="Summary 2", introduction="Intro 2", stock=5)
    b3 = Book(id="B003", title="Sách Test 3", price_vnd=200000, pages=500, genres_primary="Science", rating_avg=3.5, short_summary="Summary 3", introduction="Intro 3", stock=0)
    b4 = Book(id="B004", title="Sách Test 4", price_vnd=300000, pages=200, genres_primary="Fiction", rating_avg=5.0, short_summary="Summary 4", introduction="Intro 4", stock=2)
    b5 = Book(id="B005", title="Sách Test 5", price_vnd=40000, pages=150, genres_primary="History", rating_avg=4.2, short_summary="Summary 5", introduction="Intro 5", stock=20)
    b6 = Book(id="B006", title="Sách Test 6", price_vnd=60000, pages=100, genres_primary="History", rating_avg=4.1, short_summary="Summary 6", introduction="Intro 6", stock=10)
    
    # Tạo user profile giả
    u1 = UserProfile(shop_id="shop1", user_id="user1", budget_max=100000, fav_genres="Fiction")
    
    db_session.add_all([b1, b2, b3, b4, b5, b6, u1])
    db_session.commit()

# ========================================================
# BẮT ĐẦU VIẾT TEST CASE
# ========================================================

def test_find_books_by_filter(mock_session_local, seed_data):
    """Test chức năng tìm kiếm sách"""
    
    # Case 1: Lọc theo giá < 100k
    results = find_books_by_filter(shop_id="shop1", budget_max=100000)
    assert len(results) == 3 # B001, B005, B006
    for b in results:
        assert b["price_vnd"] <= 100000

    # Case 2: Lọc theo thể loại Fiction
    results = find_books_by_filter(shop_id="shop1", genre="Fiction")
    assert len(results) == 3 # B001, B002, B004
    
    # Case 3: Test Limit (Giới hạn số lượng)
    # Trong DB có 6 cuốn, limit=2 thì chỉ được trả về 2
    results = find_books_by_filter(shop_id="shop1", limit=2)
    assert len(results) == 2

    # Case 4: Test Limit An toàn (limit âm hoặc quá lớn)
    # Limit âm -> mặc định về 5
    results = find_books_by_filter(shop_id="shop1", limit=-5)
    assert len(results) == 5 
    # Limit quá lớn (100) -> cắt về 10 (nhưng DB chỉ có 6 nên trả về 6)
    results = find_books_by_filter(shop_id="shop1", limit=100)
    assert len(results) == 6

def test_get_book_detail(mock_session_local, seed_data):
    """Test lấy chi tiết sách"""
    
    # Case 1: Sách tồn tại
    res = tool_get_book_detail("B001")
    assert res is not None
    assert res["book_id"] == "B001"
    assert res["introduction"] == "Intro 1" # Kiểm tra trường mới thêm
    
    # Case 2: Sách không tồn tại
    res = tool_get_book_detail("B999")
    assert res is None

def test_compare_books(mock_session_local, seed_data):
    """Test so sánh sách"""
    
    # Case 1: So sánh 2 sách
    ids = ["B001", "B002"]
    res = tool_compare_books(ids)
    assert len(res) == 2
    assert res[0]["book_id"] in ids
    
    # Case 2: Gửi vào danh sách rỗng
    res = tool_compare_books([])
    assert res == []
    
    # Case 3: Gửi vào quá nhiều (6 sách), hệ thống chỉ lấy 5
    ids_many = ["B001", "B002", "B003", "B004", "B005", "B006"]
    res = tool_compare_books(ids_many)
    assert len(res) == 5 # Logic safe_ids = book_ids[:5] hoạt động

def test_user_memory(mock_session_local, seed_data, db_session):
    """Test User Profile và User Fact"""
    
    # --- TEST GET PROFILE ---
    # User1 đã có trong seed_data
    prof = tool_get_user_profile("shop1", "user1")
    assert prof is not None
    assert prof["budget_max"] == 100000
    
    # User2 chưa có
    prof_new = tool_get_user_profile("shop1", "user999")
    assert prof_new is None

    # --- TEST ADD FACT (Upsert Logic) ---
    # 1. Thêm mới
    tool_add_user_fact("shop1", "user1", "genre_like", "Horror", 0.8)
    
    # Verify trong DB
    fact = db_session.query(UserFact).filter_by(fact_value="Horror").first()
    assert fact is not None
    assert float(fact.confidence) == 0.8
    
    # 2. Cập nhật (User nói lại câu đó, confidence tăng lên)
    res = tool_add_user_fact("shop1", "user1", "genre_like", "Horror", 0.99)
    assert res["status"] == "updated"
    
    # Verify DB chỉ có 1 dòng nhưng confidence thay đổi
    facts = db_session.query(UserFact).filter_by(fact_value="Horror").all()
    assert len(facts) == 1
    assert float(facts[0].confidence) == 0.99