# ==========================================
# STAGE 1: BUILDER
# ==========================================
FROM python:3.10-slim AS builder
WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake libopenblas-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

ENV CMAKE_ARGS="-DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS"
ENV FORCE_CMAKE=1
ENV MAKEFLAGS="-j2"
RUN pip wheel --no-cache-dir --wheel-dir /build/wheels -r requirements.txt

# ==========================================
# STAGE 2: RUNTIME
# ==========================================
FROM python:3.10-slim
WORKDIR /app

# BỔ SUNG libgomp1 VÀO ĐÂY ĐỂ HỖ TRỢ ĐA LUỒNG CPU
RUN apt-get update && apt-get install -y --no-install-recommends \
    libopenblas0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /build/wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache-dir /wheels/*
RUN rm -rf /wheels requirements.txt

# Đẩy toàn bộ thư mục mã nguồn vào vùng chứa
COPY source/ /app/source/

EXPOSE 8000

# Trỏ Uvicorn vào module bên trong thư mục source
CMD ["uvicorn", "source.main:app", "--host", "0.0.0.0", "--port", "8000"]