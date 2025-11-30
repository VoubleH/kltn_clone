Dưới đây là **TOÀN BỘ nội dung** (giải thích kiến trúc + mô tả hệ thống + tài liệu kỹ thuật + chia việc chi tiết + checklist bàn giao), **gộp chung trong MỘT KHỐI DUY NHẤT**.
Bạn chỉ cần **bấm copy 1 lần** là có toàn bộ README hoàn chỉnh.

---

# 📚 KLTN SALES CHATBOT – FULL README (BẢN HOÀN CHỈNH)

```markdown
# 📚 KLTN SALES CHATBOT – FULL TECHNICAL README

Dự án chatbot tư vấn bán sách cho đồ án KLTN, bao gồm:
- Backend FastAPI (API, DB, công cụ tư vấn)
- RAG (FAQ + chunks sách)
- LLM Qwen2.5 LoRA tool-calling
- Frontend chat widget nhúng website
- Hỗ trợ trí nhớ ngắn hạn & dài hạn

Tài liệu này gom TẤT CẢ vào một file duy nhất.

---

# 1. MỤC TIÊU DỰ ÁN

Chatbot cần:

### ✔ Hiểu yêu cầu tư vấn sách về:
- Thể loại
- Ngân sách
- Số trang
- Tâm trạng / phong cách đọc

### ✔ Gợi ý 2–3 sách phù hợp
Nhấn mạnh “vì sao phù hợp”.

### ✔ Ghi nhớ dài hạn:
- Thể loại thích / ghét
- Ngân sách quen dùng
- Tác giả yêu thích
- Loại nội dung tránh

### ✔ Trả lời FAQ của shop:
- Giao hàng (bao lâu, phí, khu vực)
- Đổi trả
- COD
- Thanh toán

### ✔ Hệ thống full-stack:
- Backend FastAPI
- DB + tools
- RAG retriever
- LLM tool-calling orchestrator
- UI chat widget đẹp như Apple
- Fine-tune LLM + evaluation

---

# 2. KIẾN TRÚC TỔNG THỂ

Cấu trúc thư mục đề xuất:

```

/backend
main.py
db.py
models.py
sql_tools.py
retriever.py
static/
chat-widget.js
chat-widget.css
demo.html

/notebooks
generate_doc_chunks_books.ipynb
generate_doc_chunks_faq.ipynb
generate_retriever_index.py

/docs
SYSTEM_TOOLS.md
PROMPT_TOOLS.md
ARCHITECTURE.md

/llm_server
serve_lora_model.py

````

---

# 3. BACKEND FASTAPI – CHI TIẾT HOẠT ĐỘNG

## 3.1. DB Models

### 🟦 Book
- id (book_id logic: FI001, CL003,…)
- shop_id
- title
- authors
- genres_primary
- pages
- price_vnd
- stock
- rating_avg
- short_summary

### 🟦 Conversation
- id
- shop_id
- user_id
- session_id
- last_turn_index
- last_summary

### 🟦 Message
- conversation_id
- role (user / assistant)
- content
- turn_index

### 🟦 UserProfile (trí nhớ dài hạn)
- budget_min / budget_max
- fav_genres
- fav_authors
- content_avoid
- page_min / page_max

### 🟦 UserFact (fact thô)
- fact_type (genre_like, genre_dislike,…)
- fact_value
- confidence (0–1)

---

# 4. RAG RETRIEVER

## 4.1. Offline

### Chunk sách:  
Mỗi mô tả sách → chia 200–400 từ → `doc_chunks_books.csv`.

### FAQ:  
File nguồn → `doc_chunks_faq.csv`.

### Build index:
`generate_retriever_index.py` → `retriever_index.json`.

---

## 4.2. Runtime

