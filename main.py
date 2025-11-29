# main.py
from typing import Optional, List, Dict, Any
import os
import re
import json

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from sql_tools import (
    find_books_by_filter,
    start_or_get_conversation,
    save_message,
    get_last_messages,
    # các tool nâng cao
    tool_get_book_detail,
    tool_compare_books,
    tool_get_user_profile,
    tool_add_user_fact,
)
from retriever import search_docs  # RAG

# ==========================================
# APP & CONFIG
# ==========================================
app = FastAPI(title="KLTN Sales Chatbot API", version="0.1.0")

# Serve static (chat-widget.css, chat-widget.js, demo.html nếu cần)
app.mount("/static", StaticFiles(directory="static"), name="static")

SHOP_ID_DEFAULT = "shop_books_1"

# ---- Config LLM (OpenAI-compatible) ----
# Ví dụ: LLM_BASE_URL="http://localhost:8001/v1"
LLM_BASE_URL = os.getenv("LLM_BASE_URL")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen-sale-lora")

SYSTEM_SALE = (
    "Bạn là chatbot tư vấn bán sách chuyên nghiệp, nói tiếng Việt thân thiện, "
    "luôn hỏi lại để làm rõ nhu cầu, ưu tiên gợi ý 2–3 lựa chọn phù hợp gu và ngân sách. "
    "Không bịa số liệu về giá, số trang, tồn kho, chính sách. Khi có dữ liệu từ tool "
    "thì phải dùng đúng dữ liệu đó."
)

SYSTEM_TOOL_CALL = """
Bạn có quyền gọi các TOOL sau:
- find_books
- search_docs
- get_book_detail
- compare_books
- add_user_fact
- get_user_profile

Nếu CẦN dữ liệu thật (sách, FAQ, profile...), bạn PHẢI trả về DUY NHẤT một object JSON:
{
  "tool": "<tên_tool>",
  "params": { ... }
}

Không được thêm bất kỳ text nào bên ngoài JSON.

Nếu KHÔNG cần gọi tool (vd: trả lời chit-chat, giải thích chung chung),
hãy trả lời trực tiếp bằng tiếng Việt, không dùng JSON.
"""

# ---- CORS (để sau này nhúng widget JS) ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # dev tạm thời, sau này hạn chế theo domain shop
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# Pydantic MODELS
# ==========================================

class FindBooksRequest(BaseModel):
    genre: Optional[str] = None
    budget_max: Optional[int] = None
    page_min: Optional[int] = None
    page_max: Optional[int] = None
    limit: int = 5


class ChatRequest(BaseModel):
    shop_id: str = SHOP_ID_DEFAULT
    user_id: str
    session_id: str
    message: str


class ChatResponse(BaseModel):
    reply: str
    used_books: Optional[List[Dict[str, Any]]] = None


# --- RAG debug models ---
class SearchDocsRequest(BaseModel):
    query: str
    top_k: int = 5
    source_prefix: Optional[str] = None  # ví dụ: "FAQ:" hoặc "BOOK:"


class SearchDocsResponseItem(BaseModel):
    id: str
    source: str
    title: str
    chunk_text: str
    score: float


# ==========================================
# HEALTHCHECK
# ==========================================
@app.get("/health")
def health():
    return {"status": "ok"}


# ==========================================
# DEBUG: FIND BOOKS DIRECTLY
# ==========================================
@app.post("/api/debug/find_books")
def api_find_books(body: FindBooksRequest):
    books = find_books_by_filter(
        shop_id=SHOP_ID_DEFAULT,
        genre=body.genre,
        budget_max=body.budget_max,
        page_min=body.page_min,
        page_max=body.page_max,
        limit=body.limit,
    )
    return {"items": books}


# ==========================================
# DEBUG: RAG SEARCH DOCS (FAQ + BOOK chunks)
# ==========================================
@app.post("/api/debug/search_docs", response_model=List[SearchDocsResponseItem])
def api_search_docs(body: SearchDocsRequest):
    """
    Debug RAG: tìm doc (FAQ + BOOK chunks) theo từ khóa / câu hỏi.
    Có thể filter theo source_prefix (vd: chỉ FAQ hoặc chỉ BOOK).
    """
    # Lấy nhiều hơn rồi lọc theo source_prefix
    raw_results = search_docs(body.query, top_k=body.top_k * 3)

    results = raw_results
    if body.source_prefix:
        results = [
            r for r in raw_results
            if r["source"].startswith(body.source_prefix)
        ]

    # chỉ trả top_k cuối cùng
    results = results[: body.top_k]
    return results


