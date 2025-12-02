# 水印服务 (Watermark Service)

基于 FastAPI 构建的水印服务，支持图片和文档的水印处理。

## 功能特性

- ✅ 支持多种图片格式：JPG, PNG, GIF, BMP, WEBP, TIFF
- ✅ 支持文档格式：PDF, DOCX
- ✅ 支持 URL 下载方式和文件上传方式
- ✅ 支持异步任务处理
- ✅ 线程池并发处理
- ✅ 自动清理过期文件
- ✅ 可配置的下载 URL 前缀

## 安装

```bash
pip install -r requirements.txt
```

## 运行

### 本地运行

```bash
# 开发模式
python main.py

# 或使用 uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Docker 部署

#### 使用 Docker Compose（推荐）

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

#### 单独使用 Docker

```bash
# 构建镜像
docker build -t watermarker .

# 运行容器
docker run -d \
  --name watermarker \
  -p 8000:8000 \
  -e DOWNLOAD_URL_PREFIX=http://your-domain.com/download \
  -v watermark_output:/app/output \
  watermarker

# 查看日志
docker logs -f watermarker
```

#### Docker 环境变量配置

在 `docker-compose.yml` 中修改 `environment` 部分：

```yaml
environment:
  - DOWNLOAD_URL_PREFIX=http://your-domain.com/download
  - MAX_WORKERS=10
  - MAX_FILE_SIZE=52428800
  - FILE_RETENTION_SECONDS=3600
```

#### 自定义字体

1. 将字体文件放入 `fonts/` 目录
2. 在 `docker-compose.yml` 中取消注释字体挂载和环境变量：

```yaml
volumes:
  - ./fonts:/usr/share/fonts/custom
environment:
  - CUSTOM_FONT_PATH=/usr/share/fonts/custom/your-font.ttf
```

## 环境变量配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| WATERMARK_HOST | 0.0.0.0 | 服务监听地址 |
| WATERMARK_PORT | 8000 | 服务端口 |
| DOWNLOAD_URL_PREFIX | http://localhost:8000/download | 下载 URL 前缀 |
| MAX_WORKERS | 10 | 线程池大小 |
| MAX_FILE_SIZE | 52428800 | 最大文件大小（字节，默认50MB） |
| FILE_RETENTION_SECONDS | 3600 | 文件保留时间（秒） |
| CUSTOM_FONT_PATH | 空 | 自定义中文字体路径 |

## 中文支持

服务自动检测并使用系统中文字体，支持以下系统：

**Windows:**
- 微软雅黑 (msyh.ttc)
- 黑体 (simhei.ttf)
- 宋体 (simsun.ttc)
- 楷体 (simkai.ttf)

**Linux:**
- 文泉驿微米黑/正黑
- Noto Sans CJK
- 文鼎字体

**macOS:**
- 苹方 (PingFang)
- 华文黑体

### 自定义字体

如需使用特定字体，设置环境变量：

```bash
# Windows
set CUSTOM_FONT_PATH=C:/path/to/your/font.ttf

# Linux/macOS
export CUSTOM_FONT_PATH=/path/to/your/font.ttf
```

## API 接口

### 1. URL 方式添加水印

**POST** `/api/watermark/url`

```json
{
  "url": "https://example.com/image.png",
  "watermark_text": "机密文件",
  "file_type": "auto",
  "config": {
    "font_size": 40,
    "font_color": "#808080",
    "opacity": 0.3,
    "angle": -45,
    "spacing": 100,
    "position": "tile"
  }
}
```

### 2. 文件上传方式添加水印

**POST** `/api/watermark/file`

使用 `multipart/form-data` 格式：
- `file`: 上传的文件
- `watermark_text`: 水印文字
- `file_type`: 文件类型 (auto/image/pdf/word)
- `font_size`: 字体大小
- `font_color`: 字体颜色
- `opacity`: 透明度
- `angle`: 旋转角度
- `spacing`: 水印间距
- `position`: 水印位置 (tile/center/top_left/top_right/bottom_left/bottom_right)

### 3. 异步任务方式

**POST** `/api/watermark/async` - 创建异步任务
**GET** `/api/task/{task_id}` - 查询任务状态

### 4. 其他接口

- **GET** `/download/{filename}` - 下载处理后的文件
- **GET** `/api/config` - 获取服务配置
- **GET** `/health` - 健康检查

## 水印配置说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| font_size | int | 40 | 字体大小 (10-200) |
| font_color | string | #808080 | 字体颜色 (HEX格式) |
| opacity | float | 0.3 | 透明度 (0.0-1.0) |
| angle | float | -45 | 旋转角度 (-180 到 180) |
| spacing | int | 100 | 水印间距 (20-500，平铺模式生效) |
| position | string | tile | 水印位置 |

### 水印位置选项

- `tile`: 平铺（全页面覆盖）
- `center`: 居中
- `top_left`: 左上角
- `top_right`: 右上角
- `bottom_left`: 左下角
- `bottom_right`: 右下角

## API 文档

启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 示例

### Python 示例

```python
import requests

# URL方式
response = requests.post(
    "http://localhost:8000/api/watermark/url",
    json={
        "url": "https://example.com/image.png",
        "watermark_text": "仅供内部使用",
        "config": {
            "opacity": 0.5,
            "position": "tile"
        }
    }
)
print(response.json())

# 文件上传方式
with open("document.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/watermark/file",
        files={"file": f},
        data={
            "watermark_text": "机密",
            "opacity": 0.3
        }
    )
print(response.json())
```

### cURL 示例

```bash
# URL方式
curl -X POST "http://localhost:8000/api/watermark/url" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com/image.png","watermark_text":"测试水印"}'

# 文件上传
curl -X POST "http://localhost:8000/api/watermark/file" \
  -F "file=@image.png" \
  -F "watermark_text=测试水印"
```

## License

MIT
