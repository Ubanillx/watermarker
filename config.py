"""
水印服务配置文件
"""
import os
from pathlib import Path

# 服务配置
HOST = os.getenv("WATERMARK_HOST", "0.0.0.0")
PORT = int(os.getenv("WATERMARK_PORT", "9996"))

# 下载URL前缀配置
DOWNLOAD_URL_PREFIX = os.getenv("DOWNLOAD_URL_PREFIX", "http://121.229.205.96:9996/download")

# 文件存储配置
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
TEMP_DIR = BASE_DIR / "temp"

# 确保目录存在
OUTPUT_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

# 线程池配置
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "10"))

# 支持的文件类型
SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff"}
SUPPORTED_DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".doc"}
SUPPORTED_EXTENSIONS = SUPPORTED_IMAGE_EXTENSIONS | SUPPORTED_DOCUMENT_EXTENSIONS

# 文件大小限制 (50MB)
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", str(50 * 1024 * 1024)))

# 文件保留时间 (秒)
FILE_RETENTION_SECONDS = int(os.getenv("FILE_RETENTION_SECONDS", "3600"))

# 水印默认配置
DEFAULT_WATERMARK_CONFIG = {
    "font_size": 40,
    "font_color": "#808080",
    "opacity": 0.3,
    "angle": -45,
    "spacing": 100,
    "position": "tile",  # tile(平铺), center(居中), corner(角落)
}

# 自定义字体路径（可选，用于支持特定中文字体）
# 如果设置，将优先使用此字体
CUSTOM_FONT_PATH = os.getenv("CUSTOM_FONT_PATH", "")
