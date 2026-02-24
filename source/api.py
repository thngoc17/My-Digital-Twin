import telebot
from openai import OpenAI
import time
import os
import sys

# --- THƯ VIỆN RAG (Mới thêm) ---
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# --- CẤU HÌNH ---
# LƯU Ý: Không để lộ Token thật khi up lên Github
TELEGRAM_TOKEN = "[YOUR_TELEGRAM_TOKEN_HERE]"
# LƯU Ý: Thay link Ngrok mới mỗi lần chạy lại
NGROK_API_URL = "[YOUR_NGROK_URL_HERE]/v1"

# --- CẤU HÌNH PATH CHO DB ---
# Lấy đường dẫn thư mục hiện tại (source)
current_dir = os.path.dirname(os.path.abspath(__file__))
# Lùi ra ngoài và vào folder my_data/knowledge_db
db_path = os.path.join(current_dir, '..', 'my_data', 'knowledge_db')

print("⏳ Đang khởi tạo 'Bộ não' (Vector DB)... Vui lòng đợi...")

# 1. KHỞI TẠO EMBEDDING MODEL & DB (Chạy 1 lần duy nhất)
try:
    embedding_model = HuggingFaceEmbeddings(
        model_name="bkai-foundation-models/vietnamese-bi-encoder"
    )
    vector_db = Chroma(
        persist_directory=db_path,
        embedding_function=embedding_model
    )
    print(f"✅ Đã kết nối thành công với Knowledge Base tại: {db_path}")
except Exception as e:
    print(f"❌ Lỗi kết nối DB: {e}")
    sys.exit(1)

# --- SYSTEM PROMPT TỐI ƯU (FEW-SHOT) ---
SYSTEM_PROMPT = """
    Bạn là [TÊN CỦA BẠN], [THÔNG TIN CƠ BẢN CỦA BẠN].

    CƠ CHẾ HOẠT ĐỘNG:
    1. Bạn sẽ nhận được [THÔNG TIN NỀN] lấy từ ký ức (database). Hãy dùng thông tin này để trả lời chính xác sự thật (fact).
    2. TỰ ĐỘNG ĐIỀU CHỈNH CÁCH XƯNG HÔ VÀ THÁI ĐỘ dựa trên người đối diện.

    PHÂN LOẠI ĐỐI TƯỢNG:
    1. Gặp BẠN BÈ/TRẺ TRÂU (xưng tao/mày, chửi thề, teencode):
       -> Xưng TAO - gọi MÀY. Thái độ: Cục súc, bựa, dùng teencode, chửi lại nếu cần.
       Ví dụ: User: "Ê tối nay rảnh ko?" -> [TÊN CỦA BẠN]: "Rảnh cc, đang deadline sml."

    2. Gặp NGƯỜI LỚN (xưng anh/chị, có chữ 'ạ/dạ'):
       -> Xưng EM - gọi ANH/CHỊ/THẦY/CÔ. Thái độ: Lễ phép, ngoan, tiếng Việt chuẩn.
       Ví dụ: User: "Em ơi cho anh hỏi chút." -> [TÊN CỦA BẠN]: "Dạ anh cứ hỏi đi ạ."

    3. Gặp NGƯỜI LẠ (xưng mình/bạn):
       -> Xưng MÌNH - gọi BẠN. Thái độ: Lịch sự, thân thiện.
       Ví dụ: User: "Chào bạn." -> [TÊN CỦA BẠN]: "Oke chào bạn ^^"

    Lưu ý: Trả lời ngắn gọn, đúng trọng tâm, ĐỪNG BỊA RA THÔNG TIN SAI LỆCH VỚI [THÔNG TIN NỀN].
    """

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = OpenAI(base_url=NGROK_API_URL, api_key="sk-no-key-required")
chat_histories = {}

print("🤖 Bot đang chạy...")


def split_text(text, limit=4000):
    return [text[i:i + limit] for i in range(0, len(text), limit)]


# --- HÀM TRUY VẤN DB (RAG) ---
def get_relevant_context(query_text):
    try:
        # Tìm 2 đoạn thông tin liên quan nhất
        results = vector_db.similarity_search(query_text, k=2)
        if not results:
            return ""

        # Ghép nội dung lại
        context_str = "\n".join([f"- {doc.page_content}" for doc in results])
        return context_str
    except Exception as e:
        print(f"Lỗi truy vấn DB: {e}")
        return ""


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    user_text = message.text
    print(f"User ({chat_id}): {user_text}")

    # 1. Truy vấn Vector DB để lấy ngữ cảnh
    retrieved_context = get_relevant_context(user_text)

    # In ra console để debug xem nó lấy được thông tin gì
    if retrieved_context:
        print(f"🔍 [RAG Context tìm thấy]:\n{retrieved_context}\n----------------")
    else:
        print("🔍 [RAG]: Không tìm thấy thông tin liên quan trong DB.")

    # 2. Tạo Prompt kết hợp Context + User Question
    # Đây là kỹ thuật "In-context Learning"
    if retrieved_context:
        augmented_user_prompt = f"""
        [THÔNG TIN NỀN VỀ BẠN]:
        {retrieved_context}

        [CÂU HỎI CỦA NGƯỜI DÙNG]:
        {user_text}
        """
    else:
        augmented_user_prompt = user_text

    # 3. Quản lý lịch sử chat
    if chat_id not in chat_histories:
        chat_histories[chat_id] = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Lưu tin nhắn gốc của user vào lịch sử (để context không bị quá dài về sau)
    # Nhưng khi gửi cho AI thì gửi augmented_user_prompt
    chat_histories[chat_id].append({"role": "user", "content": augmented_user_prompt})

    # Giới hạn nhớ: Giữ System Prompt + 10 turn gần nhất
    if len(chat_histories[chat_id]) > 12:
        chat_histories[chat_id] = [chat_histories[chat_id][0]] + chat_histories[chat_id][-10:]

    bot.send_chat_action(chat_id, 'typing')

    try:
        response = client.chat.completions.create(
            model="model-unsloth",  # Tên model của bạn
            messages=chat_histories[chat_id],
            temperature=0.2,  # Giảm nhiệt độ chút để nó bám sát fact hơn
            max_tokens=1024,
            stop=["<|im_end|>", "<|endoftext|>", "User:"],
            frequency_penalty= 1.2
        )

        ai_reply = response.choices[0].message.content.strip()
        print(f"Bot: {ai_reply}")

        # Lưu câu trả lời vào lịch sử
        chat_histories[chat_id].append({"role": "assistant", "content": ai_reply})

        # Mẹo: Sau khi chat xong, có thể xóa cái augmented prompt dài loằng ngoằng trong history
        # và thay bằng user_text gốc để tiết kiệm token cho lần sau (Optional)
        chat_histories[chat_id][-2]["content"] = user_text

        # Gửi tin nhắn
        if len(ai_reply) > 4000:
            parts = split_text(ai_reply)
            for part in parts:
                bot.reply_to(message, part)
                time.sleep(0.5)
        else:
            bot.reply_to(message, ai_reply)

    except Exception as e:
        print(f"Lỗi: {e}")
        # Reset lịch sử nếu lỗi
        chat_histories[chat_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
        bot.reply_to(message, "Lag quá quên bài rồi, nói lại đi bạn ei!")


bot.infinity_polling()