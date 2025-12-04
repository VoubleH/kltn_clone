# check_db.py
from db import SessionLocal
from models import Book, UserProfile, UserFact

def check_data():
    db = SessionLocal()
    try:
        print("Số book:", db.query(Book).count())
        print("Số user profile:", db.query(UserProfile).count())
        print("Số user fact:", db.query(UserFact).count())

        # In thử 3 record đầu tiên của mỗi bảng
        print("\n3 sách đầu tiên:")
        for book in db.query(Book).limit(3):
            print(vars(book))

        print("\n3 user profile đầu tiên:")
        for profile in db.query(UserProfile).limit(3):
            print(vars(profile))

        print("\n3 user fact đầu tiên:")
        for fact in db.query(UserFact).limit(3):
            print(vars(fact))

    finally:
        db.close()


if __name__ == "__main__":
    check_data()
