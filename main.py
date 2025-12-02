"""
FastAPI 水印服务主入口
支持图片和文档水印处理
"""
import uuid
import asyncio
from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

import config
from models import (
    WatermarkConfig, WatermarkRequest, WatermarkResponse,
    FileType, TaskStatus, TaskResponse
)
from utils.file_handler import (
    download_file, detect_file_type, get_file_extension,
    generate_output_filename, save_output_file, get_download_url,
    cleanup_old_files
)
from services.watermark_service import add_watermark


# 线程池
thread_pool = ThreadPoolExecutor(max_workers=config.MAX_WORKERS)

# 任务存储
tasks: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时清理旧文件
    cleanup_old_files()
    
    # 启动定时清理任务
    cleanup_task = asyncio.create_task(periodic_cleanup())
    
    yield
    
    # 关闭时清理
    cleanup_task.cancel()
    thread_pool.shutdown(wait=False)


async def periodic_cleanup():
    """定期清理过期文件"""
    while True:
        await asyncio.sleep(300)  # 每5分钟清理一次
        cleanup_old_files()


app = FastAPI(
    title="水印服务 API",
    description="支持图片(JPG/PNG/GIF/BMP/WEBP)和文档(PDF/DOCX)水印处理",
    version="1.0.0",
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def process_watermark_sync(
    file_data: bytes,
    text: str,
    file_type: str,
    file_extension: str,
    watermark_config: WatermarkConfig
) -> bytes:
    """同步处理水印（在线程池中执行）"""
    return add_watermark(
        file_data=file_data,
        text=text,
        file_type=file_type,
        config=watermark_config,
        file_extension=file_extension
    )


async def process_watermark_async(
    file_data: bytes,
    text: str,
    file_type: str,
    file_extension: str,
    watermark_config: WatermarkConfig
) -> bytes:
    """异步处理水印"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        thread_pool,
        process_watermark_sync,
        file_data, text, file_type, file_extension, watermark_config
    )


@app.post("/api/watermark/url", response_model=WatermarkResponse, summary="URL方式添加水印")
async def add_watermark_by_url(request: WatermarkRequest):
    """
    通过URL下载文件并添加水印
    
    - **url**: 文件URL地址
    - **watermark_text**: 水印文字内容
    - **file_type**: 文件类型 (auto/image/pdf/word)
    - **config**: 水印配置（可选）
    """
    try:
        # 下载文件
        file_data, original_filename, extension = await download_file(str(request.url))
        
        # 检查文件大小
        if len(file_data) > config.MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="文件大小超过限制")
        
        # 确定文件类型
        if request.file_type == FileType.AUTO:
            file_type = detect_file_type(extension)
            if file_type == "unknown":
                raise HTTPException(status_code=400, detail=f"不支持的文件类型: {extension}")
        else:
            file_type = request.file_type.value
        
        # 获取水印配置
        watermark_config = request.config or WatermarkConfig()
        
        # 处理水印
        result_data = await process_watermark_async(
            file_data=file_data,
            text=request.watermark_text,
            file_type=file_type,
            file_extension=extension,
            watermark_config=watermark_config
        )
        
        # 保存输出文件
        output_filename = generate_output_filename(original_filename)
        save_output_file(result_data, output_filename)
        
        # 生成下载URL
        download_url = get_download_url(output_filename)
        
        return WatermarkResponse(
            success=True,
            message="水印添加成功",
            download_url=download_url,
            filename=output_filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@app.post("/api/watermark/file", response_model=WatermarkResponse, summary="文件上传方式添加水印")
async def add_watermark_by_file(
    file: UploadFile = File(..., description="要添加水印的文件"),
    watermark_text: str = Form(..., description="水印文字"),
    file_type: FileType = Form(default=FileType.AUTO, description="文件类型"),
    font_size: int = Form(default=40, description="字体大小"),
    font_color: str = Form(default="#808080", description="字体颜色"),
    opacity: float = Form(default=0.3, description="透明度"),
    angle: float = Form(default=-45, description="旋转角度"),
    spacing: int = Form(default=100, description="水印间距"),
    position: str = Form(default="tile", description="水印位置")
):
    """
    通过文件上传添加水印
    
    支持的文件格式:
    - 图片: jpg, jpeg, png, gif, bmp, webp, tiff
    - 文档: pdf, docx
    """
    try:
        # 读取文件内容
        file_data = await file.read()
        
        # 检查文件大小
        if len(file_data) > config.MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="文件大小超过限制")
        
        # 获取文件扩展名
        original_filename = file.filename or "unknown"
        extension = get_file_extension(original_filename)
        
        # 确定文件类型
        if file_type == FileType.AUTO:
            detected_type = detect_file_type(extension)
            if detected_type == "unknown":
                raise HTTPException(status_code=400, detail=f"不支持的文件类型: {extension}")
            actual_file_type = detected_type
        else:
            actual_file_type = file_type.value
        
        # 构建水印配置
        from models import WatermarkPosition
        watermark_config = WatermarkConfig(
            font_size=font_size,
            font_color=font_color,
            opacity=opacity,
            angle=angle,
            spacing=spacing,
            position=WatermarkPosition(position)
        )
        
        # 处理水印
        result_data = await process_watermark_async(
            file_data=file_data,
            text=watermark_text,
            file_type=actual_file_type,
            file_extension=extension,
            watermark_config=watermark_config
        )
        
        # 保存输出文件
        output_filename = generate_output_filename(original_filename)
        save_output_file(result_data, output_filename)
        
        # 生成下载URL
        download_url = get_download_url(output_filename)
        
        return WatermarkResponse(
            success=True,
            message="水印添加成功",
            download_url=download_url,
            filename=output_filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@app.post("/api/watermark/async", response_model=TaskResponse, summary="异步任务方式添加水印")
async def add_watermark_async(
    request: WatermarkRequest,
    background_tasks: BackgroundTasks
):
    """
    异步方式处理水印，返回任务ID，可通过任务ID查询处理状态
    """
    task_id = uuid.uuid4().hex
    
    # 初始化任务状态
    tasks[task_id] = {
        "status": TaskStatus.PENDING,
        "message": "任务已创建",
        "download_url": None
    }
    
    # 添加后台任务
    background_tasks.add_task(
        process_watermark_task,
        task_id,
        request
    )
    
    return TaskResponse(
        task_id=task_id,
        status=TaskStatus.PENDING,
        message="任务已创建，请通过任务ID查询处理状态"
    )


async def process_watermark_task(task_id: str, request: WatermarkRequest):
    """后台处理水印任务"""
    try:
        tasks[task_id]["status"] = TaskStatus.PROCESSING
        tasks[task_id]["message"] = "正在处理中..."
        
        # 下载文件
        file_data, original_filename, extension = await download_file(str(request.url))
        
        # 确定文件类型
        if request.file_type == FileType.AUTO:
            file_type = detect_file_type(extension)
        else:
            file_type = request.file_type.value
        
        watermark_config = request.config or WatermarkConfig()
        
        # 处理水印
        result_data = await process_watermark_async(
            file_data=file_data,
            text=request.watermark_text,
            file_type=file_type,
            file_extension=extension,
            watermark_config=watermark_config
        )
        
        # 保存输出文件
        output_filename = generate_output_filename(original_filename)
        save_output_file(result_data, output_filename)
        
        # 更新任务状态
        tasks[task_id]["status"] = TaskStatus.COMPLETED
        tasks[task_id]["message"] = "处理完成"
        tasks[task_id]["download_url"] = get_download_url(output_filename)
        
    except Exception as e:
        tasks[task_id]["status"] = TaskStatus.FAILED
        tasks[task_id]["message"] = f"处理失败: {str(e)}"


@app.get("/api/task/{task_id}", response_model=TaskResponse, summary="查询任务状态")
async def get_task_status(task_id: str):
    """查询异步任务的处理状态"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = tasks[task_id]
    return TaskResponse(
        task_id=task_id,
        status=task["status"],
        message=task["message"],
        download_url=task["download_url"]
    )


@app.get("/download/{filename}", summary="下载文件")
async def download_file_endpoint(filename: str):
    """下载已处理的文件"""
    file_path = config.OUTPUT_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在或已过期")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream"
    )


