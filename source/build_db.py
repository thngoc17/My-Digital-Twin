import json
import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

# --- CẤU HÌNH ĐƯỜNG DẪN (PATH CONFIGURATION) ---

# 1. Xác định vị trí file code hiện tại (trong thư mục source)
current_dir = os.path.dirname(os.path.abspath(__file__))

# 2. Xác định thư mục chứa data (ngang hàng với source)
# Đi ngược ra thư mục cha (..) rồi vào my_data
data_dir = os.path.join(current_dir, '..', 'my_data')

# 3. Đường dẫn file JSON đầu vào
input_json_path = os.path.join(data_dir, 'profile.json')

# 4. Đường dẫn thư mục lưu Vector DB đầu ra
db_output_path = os.path.join(data_dir, 'knowledge_db')

# Đảm bảo thư mục my_data tồn tại (tránh lỗi nếu chưa có)
if not os.path.exists(data_dir):
    os.makedirs(data_dir)
    print(f"Đã tạo thư mục: {data_dir}")

print(f"📂 Đang đọc dữ liệu từ: {input_json_path}")
print(f"📂 DB sẽ được lưu tại: {db_output_path}")


# --- PHẦN XỬ LÝ LOGIC ---

def load_data(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print(f"❌ LỖI: Không tìm thấy file {file_path}. Hãy kiểm tra lại vị trí file JSON.")
        exit()


# Load dữ liệu
raw_data = load_data(input_json_path)

# Chuyển đổi JSON thành LangChain Documents
documents = []
for item in raw_data:
    meta = item.get('metadata', {})
    meta['category'] = item.get('category', 'unknown')
    meta['original_id'] = item.get('id', 'unknown')

    # Gom các keywords thành string để lưu vào metadata (Chroma yêu cầu metadata phẳng)
    if 'keywords' in meta and isinstance(meta['keywords'], list):
        meta['keywords_str'] = ", ".join(meta['keywords'])

    doc = Document(
        page_content=item.get('content', ''),
        metadata=meta
    )
    documents.append(doc)

print(f"✅ Đã load {len(documents)} bản ghi.")

# Khởi tạo Embedding Model
print("⏳ Đang tải model embedding (có thể mất chút thời gian lần đầu)...")
embedding_model = HuggingFaceEmbeddings(
    model_name="bkai-foundation-models/vietnamese-bi-encoder"
)

# Tạo và lưu Vector Database
print("⏳ Đang tạo Vector Database...")
vector_db = Chroma.from_documents(
    documents=documents,
    embedding=embedding_model,
    persist_directory=db_output_path
)

print("-" * 40)
print(f"✅ HOÀN TẤT! Vector Database đã được lưu vào: {db_output_path}")