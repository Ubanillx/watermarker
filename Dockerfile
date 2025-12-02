# 水印服务 Dockerfile
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 设置国内镜像源（阿里云）
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources

# 安装系统依赖（用于Pillow和字体支持）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libfreetype6-dev \
    libjpeg62-turbo-dev \
    libpng-dev \
    fontconfig \
    fonts-noto-cjk \
    && fc-cache -fv \
    && rm -rf /var/lib/apt/lists/* \
    && find /usr/share/fonts -name "*.ttc" -o -name "*.ttf" | head -20

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖（使用阿里云镜像）
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# 复制应用代码
COPY . .

# 创建输出目录
RUN mkdir -p output temp

# 暴露端口
EXPOSE 9996

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:9996/health')" || exit 1

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9996"]
