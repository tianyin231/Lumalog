# Lumalog

Lumalog 是一个本地优先的减重记录与健康追踪应用，用来记录体重、饮食、运动，并通过 AI 辅助识别食物热量。

## 功能

- 账号系统：邮箱注册、登录、昵称、密码和头像管理
- 多账号隔离：体重、饮食、运动、AI 配置和小米登录态按账号分别存储
- 体重记录：趋势图、当前体重、快速录入、备注
- 饮食记录：手动记录、图片上传、AI 热量识别
- 运动记录：手动记录、小米运动健康同步、运动详情和轨迹地图
- 概览页：今日热量、今日运动、体重趋势、最近运动
- 设置页：用户信息、OpenAI 配置、小米账号连接状态

## 技术栈

- 前端：Vue 3、TypeScript、Vite、Pinia、Vue Router、ECharts、Leaflet、Lucide
- 后端：FastAPI、SQLite、SQLAlchemy、Pydantic
- AI：OpenAI 兼容接口，用于食物图片热量识别
- 运动同步：依赖本地 `Mi-Fitness-Sync-main` 包

## 快速启动

### 环境要求

- Node.js
- Python
- npm

### 安装依赖

```powershell
npm run install:frontend
cd backend
..\Mi-Fitness-Sync-main\.venv\Scripts\python.exe -m pip install -r requirements.txt
cd ..
```

后端脚本默认使用 `Mi-Fitness-Sync-main/.venv` 里的 Python 环境。如果本地还没有这个虚拟环境，请先创建并安装依赖。

### 启动开发服务

方式一：使用根目录脚本分别启动。

```powershell
npm run dev:backend
npm run dev
```

方式二：Windows 下双击 `start.bat`。

默认地址：

- 前端：`http://localhost:7012`
- 后端：`http://localhost:7014`
- API 文档：`http://localhost:7014/docs`

## 默认账号

开发环境会初始化一个默认账号：

- 邮箱：`default@local.lumalog`
- 密码：`lumalog123`

## 配置

AI 食物识别可以在设置页按账号保存，也可以通过环境变量提供默认值：

```env
OPENAI_API_KEY=
OPENAI_BASE_URL=
OPENAI_MODEL=
AUTH_SECRET=
```

小米运动健康登录状态按 Lumalog 账号隔离保存。退出 Lumalog 账号不会自动清除对应的小米授权状态，除非在设置页执行断开或重新登录。

## 数据与隐私

本项目默认使用本地 SQLite 数据库，适合个人自托管或本地开发。准备上传仓库时，不要提交以下内容：

- `backend/weight_minus_minus.db`
- `data/uploads/`
- `backend/uploads/`
- `backend/data/mi_fit/`
- `.env`、`.env.*`
- 本地虚拟环境和依赖目录

这些路径已经在根目录 `.gitignore` 中处理。

## 项目结构

```text
Lumalog/
├── backend/                  # FastAPI 后端
│   ├── app/
│   │   ├── routers/          # API 路由
│   │   ├── models/           # SQLAlchemy 模型
│   │   ├── schemas/          # Pydantic 模型
│   │   └── services/         # AI、小米同步等服务
│   ├── main.py
│   └── requirements.txt
├── frontend/                 # Vue 前端
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   ├── stores/
│   │   └── router/
│   └── package.json
├── Mi-Fitness-Sync-main/     # 小米同步本地依赖
├── data/                     # 本地运行数据
├── package.json
├── start.bat
└── README.md
```

## 第三方开源声明

本项目的小米运动健康同步功能基于 [kevinkwee/Mi-Fitness-Sync](https://github.com/kevinkwee/Mi-Fitness-Sync) 进行二次开发。该项目使用 MIT License，版权归原作者 Michael Elian Kevin 所有。

如果提交 `Mi-Fitness-Sync-main/` 源码，请保留其中原始 `LICENSE` 文件。

## 许可

MIT License
