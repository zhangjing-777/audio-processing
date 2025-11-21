# Audio Processing Backend API

音频处理后端服务，提供钢琴扒谱、音频分离、多轨扒谱等功能。

## 功能特性

### 1. 钢琴扒谱 (PianoTrans)
- 支持格式: MP3, WAV, M4A 等
- 自动缓存处理结果
- 返回 MIDI 文件 URL

### 2. 音频分离 (Spleeter)
- 支持格式: MP3, WAV, M4A 等
- 可选分离模式:
  - 2轨: 人声 + 伴奏
  - 4轨: 人声 + 鼓 + 贝斯 + 其他
  - 5轨: 人声 + 鼓 + 贝斯 + 钢琴 + 其他
- 自动缓存处理结果
- 返回 ZIP 压缩包 URL

### 3. 多轨扒谱 (YourMT3)
- 支持格式: MP3, WAV, M4A 等
- 自动缓存处理结果
- 返回 MIDI 文件 URL

## 技术栈

- **FastAPI**: 现代化的 Python Web 框架
- **SQLAlchemy**: 异步 ORM
- **PostgreSQL**: 数据库 (Supabase)
- **AWS S3**: 文件存储
- **RunPod**: AI 模型推理服务
- **Docker**: 容器化部署

## 快速开始

### 1. 环境准备

克隆项目:
```bash
git clone <repository_url>
cd audio-processing-backend
```

配置环境变量:
```bash
cp .env.example .env
# 编辑 .env 文件,填入实际的配置信息
```

### 2. 使用 Docker 部署 (推荐)

启动服务:
```bash
docker-compose up -d
```

查看日志:
```bash
docker-compose logs -f
```

停止服务:
```bash
docker-compose down
```

### 3. 本地开发

安装依赖:
```bash
pip install -r requirements.txt
```

运行服务:
```bash
python -m app.main
# 或
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API 文档

服务启动后,访问以下地址查看 API 文档:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API 端点

### 钢琴扒谱

**POST** `/api/piano/transcribe`

上传音频文件进行钢琴扒谱。

**请求:**
- Content-Type: `multipart/form-data`
- Body: `file` (音频文件)

**响应示例:**
```json
{
  "status": "success",
  "message": "钢琴扒谱完成",
  "midi_url": "https://qiupupu.s3.ap-southeast-1.amazonaws.com/PianoTrans/xxx.mid",
  "from_cache": false,
  "job_id": "914ee860-8fdd-45d3-af48-a57deab3d46e-e1"
}
```

### 音频分离

**POST** `/api/spleeter/separate`

上传音频文件进行音轨分离。

**请求:**
- Content-Type: `multipart/form-data`
- Body:
  - `file` (音频文件)
  - `stems` (可选, 默认: 2, 可选值: 2/4/5)
  - `format` (可选, 默认: mp3)
  - `bitrate` (可选, 默认: 192k)

**响应示例:**
```json
{
  "status": "success",
  "message": "音频分离完成",
  "download_url": "https://qiupupu.s3.ap-southeast-1.amazonaws.com/Spleeter/xxx.zip",
  "files": [
    {
      "name": "vocals.mp3",
      "size_kb": 9833.31
    },
    {
      "name": "accompaniment.mp3",
      "size_kb": 9833.31
    }
  ],
  "size_mb": 18.57,
  "from_cache": false,
  "job_id": "8c5e3df6-d5c1-4eba-a64e-74719071f969-e1"
}
```

### 多轨扒谱

**POST** `/api/yourmt3/transcribe`

上传音频文件进行多轨扒谱。

**请求:**
- Content-Type: `multipart/form-data`
- Body: `file` (音频文件)

**响应示例:**
```json
{
  "status": "success",
  "message": "多轨扒谱完成",
  "midi_url": "https://qiupupu.s3.ap-southeast-1.amazonaws.com/yourmt3/xxx.mid",
  "from_cache": false,
  "job_id": "a9e16e02-dcb9-49dd-8a66-93303cb45718-e1"
}
```

## 使用示例

### cURL

```bash
# 钢琴扒谱
curl -X POST http://localhost:8000/api/piano/transcribe \
  -F "file=@/path/to/audio.mp3"

# 音频分离 (2轨)
curl -X POST http://localhost:8000/api/spleeter/separate \
  -F "file=@/path/to/audio.mp3" \
  -F "stems=2" \
  -F "format=mp3" \
  -F "bitrate=192k"

# 多轨扒谱
curl -X POST http://localhost:8000/api/yourmt3/transcribe \
  -F "file=@/path/to/audio.mp3"
