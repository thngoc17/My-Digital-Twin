#!/usr/bin/env bash
# =============================================================================
# SEED MODEL — chạy THỦ CÔNG, TỪ CHÍNH MÁY CÁ NHÂN đang giữ file .gguf.
#
# GitHub Actions runner là máy ảo tạm thời trên cloud của GitHub — nó KHÔNG BAO GIỜ
# có quyền truy cập ổ đĩa máy cá nhân của bạn, dù workflow được viết thế nào đi nữa.
# Vì vậy bước "upload + đăng ký model .gguf" bắt buộc phải chạy từ máy đang có file,
# không thể và sẽ không bao giờ được tự động hoá trong deploy.yml.
#
# Chạy script này:
#   - Lần đầu, ngay sau khi infra.yml tạo xong Workspace (Workspace mới luôn trống).
#   - Bất cứ khi nào Workspace bị xoá/tạo lại từ đầu (model registry mất theo hạ tầng).
#   - Khi bạn train ra một phiên bản .gguf mới muốn đóng băng lại (đổi version trong azure/model.yml).
#
# Trong vòng đời bình thường (model đã đóng băng, hạ tầng không bị xoá), KHÔNG cần chạy lại.
# =============================================================================
set -euo pipefail

RESOURCE_GROUP="qwen-chatbot-twin-rg"    # Phải khớp GitHub repo Variable "RESOURCE_GROUP"
WORKSPACE='qwen-chatbot-twin-workspace'         # Phải khớp GitHub repo Variable "WORKSPACE"
GGUF_FILENAME="qwen3-4b-instruct-2507.Q4_K_M.gguf"

cd "$(dirname "$0")/.."  # về thư mục gốc repo, để path trong azure/model.yml resolve đúng

if [ ! -f "model/$GGUF_FILENAME" ]; then
  echo "Không tìm thấy source/$GGUF_FILENAME."
  echo "Đặt file .gguf vào đúng vị trí này (trên MÁY BẠN) trước khi chạy tiếp."
  exit 1
fi

az account show > /dev/null 2>&1 || { echo "Chưa 'az login'. Đăng nhập trước rồi chạy lại."; exit 1; }

az configure --defaults group="$RESOURCE_GROUP" workspace="$WORKSPACE"

echo "==> Đăng ký model lên Azure ML Workspace '$WORKSPACE' (upload trực tiếp từ máy này)..."
az ml model create -f azure/model.yml

echo ""
echo "Xong. Từ giờ 'deploy.yml' sẽ thấy model đã tồn tại và chạy tiếp bình thường."