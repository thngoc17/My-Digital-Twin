import json
import os
import sys
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

# --- CẤU HÌNH ĐƯỜNG DẪN ---
current_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(current_dir, '..', 'my_data')
input_json_path = os.path.join(data_dir, 'profile.json')
db_output_path = os.path.join(data_dir, 'knowledge_db')

# Logic đúng: Chỉ tạo thư mục cho ĐẦU RA nếu chưa có.
if not os.path.exists(db_output_path):
    os.makedirs(db_output_path)
    print(f"Đã tạo thư mục lưu Vector DB: {db_output_path}")

print(f"📂 Đang đọc dữ liệu từ: {input_json_path}")


# --- PHẦN XỬ LÝ LOGIC ---

def load_data(file_path):
    if not os.path.exists(file_path):
        print(f"❌ LỖI: Không tìm thấy file nguồn tại {file_path}.")
        sys.exit(1) # Trả về mã lỗi tiêu chuẩn
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ LỖI: File JSON bị sai định dạng: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ LỖI KHÔNG XÁC ĐỊNH khi đọc file: {e}")
        sys.exit(1)


raw_data = load_data(input_json_path)

documents = []
for item in raw_data:
    # Sử dụng .copy() để tránh thay đổi trực tiếp dữ liệu gốc trong bộ nhớ
    meta = item.get('metadata', {}).copy()
    
    # Đảm bảo các giá trị thêm vào tương thích với Schema của ChromaDB (str, int, float, bool)
    meta['category'] = str(item.get('category', 'unknown'))
    meta['original_id'] = str(item.get('id', 'unknown'))

    if 'keywords' in meta:
        if isinstance(meta['keywords'], list):
            meta['keywords_str'] = ", ".join(meta['keywords'])
        # BẮT BUỘC: Xóa kiểu dữ liệu phức hợp (list) để tránh ValueError từ ChromaDB
        del meta['keywords']

    doc = Document(
        page_content=item.get('content', ''),
        metadata=meta
    )
    documents.append(doc)

print(f"✅ Đã load {len(documents)} bản ghi hợp lệ.")

print("⏳ Đang tải model embedding...")
embedding_model = HuggingFaceEmbeddings(
    model_name="bkai-foundation-models/vietnamese-bi-encoder"
)

print("⏳ Đang tạo Vector Database...")
try:
    vector_db = Chroma.from_documents(
        documents=documents,
        embedding=embedding_model,
        persist_directory=db_output_path
    )
    print("-" * 40)
    print(f"✅ HOÀN TẤT! Vector Database đã được lưu vào: {db_output_path}")
except Exception as e:
    print(f"❌ LỖI KHI TẠO VECTOR DB: {e}")
    sys.exit(1)