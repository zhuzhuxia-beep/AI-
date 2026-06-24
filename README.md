# 🕰️ AI 老照片时光机

**TRAE AI 创造力大赛 · 生活娱乐赛道 · 造点新花样**

上传一张老照片，AI 帮你修复、上色、生成动态回忆短片——让尘封的记忆重新活过来。

---

## 项目结构

```
web-old-photo-time-machine/
├── frontend/                  # React + Vite 前端
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Home.jsx       # 首页（功能介绍 + 作品画廊 + 数据统计）
│   │   │   ├── Upload.jsx     # 上传 + 修复对比（多步骤进度反馈）
│   │   │   └── Result.jsx     # 故事模板 + TTS + 短片合成（进度可视化）
│   │   ├── services/
│   │   │   └── api.js         # API 调用封装 + 故事模板
│   │   ├── App.jsx            # 路由
│   │   └── index.css          # Tailwind + 全局样式
│   ├── vite.config.js         # Vite 配置（API 代理）
│   └── package.json
├── backend/                   # Python FastAPI 后端
│   ├── app/
│   │   ├── main.py            # FastAPI 入口（静态文件挂载）
│   │   ├── routers/
│   │   │   ├── upload.py      # 照片上传 + 画廊接口 + JSON 持久化
│   │   │   ├── restore.py     # 修复接口
│   │   │   ├── story.py       # 故事配音
│   │   │   └── video.py       # 视频合成
│   │   └── services/
│   │       ├── restoration.py  # 多阶段修复引擎（降噪+划痕修复+上色+调色）
│   │       ├── tts.py          # TTS 配音（Edge TTS）
│   │       ├── video_composer.py # Ken Burns 动态短片合成
│   │       └── kling_api.py    # 可灵 AI 视频生成（可选）
│   ├── uploads/               # 上传照片存储
│   ├── outputs/               # 输出文件
│   └── requirements.txt
├── creative-proposal.html     # 创意提案（报名用）
├── demo-preview.html          # Demo 运行效果展示
├── start.bat                  # 一键启动脚本
└── README.md
```

---

## 快速启动

### 前提条件

- Node.js >= 18
- Python >= 3.10
- FFmpeg（用于视频合成，[下载](https://ffmpeg.org/download.html)）

### 启动方式

**方式一：双击一键启动**

```bash
双击 start.bat
```

脚本会自动检查环境、安装依赖、启动前后端服务并打开浏览器。

**方式二：分别启动**

```bash
# 终端1 - 后端
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 终端2 - 前端
cd frontend
npx vite --host
```

### 访问地址

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:5173 |
| 后端 API | http://localhost:8000 |
| API 文档 | http://localhost:8000/docs |

---

## 技术栈

### 前端
- React 19 + Vite 8
- Tailwind CSS 4
- React Router 7
- Axios + react-dropzone

### 后端
- Python 3.11 + FastAPI
- OpenCV / Pillow（图像处理：降噪、划痕修复、上色、调色）
- Edge TTS（免费中文语音合成）
- FFmpeg（Ken Burns 动态效果 + 背景音乐 + 字幕合成）

---

## Demo 功能

### 核心功能
- ✅ 照片上传（拖拽/点击，支持 JPG/PNG/WebP/BMP）
- ✅ 多阶段 AI 修复：边缘保持降噪 → 划痕检测修复 → CLAHE 对比度增强 → 自适应锐化
- ✅ 智能上色：灰度图自动检测 + 自然色调映射（阴影冷色、中间暖色、高光黄色）
- ✅ 自动白平衡 + 怀旧色彩调色
- ✅ 修复前后对比滑块（自动播放 + 触摸支持）
- ✅ 故事模板（4 种场景快速填充）
- ✅ AI 配音（Edge TTS 中文语音）
- ✅ Ken Burns 动态效果短片（缓慢缩放 + 平移，让照片"活"过来）
- ✅ 情感分析 + 氛围背景音乐生成
- ✅ 自动字幕烧录
- ✅ 视频下载 + 分享

### 体验优化
- ✅ 多步骤进度反馈（修复过程 + 视频合成过程可视化）
- ✅ 作品画廊展示（悬停对比修复前后 + 视频播放模态框）
- ✅ 数据统计动画（数字滚动效果）
- ✅ 友好错误处理 + 一键重试
- ✅ 状态持久化（JSON 文件存储，重启不丢失）
- ✅ 响应式设计（移动端适配）

---

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/upload` | 上传照片 |
| POST | `/api/restore/{id}` | 修复 + 上色 |
| GET | `/api/photo/{id}` | 获取照片状态 |
| POST | `/api/story/{id}` | 生成故事配音 |
| POST | `/api/video/{id}` | 生成回忆短片 |
| GET | `/api/gallery` | 获取作品画廊 |
| GET | `/api/health` | 健康检查 |

---

## 报名信息

- **赛道**：生活娱乐 / 造点新花样
- **报名时间**：2026.06.16 - 07.15
- **提交方式**：TRAE 官方中文社区 · 大赛报名专区发帖