# ==========================================
# UTILS: parse đơn giản genre, budget
# ==========================================

def _simple_parse_budget(text: str) -> Optional[int]:
    """
    Rút ra số tiền đơn giản, hỗ trợ cả '200k', '150.000', 'dưới 300000'.
    Lấy SỐ LỚN NHẤT theo kiểu int (không phải string).
    """
    t = text.lower().replace("k", "000")
    t = t.replace(".", "")
    nums = re.findall(r"\d+", t)
    if not nums:
        return None
    values = [int(n) for n in nums]
    return max(values)


def _simple_detect_genre(text: str) -> Optional[str]:
    t = text.lower()

    # --- ưu tiên detect chủ đề tài chính trước ---
    if (
        "tài chính" in t
        or "quản lý tài chính" in t
        or "tài chính cá nhân" in t
        or "quản lý tiền" in t
        or "quản lý tiền bạc" in t
        or "đầu tư" in t
        or "investment" in t
        or "finance" in t
    ):
        # tuỳ bạn, có thể chọn "Self-help" cũng được
        return "Nonfiction"

    if "classic" in t or "kinh điển" in t or "văn học kinh điển" in t:
        return "Classic"
    if "fiction" in t or "tiểu thuyết" in t or "truyện chữ" in t or "truyện dài" in t:
        return "Fiction"
    if "self-help" in t or "kỹ năng sống" in t or "phát triển bản thân" in t:
        return "Self-help"
    if "nonfiction" in t or "phi hư cấu" in t:
        return "Nonfiction"
    if "trinh thám" in t:
        return "Mystery"

    return None


# ==========================================
# RULE-BASED CHAT – /api/chat & /api/chat_rule
# ==========================================

def _rule_based_reply(shop_id: str, user_msg: str) -> (str, List[Dict[str, Any]]):
    # 1) đoán genre + budget
    genre = _simple_detect_genre(user_msg)
    budget_max = _simple_parse_budget(user_msg)
    if budget_max is None:
        budget_max = 200_000  # default

    page_min = None
    page_max = None

    # 2) gọi tool SQL
    books = find_books_by_filter(
        shop_id=shop_id,
        genre=genre,
        budget_max=budget_max,
        page_min=page_min,
        page_max=page_max,
        limit=3,
    )

    # 3) soạn câu trả lời
    if not books:
        reply = (
            "Hiện tại mình chưa tìm được cuốn nào khớp tiêu chí bạn vừa nói. "
            "Bạn thử cho mình biết rõ hơn thể loại (vd: Classic, Fiction, Self-help) "
            "và tầm giá mong muốn nhé."
        )
        return reply, []

    lines = []
    lines.append("Mình gợi ý cho bạn vài tựa phù hợp nè:")

    for b in books:
        price = b.get("price_vnd")
        price_str = f"{price:,}đ".replace(",", ".") if price is not None else "N/A"
        line = (
            f"- **{b['title']}** – {b.get('authors') or 'tác giả không rõ'} "
            f"({b.get('pages')} trang, thể loại {b.get('genres_primary')}). "
            f"Giá khoảng {price_str} "
            f"[{b['book_id']}.price_vnd]"
        )
        lines.append(line)

    lines.append(
        "Bạn thấy cuốn nào hợp gu nhất? Nếu muốn mình có thể so sánh kỹ hơn giữa 2–3 cuốn."
    )
    reply = "\n".join(lines)
    return reply, books


@app.post("/api/chat", response_model=ChatResponse)
@app.post("/api/chat_rule", response_model=ChatResponse)
def api_chat_rule(body: ChatRequest):
    """
    Bản chat rule-based (không cần LLM):
    - Lưu message user vào DB.
    - Parse genre + budget từ câu hỏi.
    - Gọi find_books_by_filter.
    - Soạn câu trả lời + citation [book_id.price_vnd].
    - Lưu reply vào DB.
    """
    shop_id = body.shop_id
    user_id = body.user_id
    session_id = body.session_id
    user_msg = body.message

    # 1) conversation
    conv = start_or_get_conversation(
        shop_id=shop_id,
        user_id=user_id,
        session_id=session_id,
    )

    # 2) lưu message user
    save_message(conversation_id=conv.id, role="user", content=user_msg)

    # 3) sinh reply rule-based
    reply_text, used_books = _rule_based_reply(shop_id=shop_id, user_msg=user_msg)

    # 4) lưu reply
    save_message(conversation_id=conv.id, role="assistant", content=reply_text)

    return ChatResponse(reply=reply_text, used_books=used_books)