`search_docs(query, top_k, source_prefix)` trả:
```json
{
  "id": "FAQ_1",
  "source": "FAQ:FAQ_1",
  "title": "...",
  "chunk_text": "...",
  "score": 12.3
}
````

---

# 5. LLM BACKEND (QWEN + LORA)

* Base model: `Qwen/Qwen2.5-1.5B-Instruct`
* Fine-tune với LoRA: `/content/qwen-sale-lora`
* Serve bằng API OpenAI-compatible:

```
POST /v1/chat/completions
model: "qwen-sale-lora"
```

Expose qua ngrok:

```
LLM_BASE_URL="https://xxx.ngrok-free.dev/v1"
LLM_API_KEY=""
LLM_MODEL="qwen-sale-lora"
```

---

# 6. FRONTEND – CHAT WIDGET

## Gồm 3 file:

* `/static/chat-widget.css`
* `/static/chat-widget.js`
* `/static/demo.html`

### Widget có:

* Nút tròn góc phải 💬
* Popup chat
* Lưu session vào localStorage
* Anti-double-send
* Config API endpoint

---

# 7. DANH SÁCH API (HIỆN CÓ & PLAN)

### ✔ `/health`

### ✔ `/api/debug/find_books`

### ✔ `/api/debug/search_docs`

### ✔ `/api/chat_rule` (rule-based)

### ✔ `/api/chat_llm` (LLM thuần)

### ⏳ `/api/chat_orchestrator` (**QUAN TRỌNG – tool-calling JSON**)

---

# 8. TRÍ NHỚ NGẮN HẠN & DÀI HẠN

## 8.1. Short-term

Lấy từ bảng `Message`:

`get_last_messages(conversation_id, limit=6)`

## 8.2. Long-term

* `UserProfile` (tóm tắt)
* `UserFact` (dữ liệu thô)

LLM dùng:

* `add_user_fact`
* `get_user_profile`
  để ghi nhớ thói quen.

---

# 9. TOOL-CALLING – FORMAT JSON CHUẨN

## 9.1. find_books()

```json
{
  "tool": "find_books",
  "params": {
    "genre": "Classic",
    "budget_max": 200000,
    "page_min": 200,
    "page_max": 400,
    "limit": 3
  }
}
```

## 9.2. search_docs()

```json
{
  "tool": "search_docs",
  "params": {
    "query": "bao lâu nhận được hàng",
    "top_k": 3,
    "source_prefix": "FAQ:"
  }
}
```

## 9.3. get_book_detail()

```json
{
  "tool": "get_book_detail",
  "params": { "book_id": "NF004" }
}
```

## 9.4. compare_books()

```json
{
  "tool": "compare_books",
  "params": { "book_ids": ["FI007", "FI010"] }
}
```

## 9.5. add_user_fact()

```json
{
  "tool": "add_user_fact",
  "params": {
    "fact_type": "genre_like",
    "fact_value": "Classic",
    "confidence": 0.95
  }
}
```

## 9.6. get_user_profile()

```json
{
  "tool": "get_user_profile",
  "params": {}
}
```

---

# 10. TÍCH HỢP TRONG `/api/chat_orchestrator`

Flow:

```
User → Backend → Qwen (tool-call JSON)
          ↓
      Python tool
          ↓
   Qwen (final answer)
          ↓
      Trả về user
