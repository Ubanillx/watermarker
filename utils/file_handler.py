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


async def download_file(url: str) -> Tuple[bytes, str, str]:
    """
    从URL下载文件
    返回: (文件内容, 原始文件名, 扩展名)
    """
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
        
        content = response.content
        
        # 尝试从URL获取文件名
        filename = Path(str(url).split("?")[0]).name
        
        # 如果URL没有文件名，尝试从Content-Disposition获取
        if not filename or "." not in filename:
            content_disposition = response.headers.get("content-disposition", "")
            if "filename=" in content_disposition:
                filename = content_disposition.split("filename=")[-1].strip('"\'')
        
        # 获取扩展名
        extension = get_file_extension(filename)
        if not extension:
            content_type = response.headers.get("content-type", "")
            extension = get_extension_from_content_type(content_type.split(";")[0])
            filename = f"file_{uuid.uuid4().hex[:8]}{extension}"
        
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