# ==========================================
# LLM CALL CHUNG
# ==========================================

async def call_llm(messages: List[Dict[str, str]]) -> str:
    """
    Gọi LLM OpenAI-compatible (vLLM / OpenAI / LM Studio ...).
    Cần đặt biến môi trường:
      - LLM_BASE_URL (vd: http://localhost:8001/v1)
      - LLM_API_KEY  (nếu không cần auth thì để "")
      - LLM_MODEL    (vd: qwen-sale-lora)
    """
    if not LLM_BASE_URL:
        raise RuntimeError("LLM_BASE_URL chưa được cấu hình")

    headers = {"Content-Type": "application/json"}
    if LLM_API_KEY:
        headers["Authorization"] = f"Bearer {LLM_API_KEY}"

    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "temperature": 0.4,
        "top_p": 0.9,
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{LLM_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

# ==========================================
# CHAT LLM THẲNG – /api/chat_llm
# ==========================================

@app.post("/api/chat_llm", response_model=ChatResponse)
async def api_chat_llm(body: ChatRequest):
    """
    Bản chat dùng LLM thật (không fake):
    - Lưu message user vào DB.
    - Lấy history 5-6 lượt gần nhất.
    - Gọi LLM (đã fine-tune) để tư vấn trực tiếp.
    - Lưu reply vào DB.
    (Hiện tại chưa gắn tool-calling; khi cần, bạn có thể mở rộng.)
    """
    shop_id = body.shop_id
    user_id = body.user_id
    session_id = body.session_id
    user_msg = body.message

    # 1) conversation
    conv = start_or_get_conversation(
        shop_id=shop_id,
        user_id=user_id,
        session_id=session_id,
    )

    # 2) lưu message user
    save_message(conversation_id=conv.id, role="user", content=user_msg)

    # 3) lấy history để gửi cho LLM
    history = get_last_messages(conversation_id=conv.id, limit=6)

    messages: List[Dict[str, str]] = [{"role": "system", "content": SYSTEM_SALE}]
    for h in history:
        role = "user" if h["role"] == "user" else "assistant"
        messages.append({"role": role, "content": h["content"]})

    # 4) gọi LLM
    try:
        reply_text = await call_llm(messages)
    except Exception as e:
        print("❌ LLM error:", e)
        raise HTTPException(status_code=500, detail="LLM backend error")

    used_books: List[Dict[str, Any]] = []  # sẽ gắn tool-calling sau

    # 5) lưu reply
    save_message(conversation_id=conv.id, role="assistant", content=reply_text)

    return ChatResponse(reply=reply_text, used_books=used_books)


# ==========================================
# ORCHESTRATOR: TOOL-CALLING – /api/chat_orchestrator
# ==========================================

def _clean_json_block(s: str) -> str:
    """
    Xử lý trường hợp model trả về dạng ```json ... ```.
    """
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z0-9]*\s*", "", s)
        s = re.sub(r"```$", "", s.strip())
    return s.strip()


