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

- Node.js 和 npm
- Python 3.12 或更高版本
- Chrome 或 Edge：用于小米账号二次验证窗口

### 安装依赖

本项目建议统一使用 `Mi-Fitness-Sync-main/.venv` 作为后端虚拟环境。下面的命令会安装前端依赖、创建后端虚拟环境，并安装后端与小米同步所需的 Python 包。

macOS / Linux：

```bash
npm run install:frontend
cd Mi-Fitness-Sync-main
python3 -m venv .venv
source .venv/bin/activate
pip install -r ../backend/requirements.txt
cd ..
```

Windows PowerShell：

```powershell
npm run install:frontend
cd Mi-Fitness-Sync-main
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r ..\backend\requirements.txt
cd ..
```

安装完成后，可以用下面的命令确认小米二次验证所需的 `playwright` 已可用。

macOS / Linux：

```bash
Mi-Fitness-Sync-main/.venv/bin/python -c "from playwright.sync_api import sync_playwright; print('playwright ok')"
```

Windows PowerShell：

```powershell
.\Mi-Fitness-Sync-main\.venv\Scripts\python.exe -c "from playwright.sync_api import sync_playwright; print('playwright ok')"
```

### 启动开发服务

推荐使用项目自带启动脚本。脚本会检查基础环境、准备前端依赖、创建或更新后端虚拟环境，并同时启动前后端。

macOS / Linux：

```bash
chmod +x start.sh
./start.sh
```

Windows：

```powershell
.\start.bat
```

下面是手动启动方式，适合需要单独排查前端或后端问题时使用。

需要开两个终端窗口：一个启动后端，一个启动前端。

后端请固定从 `backend` 目录启动。这样数据库、上传文件和小米登录态都会保存到稳定的位置，避免因为启动目录不同导致状态不一致。

macOS / Linux：

```bash
cd backend
../Mi-Fitness-Sync-main/.venv/bin/python -m uvicorn main:app --reload --reload-dir app --port 7014
```

Windows PowerShell：

```powershell
cd backend
..\Mi-Fitness-Sync-main\.venv\Scripts\python.exe -m uvicorn main:app --reload --reload-dir app --port 7014
```

如果你已经激活了虚拟环境，也可以在 `backend` 目录中直接使用：

```bash
python -m uvicorn main:app --reload --reload-dir app --port 7014
```

前端在项目根目录启动：

```bash
npm run dev
```

Windows 用户也可以双击 `start.bat` 一次启动前后端。

> 说明：根目录的 `npm run dev:backend` 使用 Windows 虚拟环境路径。macOS / Linux 推荐使用上面的后端启动命令。

默认地址：

- 前端：`http://localhost:7012`
- 后端：`http://localhost:7014`
- API 文档：`http://localhost:7014/docs`

## 生产部署

线上不要使用 `npm run dev` 作为前端服务。生产环境应先执行 `npm run build` 生成 `frontend/dist`，再由 FastAPI 后端直接托管静态文件和 API。这样只需要暴露一个端口，加载速度也会明显优于 Vite 开发服务器。

下面的一行式命令适合宝塔 Node 项目的“自定义启动命令”。请把 `/www/codex_work/Lumalog` 替换成服务器上的实际项目目录：

```bash
bash -lc 'cd /www/codex_work/Lumalog || exit 1; export HOME="$PWD/.home" PIP_CACHE_DIR="$PWD/.pip-cache" NPM_CONFIG_CACHE="$PWD/.npm-cache"; mkdir -p "$HOME" "$PIP_CACHE_DIR" "$NPM_CONFIG_CACHE"; cd frontend && npm install --cache ../.npm-cache && npm run build || exit 1; test -f dist/index.html || exit 1; cd ../backend && ../Mi-Fitness-Sync-main/.venv/bin/python -m pip install -r requirements.txt || exit 1; exec ../Mi-Fitness-Sync-main/.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 7014'
```

生产访问地址：

- 应用入口：`http://服务器IP:7014/`
- API 文档：`http://服务器IP:7014/docs`

宝塔或反向代理中，项目端口填写 `7014`。前端页面和 `/api` 都从同一个端口提供，不需要再单独开放 `7012`。

首次部署前请确保后端虚拟环境已用 Python 3.12 或更高版本创建：

```bash
cd /www/codex_work/Lumalog
python3.12 -m venv Mi-Fitness-Sync-main/.venv
```

## 默认账号

开发环境会初始化一个默认账号：

- 邮箱：`default@local.lumalog`
- 密码：`lumalog123`

## 配置

AI 食物识别可以在设置页按账号保存配置。也可以通过环境变量提供默认值：

```env
OPENAI_API_KEY=
OPENAI_BASE_URL=
OPENAI_MODEL=
AUTH_SECRET=
```

## 小米运动健康同步

1. 按上面的方式启动后端，确保后端运行在 `Mi-Fitness-Sync-main/.venv` 虚拟环境中。
2. 打开前端 `http://localhost:7012`，登录 Lumalog 账号。
3. 进入设置页，在“小米运动健康同步”中输入小米账号和密码，点击“登录小米”。
4. 如果小米要求二次验证，请在后端自动弹出的 Chrome / Edge 临时窗口中完成验证，不要复制链接到普通浏览器打开。
5. 验证完成后，前端会自动确认；如果没有自动完成，可以点击“我已完成验证”。

小米登录态会保存到当前后端工作目录下的 `data/mi_fit/user_<Lumalog用户ID>.json`。因此请固定从 `backend` 目录启动后端；否则从项目根目录启动时会读写另一份 `data/mi_fit/`，看起来像登录状态丢失或突然恢复。

当前支持：

- 普通账号密码登录：成功后直接保存登录态。
- 通知型二次验证：通过后端弹出的 Chrome / Edge 窗口完成。

当前限制：

- 图形验证码或短信 step2 暂不支持在网页中直接完成。如果小米触发这类验证，需要先使用命令行流程完成登录，或等待后续补充验证码输入流程。
- 退出 Lumalog 账号不会自动清除小米授权状态。如需断开小米账号，请在设置页点击退出小米登录。
- 不需要执行 `playwright install chromium`。本项目使用本机已经安装的 Chrome 或 Edge。

## 数据与隐私

本项目默认使用本地 SQLite 数据库，适合个人自托管或本地开发。以下文件包含个人数据或本地环境信息，请不要提交到公开仓库：

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
