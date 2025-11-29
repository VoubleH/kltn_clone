(function () {
    "use strict";

    console.log("[KLTN CHAT] Widget script loaded.");

    // ========= CONFIG =========
    const API_ENDPOINT = "/api/chat_rule"; // hoặc "/api/chat_llm"
    const SHOP_ID = "shop_books_1";
    const USER_ID = "web_demo_user";

    // Tạo SESSION_ID an toàn (không crash nếu crypto không tồn tại)
    function createSessionId() {
        try {
            const c = (typeof window !== "undefined" && window.crypto) || null;
            if (c && typeof c.randomUUID === "function") {
                return "session_id_" + c.randomUUID();
            }
        } catch (e) {
            console.warn("[KLTN CHAT] crypto.randomUUID not available:", e);
        }
        return "session_id_" + Math.random().toString(36).slice(2);
    }

    const SESSION_ID =
        window.localStorage.getItem("ktn_session_id") || createSessionId();

    if (!window.localStorage.getItem("ktn_session_id")) {
        window.localStorage.setItem("ktn_session_id", SESSION_ID);
    }

    console.log("[KLTN CHAT] SESSION_ID =", SESSION_ID);

    // ========= DOM TẠO WIDGET =========

    function createWidget() {
        console.log("[KLTN CHAT] Creating widget DOM...");

        // launcher
        const launcher = document.createElement("div");
        launcher.className = "ktn-chat-launcher";

        const btn = document.createElement("button");
        btn.className = "ktn-chat-button";
        btn.innerHTML =
            '<span class="ktn-chat-button-icon" aria-hidden="true">💬</span>';

        launcher.appendChild(btn);
        document.body.appendChild(launcher);

        // popup
        const popup = document.createElement("div");
        popup.className = "ktn-chat-popup";
        popup.style.display = "none";

        popup.innerHTML = `
      <div class="ktn-chat-header">
        <div class="ktn-chat-avatar">📚</div>
        <div>
          <div class="ktn-chat-header-text-main">Tư vấn sách KLTN</div>
          <div class="ktn-chat-header-text-sub">Online • sẵn sàng hỗ trợ</div>
        </div>
      </div>
      <div class="ktn-chat-body">
        <div class="ktn-chat-messages" id="ktn-messages"></div>
      </div>
      <div class="ktn-chat-input-area">
        <input
          id="ktn-input"
          class="ktn-chat-input"
          placeholder="Nhập tin nhắn..."
        />
        <button id="ktn-send" class="ktn-chat-send-btn">
          Gửi
        </button>
      </div>
      <div class="ktn-chat-status" id="ktn-status"></div>
    `;

        document.body.appendChild(popup);

        // Toggle popup
        let isOpen = false;
        btn.addEventListener("click", () => {
            isOpen = !isOpen;
            popup.style.display = isOpen ? "flex" : "none";
        });

        const inputEl = popup.querySelector("#ktn-input");
        const sendBtn = popup.querySelector("#ktn-send");
        const statusEl = popup.querySelector("#ktn-status");
        const messagesEl = popup.querySelector("#ktn-messages");

        function appendMessage(role, text) {
            const row = document.createElement("div");
            row.className = "ktn-msg-row " + (role === "user" ? "user" : "bot");
            const bubble = document.createElement("div");
            bubble.className =
                "ktn-msg-bubble " + (role === "user" ? "user" : "bot");
            bubble.innerText = text;
            row.appendChild(bubble);
            messagesEl.appendChild(row);
            messagesEl.scrollTop = messagesEl.scrollHeight;
        }

        // ==== CHỐT QUAN TRỌNG: CHẶN GỬI ĐÒN 2 ====
        let isSending = false;

        async function sendMessage() {
            const text = inputEl.value.trim();
            if (!text) return;
            if (isSending) {
                console.log("[KLTN CHAT] Prevent duplicate send.");
                return;
            }
            isSending = true;

            inputEl.value = "";
            statusEl.textContent = "";
            appendMessage("user", text);

            sendBtn.disabled = true;

            try {
                console.log("[KLTN CHAT] Sending to API:", API_ENDPOINT, {
                    shop_id: SHOP_ID,
                    user_id: USER_ID,
                    session_id: SESSION_ID,
                    message: text,
                });

                const res = await fetch(API_ENDPOINT, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({
                        shop_id: SHOP_ID,
                        user_id: USER_ID,
                        session_id: SESSION_ID,
                        message: text,
                    }),
                });

                console.log("[KLTN CHAT] Response status:", res.status);

                if (!res.ok) {
                    throw new Error("HTTP " + res.status);
                }

                const data = await res.json();
                console.log("[KLTN CHAT] Response JSON:", data);

                const reply = data.reply || "(Không có nội dung trả lời)";
                appendMessage("bot", reply);
            } catch (err) {
                console.error("Chat error:", err);
                appendMessage(
                    "bot",
                    "Xin lỗi, hiện tại kết nối đang không ổn định. Bạn thử gửi lại giúp mình nhé."
                );
                statusEl.textContent = "Lỗi kết nối tới máy chủ.";
            } finally {
                sendBtn.disabled = false;
                isSending = false;
            }
        }

        // Gửi khi bấm nút
        sendBtn.addEventListener("click", (e) => {
            e.preventDefault();
            sendMessage();
        });

        // Gửi khi Enter
        inputEl.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        // Tin nhắn chào
        appendMessage(
            "bot",
            "Chào bạn 👋 Mình là trợ lý AI tư vấn sách. Bạn có thể hỏi về thể loại, ngân sách, số trang, phong cách bạn thích..."
        );

        console.log("[KLTN CHAT] Widget created.");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", createWidget);
    } else {
        createWidget();
    }
})();
