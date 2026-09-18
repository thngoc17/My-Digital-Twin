import json
import os
import re
from tqdm import tqdm
from underthesea_core import TextPreprocessor

# ================= AUTOMATED PATH CONFIGURATION =================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "my_data", "facebook_chat"))
OUTPUT_FILE = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "my_data", "train_data.jsonl"))

MY_NAME = "Lê Thái Ngọc" # Target user name for assistant role mapping

# Time threshold configuration
MERGE_TIMEOUT = 60
SESSION_TIMEOUT = 3600 * 2

print(f"INFO: Data Directory resolved at {DATA_DIR}")
print(f"INFO: Output File targeted at {OUTPUT_FILE}")
print("-" * 50)

# ================= INITIALIZE LLM TEXT PREPROCESSOR =================
pp = TextPreprocessor(
    lowercase=False,
    unicode_normalize=True,
    remove_urls=True,
    normalize_repeated_chars=True,
    normalize_punctuation=True,
    use_defaults=True,
    negation_words=[],
    negation_window=0
)

# ================= CLASSIFICATION DICTIONARIES =================
KEYWORDS = {
    "friends": [
        "tao", "mày", "dm", "vcl", "vl", "đm", "đéo", "dell",
        "ngu", "điên", "khùng", "con", "thằng", "mi", "tau", "chó", "loz", "cc", "đù"
    ],
    "elders": [
        "dạ", "vâng", "ạ", "con", "cháu", "bác", "chú", "cô", "dì", "thưa", "kính",
        "ba", "mẹ", "bố", "anh ơi", "chị ơi", "anh", "chị"
    ],
    "polite": [
        "mình", "bạn", "cậu", "tớ", "ấy", "chào", "cảm ơn", "thanks", "tks",
        "xin", "phiền", "giúp", "vui lòng", "b", "c", "tui", "bà", "ông", "tôi"
    ]
}


# ================= CORE LOGIC FUNCTIONS =================
def classify_conversation(session_messages):
    scores = {"friends": 0, "elders": 0, "polite": 0}
    full_text = " ".join([m['content'].lower() for m in session_messages]).lower()
    tokens = full_text.split()

    for token in tokens:
        word = re.sub(r'[^\w\s]', '', token)
        if word in KEYWORDS["friends"]: scores["friends"] += 2
        if word in KEYWORDS["elders"]: scores["elders"] += 1.5
        if word in KEYWORDS["polite"]: scores["polite"] += 1

    if "dạ" in tokens or "vâng" in tokens or "ạ" in tokens:
        return "elders"

    best_category = max(scores, key=scores.get)
    if scores[best_category] == 0:
        return "friends"

    return best_category


def fix_encoding(text):
    if not text: return ""
    try:
        return text.encode('latin1').decode('utf-8')
    except:
        return text


def is_system_message(content):
    if not content: return False
    block_phrases = [
        "đã bày tỏ cảm xúc", "đã thu hồi", "đã xóa", "cuộc gọi",
        "missed call", "đã đặt biệt danh",
        "giờ đây, các bạn có thể gọi",
        "các bạn hiện có thể nhắn tin"
    ]
    return any(p in content.lower() for p in block_phrases)


def get_content(msg):
    if 'is_unsent' in msg and msg['is_unsent']: return ""

    content = ""
    if 'content' in msg:
        raw_text = fix_encoding(msg['content'])

        if is_system_message(raw_text):
            return ""

        try:
            content = pp.transform(raw_text)
        except:
            content = raw_text

    if not content:
        if 'photos' in msg: return "[Image sent]"
        if 'videos' in msg: return "[Video sent]"
        if 'sticker' in msg: return "[Sticker sent]"
        return ""

    return content


def process_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        return []

    # === STRICT GROUP CHAT FILTERING LOGIC ===
    # 1. Skip explicit RegularGroup threads
    if data.get('thread_type') == 'RegularGroup':
        return []

    # 2. Skip threads with more than 2 participants
    if len(data.get('participants', [])) > 2:
        return []

    raw_messages = data.get('messages', [])
    if not raw_messages: return []
    raw_messages.sort(key=lambda x: x.get('timestamp_ms', 0))

    conversations = []
    current_session = []
    last_sender = None
    last_time = 0
    buffer_text = []

    for msg in raw_messages:
        sender = fix_encoding(msg.get('sender_name', 'Unknown'))
        timestamp = msg.get('timestamp_ms', 0) / 1000
        content = get_content(msg)

        if not content: continue

        if last_time > 0 and (timestamp - last_time > SESSION_TIMEOUT):
            if buffer_text:
                current_session.append({
                    "role": "assistant" if last_sender == MY_NAME else "user",
                    "content": "\n".join(buffer_text)
                })
            if len(current_session) >= 2:
                category = classify_conversation(current_session)
                conversations.append({"category": category, "messages": current_session})

            current_session = []
            buffer_text = []
            last_sender = None

        if (sender == last_sender) and (timestamp - last_time < MERGE_TIMEOUT):
            buffer_text.append(content)
        else:
            if buffer_text:
                current_session.append({
                    "role": "assistant" if last_sender == MY_NAME else "user",
                    "content": "\n".join(buffer_text)
                })
            buffer_text = [content]
            last_sender = sender
        last_time = timestamp

    if buffer_text:
        current_session.append({
            "role": "assistant" if last_sender == MY_NAME else "user",
            "content": "\n".join(buffer_text)
        })
    if len(current_session) >= 2:
        category = classify_conversation(current_session)
        conversations.append({"category": category, "messages": current_session})

    return conversations


def main():
    if not os.path.exists(DATA_DIR):
        print(f"ERROR: Data directory not found at {DATA_DIR}")
        return

    print(f"INFO: Recursively scanning directory {DATA_DIR}...")
    target_files = []

    for root, dirs, files in os.walk(DATA_DIR):
        for file in files:
            if file == "message_1.json":
                target_files.append(os.path.join(root, file))

    if not target_files:
        print("WARNING: No matching JSON files found.")
        return

    print(f"INFO: Found {len(target_files)} chat threads. Initiating processing...")

    final_dataset = []
    for file_path in tqdm(target_files):
        sessions = process_file(file_path)
        for item in sessions:
            has_assistant = any(msg['role'] == 'assistant' for msg in item['messages'])
            if has_assistant:
                final_dataset.append(item)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    print(f"INFO: Writing {len(final_dataset)} samples to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for entry in final_dataset:
            json.dump(entry, f, ensure_ascii=False)
            f.write('\n')

    print("SUCCESS: Data normalization completed successfully using TextPreprocessor.")


if __name__ == "__main__":
    main()