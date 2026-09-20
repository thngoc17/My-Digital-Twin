import os
import sys
import time
import requests
import telebot
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.core.exceptions import ClientAuthenticationError, ResourceNotFoundError

# ==========================================
# 1. AUTHENTICATION & SECRET EXTRACTION
# ==========================================
KEY_VAULT_NAME = "qwen-chatbot-twin-vault"  # Insert Vault name here
KV_URI = f"https://{KEY_VAULT_NAME}.vault.azure.net"

print(f"INFO: Authenticating with Azure Key Vault at {KV_URI}")

try:
    # Retrieve default credentials (requires 'az login' locally)
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=KV_URI, credential=credential)

    # Extract secrets from Key Vault
    # Use .value to retrieve the actual text string from KeyVaultSecret
    TELEGRAM_TOKEN = client.get_secret("telegram-token").value
    AZURE_ENDPOINT_URL = client.get_secret("azure-endpoint-url").value
    AZURE_API_KEY = client.get_secret("azure-api-key").value

    print("SUCCESS: Configuration keys retrieved successfully.")

except ClientAuthenticationError:
    print("ERROR: Authentication failed. Unable to verify Azure identity.")
    print("ACTION: Run 'az login' in your terminal to grant local access.")
    sys.exit(1)
except ResourceNotFoundError as e:
    print(f"ERROR: Resource not found. Secret missing in Vault. Details: {e}")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: Unexpected error connecting to Key Vault: {e}")
    sys.exit(1)

# ==========================================
# 2. THIN CLIENT INITIALIZATION
# ==========================================
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Internal session state
chat_histories = {}
SYSTEM_PROMPT = """
    Bạn là Lê Thái Ngọc, Sinh viên năm 3 ngành Trí tuệ nhân tạo trường Đại học Khoa học tự nhiên, ĐHQG-HCM.

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


def split_text(text, limit=4000):
    return [text[i:i + limit] for i in range(0, len(text), limit)]


# ==========================================
# 3. MAIN EXECUTION LOOP
# ==========================================
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    user_text = message.text

    print(f"INFO [User-{chat_id}]: {user_text}")

    if chat_id not in chat_histories:
        chat_histories[chat_id] = [{"role": "system", "content": SYSTEM_PROMPT}]

    chat_histories[chat_id].append({"role": "user", "content": user_text})

    # Sliding window: Limit context to System prompt + 8 messages
    if len(chat_histories[chat_id]) > 10:
        chat_histories[chat_id] = [chat_histories[chat_id][0]] + chat_histories[chat_id][-8:]

    bot.send_chat_action(chat_id, 'typing')

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AZURE_API_KEY}"
    }

    payload = {
        "messages": chat_histories[chat_id],
        "temperature": 0.02,
        "max_tokens": 1024
    }

    try:
        start_time = time.time()

        # Communicate with Managed Endpoint
        response = requests.post(
            AZURE_ENDPOINT_URL,
            headers=headers,
            json=payload,
            timeout=120
        )
        response.raise_for_status()

        response_data = response.json()
        ai_reply = response_data.get("reply", "")
        processing_time = response_data.get("processing_time", 0)

        print(f"INFO [Azure Backend] (Latency: {processing_time:.2f}s): {ai_reply}")

        chat_histories[chat_id].append({"role": "assistant", "content": ai_reply})

        if len(ai_reply) > 4000:
            for part in split_text(ai_reply):
                bot.reply_to(message, part)
                time.sleep(0.3)
        else:
            bot.reply_to(message, ai_reply)

    except requests.exceptions.Timeout:
        print("ERROR: Azure Endpoint timeout.")
        bot.reply_to(message, "Cloud system is overloaded or starting up. Please wait and try again.")
        chat_histories[chat_id].pop()

    except requests.exceptions.RequestException as e:
        print(f"ERROR [HTTP]: {e}")
        bot.reply_to(message, "Communication error with AI Backend.")
        chat_histories[chat_id].pop()


if __name__ == "__main__":
    print("INFO: Telegram Thin Client (Zero-Trust Architecture) started.")
    bot.infinity_polling()