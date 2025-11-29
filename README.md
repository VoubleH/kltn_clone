# KLTN Sales Chatbot – Book Sales Assistant

## 1. Mục tiêu

Xây dựng **chatbot tư vấn bán sách** cho đồ án KLTN:

- Hỏi đáp về **thể loại, ngân sách, số trang, phong cách đọc**.
- Gợi ý **2–3 tựa** phù hợp **gu & ngân sách**.
- Ghi nhớ **gu đọc lâu dài**:
  - Thể loại thích / tránh.
  - Ngân sách quen thuộc.
- Trả lời được **FAQ của shop**:
  - Giao hàng.
  - Đổi trả.
  - COD.
  - Thanh toán, v.v.

Hệ thống gồm:

- **Backend FastAPI** (API / tools / DB).
- **RAG retriever** cho FAQ + mô tả sách dài.
- **LLM Qwen2.5 + LoRA** (tool-calling JSON).
- **Chat widget web** kiểu app Apple, nhúng vào bất kỳ website nào.

---

## 2. Kiến trúc tổng thể

### 2.1. Backend (FastAPI)

- File chính: `main.py`

- Các module quan trọng:

  - `db.py` – config SQLAlchemy:
    - `SessionLocal`
    - `Base`

  - `models.py` – định nghĩa bảng:

    - `Book`
      - `id`
      - `title`
      - `authors`
      - `genres_primary`
      - `pages`
      - `price_vnd`
      - `stock`
      - `rating_avg`
      - … (year, publisher, short_summary, created_at, updated_at)

    - `Conversation`
      - `id`
      - `shop_id`
      - `user_id`
      - `session_id`
      - `title`
      - `last_turn_index`
      - `last_summary`
      - `created_at`
      - `updated_at`

    - `Message`
      - `conversation_id`
      - `role` (`user` / `assistant`)
      - `content`
      - `turn_index`
      - `created_at`

    - `UserProfile`
      - `user_id`
      - `shop_id`
      - `budget_min`
      - `budget_max`
      - `fav_genres`
      - `fav_authors`
      - `page_min`
      - `page_max`
      - `content_avoid`

    - `UserFact`
      - `user_id`
      - `shop_id`
      - `fact_type`
      - `fact_value`
      - `confidence`
      - `created_at`

    - (optional) `Shop`, `ShopApiKey` cho **multi-shop**.

  - `sql_tools.py` – các hàm thao tác DB:

    - `find_books_by_filter(...)`
    - `get_book_detail(book_id)`
    - `compare_books(book_ids)`
    - `add_user_fact(shop_id, user_id, fact_type, fact_value, confidence)`
    - `get_user_profile(shop_id, user_id)`
    - `start_or_get_conversation(shop_id, user_id, session_id)`
    - `save_message(conversation_id, role, content)`
    - `get_last_messages(conversation_id, limit)`

  - `retriever.py`:
    - Load file `retriever_index.json`.
    - Hàm:
      ```python
      search_docs(query: str, top_k: int = 5, source_prefix: Optional[str] = None)
      ```
      - `source_prefix = "FAQ:"` hoặc `"BOOK:"` để filter.

- Static files:

  - `static/chat-widget.css` – style widget.
  - `static/chat-widget.js` – logic widget.
  - `static/demo.html` – trang demo UI.

---

### 2.2. RAG Layer

- Notebooks (Colab):

  - `generate_doc_chunks_books.ipynb`:
    - Đọc `book_master_template.csv`.
    - Chia `short_summary` thành chunk 200–400 từ.
    - Xuất `doc_chunks_books.csv`.

  - `generate_doc_chunks_faq.ipynb`:
    - Đọc file FAQ (CSV).
    - Xuất `doc_chunks_faq.csv`.

  - `generate_retriever_index.py`:
    - Nối `doc_chunks_books.csv` + `doc_chunks_faq.csv`.
    - Tạo inverted index (`term_index`).
    - Xuất `retriever_index.json`.

- Runtime:

  - `retriever.py` đọc `retriever_index.json` và cho phép:
    - `search_docs` trên toàn bộ (FAQ + BOOK chunk).
    - Filter theo:
      - `source_prefix = "FAQ:"`
      - Hoặc `source_prefix = "BOOK:"`.

---

### 2.3. LLM Backend (Qwen + LoRA)

- Model:

  - Base: `Qwen/Qwen2.5-1.5B-Instruct`
  - LoRA fine-tune: `/content/qwen-sale-lora`

- Serve LLM qua API OpenAI-compatible:

  - Server chạy ở Colab port `8001`, endpoint:
    - `POST /v1/chat/completions`

  - Sử dụng `pyngrok` để tạo public endpoint, ví dụ:

    ```text
    https://xxxxxx.ngrok-free.dev/v1
    ```

- Backend FastAPI cấu hình qua biến môi trường:

  ```bash
  LLM_BASE_URL=https://xxxxxx.ngrok-free.dev/v1
  LLM_API_KEY=        # nếu không cần auth thì để trống
  LLM_MODEL=qwen-sale-lora
