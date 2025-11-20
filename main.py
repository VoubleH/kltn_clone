# main.py
from typing import Optional, List
from fastapi import FastAPI
from pydantic import BaseModel

from sql_tools import (
    find_books_by_filter,
    get_or_create_user_profile,
    start_or_get_conversation,
    save_message,
    get_last_messages,
)

app = FastAPI(title="KLTN Sales Chatbot API")

SHOP_ID_DEFAULT = "shop_books_1"


# --------- MODELS (request/response) ---------
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
    used_books: Optional[List[dict]] = None


# --------- HEALTHCHECK ---------
@app.get("/health")
def health():
    return {"status": "ok"}


# --------- DEBUG: FIND BOOKS DIRECTLY ---------
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


# --------- SIMPLE CHAT (FAKE LLM) ---------
def _simple_parse_int(text: str) -> Optional[int]:
    """Rút số tiền rất đơn giản từ câu (ví dụ: 'tầm 150k', 'dưới 200000')."""
    import re

    # bắt số liền nhau
    nums = re.findall(r"\d+", text.replace(".", ""))
    if not nums:
        return None
    # lấy số lớn nhất trong câu
    return int(max(nums))


def _simple_detect_genre(text: str) -> Optional[str]:
    text_l = text.lower()
    # có thể bổ sung thêm mapping cho các thể loại khác
    if "classic" in text_l or "kinh điển" in text_l:
        return "Classic"
    if "fiction" in text_l or "tiểu thuyết" in text_l:
        return "Fiction"
    if "self-help" in text_l or "kỹ năng sống" in text_l or "phát triển bản thân" in text_l:
        return "Self-help"
    if "nonfiction" in text_l or "phi hư cấu" in text_l:
        return "Nonfiction"
    # fallback: None
    return None


@app.post("/api/chat", response_model=ChatResponse)
def api_chat(body: ChatRequest):
    """
    Bản chat đơn giản:
    - Lưu message user vào DB.
    - Parse genre + budget từ câu hỏi.
    - Gọi find_books_by_filter.
    - Tự format câu trả lời + citation [book_id.price_vnd].
    - Lưu reply vào DB.
    """

    shop_id = body.shop_id
    user_id = body.user_id
    session_id = body.session_id
    user_msg = body.message

    # 1) Mở / tạo conversation
    conv = start_or_get_conversation(
        shop_id=shop_id,
        user_id=user_id,
        session_id=session_id,
        title_hint="Chat tư vấn sách",
    )

    # 2) Lưu message của user
    save_message(
        conversation_id=conv["id"],
        role="user",
        content=user_msg,
        metadata=None,
    )

    # 3) Lấy history gần đây (để sau này build prompt cho LLM)
    last_turns = get_last_messages(conversation_id=conv["id"], limit=6)

    # 4) "Fake LLM": tự suy luận genre + budget + pages
    genre = _simple_detect_genre(user_msg)
    budget_max = _simple_parse_int(user_msg)

    # Đặt mặc định nếu không parse được
    if budget_max is None:
        budget_max = 200_000
    page_min = None
    page_max = None

    # 5) Gọi tool find_books_by_filter
    books = find_books_by_filter(
        shop_id=shop_id,
        genre=genre,
        budget_max=budget_max,
        page_min=page_min,
        page_max=page_max,
        limit=3,
    )

    # 6) Soạn câu trả lời (giả lập LLM)
    if not books:
        reply_text = (
            "Hiện tại mình chưa tìm được cuốn nào khớp tiêu chí bạn nói. "
            "Bạn thử cho mình biết thể loại cụ thể hơn (vd: Classic, Fiction, Self-help) "
            "hoặc tầm giá bạn muốn nhé?"
        )
    else:
        lines = []
        lines.append("Mình gợi ý bạn vài tựa phù hợp nè:")
        for b in books:
            line = (
                f"- **{b['title']}** của {b.get('authors') or 'N/A'} "
                f"(khoảng {b.get('pages')} trang, thể loại {b.get('genres_primary')}). "
                f"Giá ~ {b.get('price_vnd')}đ "
                f"[{b['id']}.price_vnd]"
            )
            lines.append(line)
        lines.append(
            "Bạn thấy cuốn nào hợp gu nhất, hoặc muốn mình so sánh kỹ hơn giữa 2–3 cuốn không?"
        )
        reply_text = "\n".join(lines)

    # 7) Lưu reply vào DB
    save_message(
        conversation_id=conv["id"],
        role="assistant",
        content=reply_text,
        metadata={"used_books": [b["id"] for b in books]},
    )

    return ChatResponse(reply=reply_text, used_books=books)
