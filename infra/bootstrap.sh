#!/usr/bin/env bash
# =============================================================================
# BOOTSTRAP — CHẠY THỦ CÔNG MỘT LẦN DUY NHẤT, KHÔNG CHẠY TRONG GITHUB ACTIONS.
#
# Người chạy script này cần quyền cao ở cấp SUBSCRIPTION (Owner, hoặc Contributor
# + User Access Administrator) — vì phải tạo Resource Group VÀ gán quyền, mà
# gán quyền (Microsoft.Authorization/roleAssignments) luôn đòi hỏi quyền đó.
#
# Sau khi chạy xong: Service Principal dùng cho GitHub Actions chỉ còn quyền
# Contributor trên ĐÚNG 1 Resource Group này. Từ đó về sau, infra.yml và
# deploy.yml không bao giờ cần và không bao giờ có quyền cao hơn thế nữa.
#
# Chạy lại script này (idempotent) nếu cần tái tạo RG sau khi đã xoá.
# =============================================================================
set -euo pipefail

SUBSCRIPTION_ID="f6b812fd-ef94-4ce1-948f-ea652339a497"
RESOURCE_GROUP="qwen-digital-twin-rg"     # Phải khớp với GitHub repo Variable "RESOURCE_GROUP"
LOCATION="eastasia"
SP_NAME="sp-qwen-digital-twin"

echo "==> Đăng nhập và chọn đúng subscription..."
az account set --subscription "$SUBSCRIPTION_ID"

echo "==> Tạo Resource Group (idempotent, không lỗi nếu đã tồn tại)..."
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none

RG_ID=$(az group show --name "$RESOURCE_GROUP" --query id -o tsv)
echo "    Resource Group ID: $RG_ID"

echo "==> Tạo Service Principal, gán Contributor CHỈ trên Resource Group này..."
echo "    (Không dùng --scopes ở cấp subscription — đây chính là điểm mấu chốt)"
az ad sp create-for-rbac \
  --name "$SP_NAME" \
  --role "Contributor" \
  --scopes "$RG_ID" \
  --sdk-auth > sp-credentials.json

echo ""
echo "=================================================================="
echo "XONG. Các bước tiếp theo (thủ công):"
echo "1. Mở file sp-credentials.json vừa tạo, copy toàn bộ nội dung JSON."
echo "2. Vào GitHub repo > Settings > Secrets and variables > Actions"
echo "   > New repository secret > tên 'AZURE_CREDENTIALS' > dán JSON vào."
echo "3. Thêm repository Variable 'RESOURCE_GROUP' = '$RESOURCE_GROUP'"
echo "   (và 'WORKSPACE' nếu muốn đổi tên workspace khác 'mlops-workspace')."
echo "4. XOÁ NGAY file sp-credentials.json khỏi máy — nó chứa secret nhạy cảm:"
echo "     rm sp-credentials.json"
echo ""
echo "Lưu ý bảo mật: cân nhắc chuyển sang OIDC (Workload Identity Federation)"
echo "thay vì secret dạng JSON có hạn dùng dài — xem 'azure/login' action docs."
echo "=================================================================="