```

---

# 11. TOÀN BỘ CÔNG VIỆC & BÀN GIAO (HOÀNG ANH – HUY – GIANG)

Dưới đây là **bản phân chia nhiệm vụ chuẩn nhất**, đầy đủ trách nhiệm & tiêu chí đánh giá.

---

# 🧑‍💻 1. HOÀNG ANH – TECH LEAD / BACKEND / UI / ORCHESTRATOR

## 1.1. Nhiệm vụ chính

### 🔹 Kiến trúc & repo

* Tổ chức thư mục chuẩn
* Viết `README` và `ARCHITECTURE.md`

### 🔹 Backend main.py

* Hoàn thiện:

  * `/api/chat_rule`
  * `/api/chat_llm`
  * **/api/chat_orchestrator** (QUAN TRỌNG)

### 🔹 Orchestrator

* Gửi prompt → Qwen → parse JSON
* Gọi tool tương ứng
* Gửi kết quả tool cho Qwen → final answer
* Xử lý lỗi đẹp

### 🔹 UI Widget

* Chống double message
* loading indicator
* lỗi mạng
* config đổi endpoint dễ dàng

### 🔹 Environment / Lauching

* `.env.example`
* `run_dev.sh`
* Hướng dẫn kết nối ngrok

---

## 1.2. Tiêu chí đánh giá (để biết lỗi thuộc Hoàng Anh)

* API trả đúng format
* Không 500 / 422 vô lý
* Orchestrator chạy được tool-call thật
* Widget không lỗi console
* Chat không bị gửi hai lần
* Demo chạy được Chrome / Safari

---

# 🧑‍🔬 2. HUY – DATA / DB / TOOLS / RAG

## 2.1. Nhiệm vụ chính

### 🔹 Database

* Kiểm tra schema tất cả bảng
* Viết `scripts/import_data.py`
* Import full `book_master_template.csv`
* Import FAQ

### 🔹 Tool functions

* Full logic cho:

  * `find_books_by_filter`
  * `get_book_detail`
  * `compare_books`
  * `add_user_fact`
  * `get_user_profile`

### 🔹 RAG

* Tạo chunk sách / chunk FAQ
* Build `retriever_index.json`
* Tối ưu search_docs()

### 🔹 Unit tests

* pytest cho tất cả tool quan trọng

---

## 2.2. Tiêu chí đánh giá (để biết lỗi thuộc Huy)

* find_books trả sai kết quả
* compare_books thiếu dữ liệu
* search_docs trả doc không liên quan
* Tool result JSON thiếu field
* DB bị nhập sai data
* Các route /api/debug/* trả rỗng hoặc lỗi

---

# 🤖 3. GIANG – LLM / PROMPT / TOOL-CALL EVALUATION

## 3.1. Nhiệm vụ chính

### 🔹 Prompt Engineer

* Viết `SYSTEM_TOOLS.md` chuẩn nhất
* Viết `PROMPT_TOOLS.md` mô tả schema
* Ví dụ input/output mẫu cho từng tool

### 🔹 Fine-tune LoRA

* Tạo dataset tool-calling JSON
* Train Qwen LoRA
* Xuất model `/content/qwen-sale-lora`

### 🔹 Test & Evaluation

* Bộ test-case chuẩn:

  * Tư vấn sách theo thể loại + budget
  * FAQ RAG
  * So sánh sách
  * Nhớ gu đọc
* Đề xuất chỉ số:

  * Tool-format accuracy ≥ 90%
  * Tool-choice accuracy ≥ 80%
  * FAQ faithfulness ≥ 90%

---

## 3.2. Tiêu chí đánh giá (lỗi thuộc Giang)

* LLM trả JSON không parse được
* Dùng sai tool
* Bịa thông tin sách / FAQ
* Không nhớ thông tin user
* Tool-call format bị lệch schema

---

# 12. CHECKLIST BÀN GIAO CUỐI CÙNG (CỰC QUAN TRỌNG)

## ✔ Backend & UI (Hoàng Anh)

* [ ] Orchestrator chạy hoàn chỉnh
* [ ] Widget hoạt động tốt
* [ ] Tài liệu đầy đủ

## ✔ Data & RAG (Huy)

* [ ] DB đầy đủ
* [ ] RAG hoạt động đúng
* [ ] Tools chạy đủ 6 chức năng

## ✔ LLM (Giang)

* [ ] LoRA Qwen chạy được tool-call
* [ ] Bộ test-case + báo cáo accuracy

---

# 🎉 TỔNG KẾT

File README này là **tài liệu hoàn chỉnh nhất**, bao gồm:

* kiến trúc
* mô tả hệ thống
* schema
* API
* RAG
* LLM
* tool-calling
* frontend
* phân chia việc
* tiêu chí đánh giá
* checklist final