```

### Python

```python
import requests

# 钢琴扒谱
with open('audio.mp3', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/piano/transcribe',
        files={'file': f}
    )
    print(response.json())

# 音频分离
with open('audio.mp3', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/spleeter/separate',
        files={'file': f},
        data={'stems': 2, 'format': 'mp3', 'bitrate': '192k'}
    )
    print(response.json())
```

### JavaScript (Fetch API)

```javascript
// 钢琴扒谱
const formData = new FormData();
formData.append('file', fileInput.files[0]);

fetch('http://localhost:8000/api/piano/transcribe', {
  method: 'POST',
  body: formData
})
.then(response => response.json())
.then(data => console.log(data));

// 音频分离
const formData2 = new FormData();
formData2.append('file', fileInput.files[0]);
formData2.append('stems', '2');
formData2.append('format', 'mp3');
formData2.append('bitrate', '192k');

fetch('http://localhost:8000/api/spleeter/separate', {
  method: 'POST',
  body: formData2
})
.then(response => response.json())
.then(data => console.log(data));
```

## 项目结构

```
audio-processing-backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # 主应用入口
│   ├── config.py            # 配置管理
│   ├── database.py          # 数据库连接
│   ├── models.py            # 数据库模型
│   ├── schemas.py           # Pydantic 模型
│   ├── services/            # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── s3_service.py
│   │   ├── piano_service.py
│   │   ├── spleeter_service.py
│   │   └── yourmt3_service.py
│   └── routers/             # API 路由
│       ├── __init__.py
│       ├── piano.py
│       ├── spleeter.py
│       └── yourmt3.py
├── .env                     # 环境变量 (不提交到 git)
├── .env.example             # 环境变量示例
├── .gitignore
├── requirements.txt         # Python 依赖
├── Dockerfile              # Docker 镜像
├── docker-compose.yml      # Docker Compose 配置
└── README.md               # 项目文档
```

## 环境变量说明

| 变量名 | 说明 | 示例 |
|--------|------|------|
| AWS_ACCESS_KEY_ID | AWS 访问密钥 ID | AKIAIOSFODNN7EXAMPLE |
| AWS_SECRET_ACCESS_KEY | AWS 访问密钥 | wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY |
| AWS_REGION | AWS 区域 | ap-southeast-1 |
| S3_BUCKET_NAME | S3 存储桶名称 | qiupupu |
| DB_HOST | 数据库主机 | db.xxx.supabase.co |
| DB_NAME | 数据库名称 | postgres |
| DB_USER | 数据库用户 | postgres |
| DB_PASSWORD | 数据库密码 | your_password |
| DB_PORT | 数据库端口 | 5432 |
| RUNPOD_API_KEY | RunPod API 密钥 | rpa_xxx |
| RUNPOD_PIANO_ENDPOINT | Piano API 端点 | https://api.runpod.ai/v2/xxx/run |
| RUNPOD_SPLEETER_ENDPOINT | Spleeter API 端点 | https://api.runpod.ai/v2/xxx/run |
| RUNPOD_YOURMT3_ENDPOINT | YourMT3 API 端点 | https://api.runpod.ai/v2/xxx/run |
| DEBUG | 调试模式 | false |

## 缓存机制

系统会自动缓存所有处理结果:

1. 计算上传文件的 MD5 哈希值
2. 检查数据库中是否存在相同哈希值的已完成记录
3. 如果存在,直接返回缓存的 S3 URL
4. 如果不存在,上传到 S3 并调用 RunPod API 处理
5. 处理完成后保存结果到数据库

**注意**: Spleeter 服务的缓存还会匹配 `stems` 参数,只有文件和参数都相同才会命中缓存。

## 健康检查

```bash
# 全局健康检查
curl http://localhost:8000/health

# 各服务健康检查
curl http://localhost:8000/api/piano/health
curl http://localhost:8000/api/spleeter/health
curl http://localhost:8000/api/yourmt3/health
```

## 常见问题

### 1. 数据库连接失败

检查数据库配置是否正确,确保 Supabase 数据库可以访问。

### 2. S3 上传失败

检查 AWS 凭证是否正确,确保有足够的权限访问 S3 存储桶。

### 3. RunPod API 调用失败

- 检查 API Key 是否正确
- 检查端点 URL 是否正确
- 确保 RunPod 服务正常运行

### 4. 处理时间过长

音频处理需要一定时间,特别是较长的音频文件。默认超时时间为 300 秒。

## 许可证

MIT License

## 联系方式

如有问题或建议,请提交 Issue。
