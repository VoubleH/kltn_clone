# scripts/check_schema.py
from sqlalchemy import inspect
from db import engine

def check_schema():
    # Tạo inspector để đọc thông tin DB
    inspector = inspect(engine)

    # Lấy danh sách tất cả bảng
    tables = inspector.get_table_names()
    print("\nDANH SÁCH TẤT CẢ BẢNG TRONG DATABASE:")
    for tbl in tables:
        print(" -", tbl)

    # In chi tiết từng bảng
    print("\nCHI TIẾT CẤU TRÚC BẢNG:")
    for table in tables:
        print(f"\n Bảng: {table}")
        columns = inspector.get_columns(table)
        for col in columns:
            print(f"  ▪ {col['name']} | {col['type']} | nullable={col['nullable']}")
        
        # Primary Key
        pk = inspector.get_pk_constraint(table)
        print(" Primary Key:", pk.get("constrained_columns"))

        # Foreign Keys (nếu có)
        fks = inspector.get_foreign_keys(table)
        if fks:
            print("Foreign Keys:")
            for fk in fks:
                print("     -", fk)

if __name__ == "__main__":
    check_schema()