def _run_tool_for_orchestrator(shop_id: str, user_id: str, tool_spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Nhận tool_spec dạng {"tool": "...", "params": {...}}
    → Gọi đúng hàm Python backend và trả:
    {
      "tool": "...",
      "params": {...},
      "result": <bất kỳ>
    }
    """
    name = (tool_spec.get("tool") or "").strip()
    params = tool_spec.get("params") or {}
    result: Any = None

    if name == "find_books":
        result = find_books_by_filter(
            shop_id=shop_id,
            genre=params.get("genre"),
            budget_max=params.get("budget_max"),
            page_min=params.get("page_min"),
            page_max=params.get("page_max"),
            limit=params.get("limit", 3),
        )

    elif name == "search_docs":
        q = params.get("query") or ""
        top_k = params.get("top_k", 5)
        source_prefix = params.get("source_prefix")
        result = search_docs(q, top_k=top_k, source_prefix=source_prefix)

    elif name == "get_book_detail":
        book_id = params.get("book_id")
        result = tool_get_book_detail(book_id)

    elif name == "compare_books":
        book_ids = params.get("book_ids") or []
        result = tool_compare_books(book_ids)

    elif name == "add_user_fact":
        result = tool_add_user_fact(
            shop_id=shop_id,
            user_id=user_id,
            fact_type=params.get("fact_type", ""),
            fact_value=params.get("fact_value", ""),
            confidence=params.get("confidence", 1.0),
        )

    elif name == "get_user_profile":
        result = tool_get_user_profile(shop_id=shop_id, user_id=user_id)

    else:
        raise ValueError(f"Unknown tool: {name}")

    return {"tool": name, "params": params, "result": result}


@app.post("/api/chat_orchestrator", response_model=ChatResponse)
async def api_chat_orchestrator(body: ChatRequest):
    """
    Flow:
    - Lưu message user
    - Gọi LLM phase 1: quyết định dùng tool hay trả lời luôn
    - Nếu có tool: chạy tool, lưu message role='tool', gọi LLM phase 2 để trả lời final
    """
    shop_id = body.shop_id
    user_id = body.user_id
    session_id = body.session_id
    user_msg = body.message

    # 1) conversation + lưu user message
    conv = start_or_get_conversation(
        shop_id=shop_id,
        user_id=user_id,
        session_id=session_id,
        title_hint="Chat tư vấn sách (orchestrator)",
    )
    save_message(conversation_id=conv.id, role="user", content=user_msg)

    # 2) lấy history để LLM hiểu ngữ cảnh
    history = get_last_messages(conversation_id=conv.id, limit=8)
    messages_decision: List[Dict[str, str]] = [
        {
            "role": "system",
            "content": SYSTEM_SALE + "\n\n" + SYSTEM_TOOL_CALL,
        }
    ]
    for h in history:
        role = h["role"]
        if role not in ("user", "assistant"):
            # role 'tool' sẽ chỉ xuất hiện ở phase 2, nên ở đây bỏ qua hoặc map đơn giản
            role = "user" if role == "user" else "assistant"
        messages_decision.append({"role": role, "content": h["content"]})

    # 3) Gọi LLM phase 1: quyết định tool
    try:
        raw = await call_llm(messages_decision)
    except Exception as e:
        print("❌ LLM error (phase 1):", e)
        raise HTTPException(status_code=500, detail="LLM backend error (phase 1)")

    raw = raw.strip()
    tool_spec = None
    used_books: List[Dict[str, Any]] = []

    # 4) Thử parse JSON để xem có tool hay không
    try:
        cleaned = _clean_json_block(raw)
        obj = json.loads(cleaned)
        if isinstance(obj, dict) and "tool" in obj:
            tool_spec = obj
    except Exception:
        tool_spec = None

    # 5) Nếu KHÔNG có tool → raw chính là câu trả lời final
    if not tool_spec:
        reply_text = raw
        save_message(conversation_id=conv.id, role="assistant", content=reply_text)
        return ChatResponse(reply=reply_text, used_books=used_books)

    # 6) Có tool → chạy backend
    try:
        tool_payload = _run_tool_for_orchestrator(
            shop_id=shop_id,
            user_id=user_id,
            tool_spec=tool_spec,
        )
    except Exception as e:
        print("❌ Tool error:", e)
        raise HTTPException(status_code=500, detail=f"Tool error: {e}")

    # Lưu message role="tool" (để LLM phase 2 đọc lại)
    tool_msg_json = json.dumps(tool_payload, ensure_ascii=False)
    save_message(conversation_id=conv.id, role="tool", content=tool_msg_json)

    # Xác định used_books (nếu có)
    name = tool_payload["tool"]
    result = tool_payload["result"]
    if name in ("find_books", "compare_books") and isinstance(result, list):
        used_books = result
    elif name == "get_book_detail" and isinstance(result, dict):
        used_books = [result]

    # 7) Phase 2: nhờ LLM soạn câu trả lời final dựa trên kết quả TOOL
    history2 = get_last_messages(conversation_id=conv.id, limit=10)
    messages_final: List[Dict[str, str]] = [
        {
            "role": "system",
            "content": SYSTEM_SALE
            + "\n\nBạn vừa gọi một TOOL. Các message role=tool bên dưới chứa JSON kết quả. "
              "Hãy dùng dữ liệu đó để trả lời khách bằng tiếng Việt thân thiện, kèm citation "
              "đúng chuẩn (vd: [CL002.price_vnd], [FAQ_1]).",
        }
    ]
    for h in history2:
        role = h["role"]
        if role not in ("user", "assistant", "tool"):
            role = "user" if role == "user" else "assistant"
        messages_final.append({"role": role, "content": h["content"]})

    try:
        final_reply = await call_llm(messages_final)
    except Exception as e:
        print("❌ LLM error (phase 2):", e)
        raise HTTPException(status_code=500, detail="LLM backend error (phase 2)")

    final_reply = final_reply.strip()
    save_message(conversation_id=conv.id, role="assistant", content=final_reply)

    return ChatResponse(reply=final_reply, used_books=used_books)