@app.get("/api/config", summary="获取服务配置")
async def get_config():
    """获取当前服务配置"""
    return {
        "max_file_size": config.MAX_FILE_SIZE,
        "max_file_size_mb": config.MAX_FILE_SIZE / (1024 * 1024),
        "file_retention_seconds": config.FILE_RETENTION_SECONDS,
        "supported_image_formats": list(config.SUPPORTED_IMAGE_EXTENSIONS),
        "supported_document_formats": list(config.SUPPORTED_DOCUMENT_EXTENSIONS),
        "max_workers": config.MAX_WORKERS,
        "download_url_prefix": config.DOWNLOAD_URL_PREFIX
    }


@app.get("/health", summary="健康检查")
async def health_check():
    """服务健康检查"""
    return {"status": "healthy", "service": "watermark-service"}


@app.get("/api/debug/fonts", summary="字体诊断")
async def debug_fonts():
    """检查可用字体"""
    import glob
    from pathlib import Path
    from services.watermark_service import CHINESE_FONT_PATHS, _find_cjk_fonts
    
    results = {
        "predefined_fonts": {},
        "dynamic_fonts": [],
        "all_fonts_in_system": []
    }
    
    # 检查预定义字体
    for font_path in CHINESE_FONT_PATHS:
        results["predefined_fonts"][font_path] = Path(font_path).exists()
    
    # 动态查找的字体
    results["dynamic_fonts"] = _find_cjk_fonts()
    
    # 列出 /usr/share/fonts 下所有文件
    try:
        all_fonts = glob.glob("/usr/share/fonts/**/*", recursive=True)
        results["all_fonts_in_system"] = [f for f in all_fonts if Path(f).is_file()]
    except Exception as e:
        results["all_fonts_in_system"] = [f"Error: {e}"]
    
    return results


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=True
    )
