"""
数据模型定义
"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, HttpUrl


class FileType(str, Enum):
    """支持的文件类型"""
    IMAGE = "image"
    PDF = "pdf"
    WORD = "word"
    AUTO = "auto"  # 自动检测


class WatermarkPosition(str, Enum):
    """水印位置"""
    TILE = "tile"          # 平铺
    CENTER = "center"      # 居中
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"


class WatermarkConfig(BaseModel):
    """水印配置"""
    font_size: int = Field(default=40, ge=10, le=200, description="字体大小")
    font_color: str = Field(default="#808080", description="字体颜色(HEX格式)")
    opacity: float = Field(default=0.3, ge=0.0, le=1.0, description="透明度")
    angle: float = Field(default=-45, ge=-180, le=180, description="旋转角度")
    spacing: int = Field(default=100, ge=20, le=500, description="水印间距(平铺模式)")
    position: WatermarkPosition = Field(default=WatermarkPosition.TILE, description="水印位置")


class WatermarkRequest(BaseModel):
    """水印请求 - URL方式"""
    url: HttpUrl = Field(..., description="文件URL")
    watermark_text: str = Field(..., min_length=1, max_length=200, description="水印文字")
    file_type: FileType = Field(default=FileType.AUTO, description="文件类型")
    config: Optional[WatermarkConfig] = Field(default=None, description="水印配置")


class WatermarkResponse(BaseModel):
    """水印响应"""
    success: bool
    message: str
    download_url: Optional[str] = None
    filename: Optional[str] = None


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskResponse(BaseModel):
    """异步任务响应"""
    task_id: str
    status: TaskStatus
    message: str
    download_url: Optional[str] = None
