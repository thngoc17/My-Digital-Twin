import os
import sys
import time
import requests
import concurrent.futures
import logging
from datetime import datetime
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.core.exceptions import ClientAuthenticationError

# ==========================================
# STANDARDIZED LOGGING CONFIGURATION
# ==========================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILENAME = os.path.join(CURRENT_DIR, f"stress_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

# Initialize logger for concurrent console and file output
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
# 1. ZERO-TRUST AUTHENTICATION ARCHITECTURE
# ==========================================
KEY_VAULT_NAME = "qwen-rag-vault"
KV_URI = f"https://{KEY_VAULT_NAME}.vault.azure.net"

logger.info(f"Authenticating with Azure Key Vault at {KV_URI}...")
try:
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=KV_URI, credential=credential)

    AZURE_ENDPOINT_URL = client.get_secret("azure-endpoint-url").value
    AZURE_API_KEY = client.get_secret("azure-api-key").value
    logger.info("Successfully decrypted API configuration keys.")
except ClientAuthenticationError:
    logger.error("AUTHENTICATION ERROR: Execute 'az login' in your Windows terminal.")
    sys.exit(1)
except Exception as e:
    logger.error(f"KEY VAULT ERROR: {e}")
    sys.exit(1)

# ==========================================
# 2. TEST CONFIGURATION & PAYLOAD
# ==========================================
# Step-load model: 1, 2, 5, 10, 15
CONCURRENCY_LEVELS = [1, 2, 5, 10, 15]
COOL_DOWN_SECONDS = 20  # Cool-down period between test tiers

PAYLOAD = {
    "messages": [{"role": "user", "content": "Tóm tắt về tiểu sử của bạn trong 2 câu."}],
    "temperature": 0.2,
    "max_tokens": 1024
}

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {AZURE_API_KEY}"
}


# ==========================================
# 3. EXECUTION LOGIC (THREADING)
# ==========================================
def send_request(user_id):
    """Simulate an independent user query."""
    start_time = time.time()
    try:
        response = requests.post(AZURE_ENDPOINT_URL, headers=HEADERS, json=PAYLOAD, timeout=120)
        latency = time.time() - start_time

        if response.status_code == 200:
            return {"status": "success", "latency": latency, "msg": f"User-{user_id}: Success"}
        else:
            return {"status": "error", "latency": latency,
                    "msg": f"User-{user_id}: Error {response.status_code} - {response.text}"}
    except requests.exceptions.Timeout:
        latency = time.time() - start_time
        return {"status": "timeout", "latency": latency, "msg": f"User-{user_id}: Timeout"}
    except Exception as e:
        latency = time.time() - start_time
        return {"status": "error", "latency": latency, "msg": f"User-{user_id}: Exception {str(e)}"}


def run_stress_test():
    logger.info("=" * 50)
    logger.info("INITIATING STEP-LOAD STRESS TEST SEQUENCE")
    logger.info("=" * 50)

    for concurrent_users in CONCURRENCY_LEVELS:
        logger.info(f"\n[PHASE] Testing with {concurrent_users} concurrent users...")

        results = []
        start_tier = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(send_request, i) for i in range(concurrent_users)]
            for future in concurrent.futures.as_completed(futures):
                res = future.result()
                results.append(res)

                # Log details only on failure to prevent console flooding
                if res["status"] != "success":
                    logger.warning(res["msg"])

        total_time = time.time() - start_tier

        # Calculate metrics
        success_count = sum(1 for r in results if r["status"] == "success")
        latencies = [r["latency"] for r in results if r["status"] == "success"]

        error_count = concurrent_users - success_count
        success_rate = (success_count / concurrent_users) * 100

        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        max_latency = max(latencies) if latencies else 0
        min_latency = min(latencies) if latencies else 0

        # Output localized report
        logger.info(f"[PHASE REPORT: {concurrent_users} USERS]")
        logger.info(f"   - Success Rate   : {success_rate:.2f}% ({success_count}/{concurrent_users})")
        logger.info(f"   - Error Count    : {error_count}")
        logger.info(f"   - Avg Latency    : {avg_latency:.2f}s")
        logger.info(f"   - Min/Max Latency: {min_latency:.2f}s / {max_latency:.2f}s")
        logger.info(f"   - Tier Duration  : {total_time:.2f}s")

        # Abort test sequence if complete system failure occurs
        if success_rate == 0:
            logger.critical("CRITICAL FAILURE: System completely unresponsive. Aborting to protect resources.")
            break

        # Cool-down before increasing load
        if concurrent_users != CONCURRENCY_LEVELS[-1]:
            logger.info(f"Cooling down... Waiting {COOL_DOWN_SECONDS}s before scaling up load.")
            time.sleep(COOL_DOWN_SECONDS)

    logger.info("\n" + "=" * 50)
    logger.info(f"TEST COMPLETE. Logs saved at: {LOG_FILENAME}")
    logger.info("=" * 50)


if __name__ == "__main__":
    run_stress_test()