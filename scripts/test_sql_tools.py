# test_sql_tools.py
from sql_tools import (
    find_books_by_filter,
    get_book_by_id,
    get_or_create_user_profile,
    upsert_user_profile,
    add_user_fact,
    get_user_facts,
    start_or_get_conversation,
    add_message,
    get_last_messages,
)

def main():
    # 1) Test lọc sách
    print("=== FIND BOOKS ===")
    books = find_books_by_filter(
        shop_id="shop_books_1",
        genre="Classic",
        budget_max=200000,
        page_min=200,
        page_max=800,
        limit=3,
    )
    for b in books:
        print(b)

    # 2) Test profile
    print("\n=== USER PROFILE ===")
    profile = get_or_create_user_profile("shop_books_1", "user_001")
    print("Profile:", profile.user_id, profile.budget_min, profile.budget_max)

    upsert_user_profile(
        "shop_books_1",
        "user_004",
        budget_min=100000,
        budget_max=150000,
        fav_genres="Fantasy,Classic",
    )

    # 3) Test facts
    print("\n=== USER FACTS ===")
    add_user_fact("shop_books_1", "user_004", "genre_like", "Fantasy", 0.9)
    facts = get_user_facts("shop_books_1", "user_004")
    print(facts)

    # 4) Test conversation
    print("\n=== CONVERSATION ===")
    conv = start_or_get_conversation("shop_books_1", "user_004", "session_abc123")
    add_message(conv.id, "user", "Mình thích fantasy dưới 150k.", turn_index=1)
    add_message(conv.id, "assistant", "Ok, mình gợi ý bạn vài cuốn nè...", turn_index=2)

    last_msgs = get_last_messages(conv.id, limit=5)
    for m in last_msgs:
        print(m)

if __name__ == "__main__":
    main()
