"""
文件处理工具
"""
import os
import uuid
import httpx
import mimetypes
from pathlib import Path
from typing import Tuple, Optional

import config
import re
from urllib.parse import urlparse, unquote


def get_file_extension(filename: str) -> str:
    """获取文件扩展名"""
    return Path(filename).suffix.lower()


def get_extension_from_content_type(content_type: str) -> str:
    """从Content-Type获取扩展名"""
    ext = mimetypes.guess_extension(content_type)
    if ext == ".jpe":
        ext = ".jpg"
    return ext or ""


def detect_file_type(extension: str) -> str:
    """根据扩展名检测文件类型"""
    ext = extension.lower()
    if ext in config.SUPPORTED_IMAGE_EXTENSIONS:
        return "image"
    elif ext == ".pdf":
        return "pdf"
    elif ext in {".docx", ".doc"}:
        return "word"
    return "unknown"


def generate_output_filename(original_filename: str) -> str:
    """生成输出文件名"""
    ext = get_file_extension(original_filename)
    unique_id = uuid.uuid4().hex[:8]
    base_name = Path(original_filename).stem
    return f"{base_name}_watermarked_{unique_id}{ext}"


def parse_content_disposition(content_disposition: str) -> Optional[str]:
    """
    解析Content-Disposition header获取文件名
    支持 filename*=UTF-8''... 和 filename="..." 格式
    """
    if not content_disposition:
        return None
    
    # 优先解析 filename*=UTF-8''encoded_name 格式 (RFC 5987)
    match = re.search(r"filename\*\s*=\s*([^']+)'[^']*'(.+?)(?:;|$)", content_disposition, re.IGNORECASE)
    if match:
        encoding = match.group(1).lower()
        encoded_name = match.group(2)
        try:
            return unquote(encoded_name, encoding=encoding if encoding else 'utf-8')
        except Exception:
            pass
    
    # 解析 filename="name" 或 filename=name 格式
    match = re.search(r'filename\s*=\s*["\']?([^"\'\s;]+)["\']?', content_disposition, re.IGNORECASE)
    if match:
        return match.group(1)
    
    return None


def extract_filename_from_url(url: str) -> Optional[str]:
    """
    从URL路径中提取文件名
    """
    try:
        parsed = urlparse(url)
        path = unquote(parsed.path)  # URL解码
        filename = Path(path).name
        # 检查是否是有效文件名（有扩展名）
        if filename and "." in filename and len(filename) > 2:
            return filename
    except Exception:
        pass
    return None


async def download_file(url: str) -> Tuple[bytes, str, str]:
    """
    从URL下载文件
    返回: (文件内容, 原始文件名, 扩展名)
    """
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
        
        content = response.content
        filename = None
        
        # 1. 优先从Content-Disposition获取文件名（最可靠）
        content_disposition = response.headers.get("content-disposition", "")
        filename = parse_content_disposition(content_disposition)
        
        # 2. 尝试从URL路径获取文件名
        if not filename:
            filename = extract_filename_from_url(url)
        
        # 3. 根据Content-Type生成文件名
        if not filename:
            content_type = response.headers.get("content-type", "")
            extension = get_extension_from_content_type(content_type.split(";")[0])
            filename = f"file_{uuid.uuid4().hex[:8]}{extension}"
        
        # 获取扩展名
        extension = get_file_extension(filename)
        
        # 如果没有扩展名，尝试从Content-Type补充
        if not extension:
            content_type = response.headers.get("content-type", "")
            extension = get_extension_from_content_type(content_type.split(";")[0])
            if extension:
                filename = f"{filename}{extension}"
        
        return content, filename, extension


def save_temp_file(content: bytes, filename: str) -> Path:
    """保存临时文件"""
    temp_path = config.TEMP_DIR / f"{uuid.uuid4().hex}_{filename}"
    temp_path.write_bytes(content)
    return temp_path


def save_output_file(content: bytes, filename: str) -> Path:
    """保存输出文件"""
    output_path = config.OUTPUT_DIR / filename
    output_path.write_bytes(content)
    return output_path


def get_download_url(filename: str) -> str:
    """生成下载URL"""
    return f"{config.DOWNLOAD_URL_PREFIX}/{filename}"


def cleanup_old_files():
    """清理过期文件"""
    import time
    current_time = time.time()
    
    for directory in [config.OUTPUT_DIR, config.TEMP_DIR]:
        if not directory.exists():
            continue
        for file_path in directory.iterdir():
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                if file_age > config.FILE_RETENTION_SECONDS:
                    try:
                        file_path.unlink()
                    except Exception:
                        pass
