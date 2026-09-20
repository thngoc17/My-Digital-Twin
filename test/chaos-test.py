import os
import sys
import time
import random
import requests
import concurrent.futures
import logging
from datetime import datetime
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

# ==========================================
# CẤU HÌNH LOGGING
# ==========================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILENAME = os.path.join(CURRENT_DIR, f"chaos_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILENAME, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ==========================================
# 1. XÁC THỰC BẢO MẬT (KEY VAULT)
# ==========================================
KEY_VAULT_NAME = "qwen-twin-vault"
KV_URI = f"https://{KEY_VAULT_NAME}.vault.azure.net"

try:
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=KV_URI, credential=credential)
    AZURE_ENDPOINT_URL = client.get_secret("azure-endpoint-url").value
    AZURE_API_KEY = client.get_secret("azure-api-key").value
    logger.info("Decrypted API configuration keys successfully.")
except Exception as e:
    logger.error(f"KEY VAULT ERROR: {e}")
    sys.exit(1)

# ==========================================
# 2. ĐỊNH NGHĨA KỊCH BẢN & LƯU LƯỢNG
# ==========================================
TOTAL_REQUESTS = 50
CONCURRENCY = 2          # Đồng bộ tuyệt đối với năng lực xử lý (max 2)
PACING_DELAY = 3.0       # Độ trễ (giây) giữa các lần nạp request vào hàng đợi

SCENARIOS = {
    "VALID": {
        "headers": {"Content-Type": "application/json", "Authorization": f"Bearer {AZURE_API_KEY}"},
        "payload": {"messages": [{"role": "user", "content": "Tóm tắt tiểu sử của bạn."}], "temperature": 0.2, "max_tokens": 100},
        "expected_code": 200
    },
    "BAD_REQUEST": { 
        "headers": {"Content-Type": "application/json", "Authorization": f"Bearer {AZURE_API_KEY}"},
        "payload": {"wrong_schema_key": "data", "temperature": "high"}, 
        "expected_code": 400
    },
    "UNAUTHORIZED": { 
        "headers": {"Content-Type": "application/json", "Authorization": "Bearer INVALID_OR_EXPIRED_TOKEN_123"},
        "payload": {"messages": [{"role": "user", "content": "Test."}]},
        "expected_code": 401
    }
}

# ==========================================
# 3. LOGIC THỰC THI (ĐIỀU PHỐI NHỊP ĐỘ)
# ==========================================
def inject_chaos(request_id):
    scenario_name = random.choice(list(SCENARIOS.keys()))
    scenario = SCENARIOS[scenario_name]
    
    try:
        # Tăng timeout lên 60s cho LLM trên CPU
        response = requests.post(
            AZURE_ENDPOINT_URL, 
            headers=scenario["headers"], 
            json=scenario["payload"], 
            timeout=60
        )
        status = response.status_code
        logger.info(f"Req-{request_id:02d} [{scenario_name}] -> HTTP {status}")
        return status
    except requests.exceptions.Timeout:
        logger.error(f"Req-{request_id:02d} [{scenario_name}] -> TIMEOUT EXCEPTION")
        return 0
    except Exception as e:
        logger.error(f"Req-{request_id:02d} [{scenario_name}] -> NETWORK EXCEPTION: {str(e)}")
        return 0

def run_chaos_test():
    logger.info("=" * 50)
    logger.info(f"KHỞI CHẠY CHAOS TEST: {TOTAL_REQUESTS} REQUESTS (PACED)")
    logger.info("=" * 50)

    status_counts = {}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = []
        # Nạp request từ từ vào hàng đợi của ThreadPool thay vì nạp ồ ạt
        for i in range(TOTAL_REQUESTS):
            futures.append(executor.submit(inject_chaos, i))
            time.sleep(PACING_DELAY) 
            
        for future in concurrent.futures.as_completed(futures):
            status = future.result()
            status_counts[status] = status_counts.get(status, 0) + 1

    logger.info("\n" + "=" * 50)
    logger.info("TỔNG HỢP HTTP STATUS CODES:")
    for code, count in status_counts.items():
        logger.info(f"HTTP {code}: {count} requests")
    
    logger.info("=" * 50)
    logger.warning("BẮT BUỘC CHỜ 5 PHÚT ĐỂ LOG ANALYTICS HOÀN TẤT ĐỒNG BỘ DỮ LIỆU (INGESTION)...")
    logger.warning("TUYỆT ĐỐI KHÔNG XÓA ENDPOINT LÚC NÀY.")
    time.sleep(300)
    logger.info("Đã hoàn tất đồng bộ. Bạn có thể mở Azure Portal và chạy KQL.")

if __name__ == "__main__":
    run_chaos_test()