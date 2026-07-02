# Mi Fitness Sync 中文使用记录

本项目用于从小米运动健康（Mi Fitness）云端读取运动记录，并导出为 `fit` / `gpx` / `tcx`。

## 当前环境

- Windows PowerShell
- Python 3.14.6
- 项目虚拟环境：`.venv`
- 已安装本项目：`pip install -e .`
- 已额外安装：`playwright`

进入项目后先激活虚拟环境：

```powershell
cd E:\codex_work\WeightMinusMinus\Mi-Fitness-Sync-main
.\.venv\Scripts\Activate.ps1
```

验证命令：

```powershell
mi-fitness-sync --help
```

## 登录

普通登录：

```powershell
mi-fitness-sync login
```

如果小米要求浏览器或 App 二次验证，使用本地改造后的登录方式：

```powershell
mi-fitness-sync login --wait-verification --no-proxy
```

流程：

1. 输入小米账号和密码
2. 工具自动打开临时 Chrome / Edge 窗口
3. 在自动打开的窗口里完成小米验证
4. 回到终端按回车
5. 成功后会保存登录状态

登录状态保存位置：

```text
C:\Users\86166\.mi_fitness_sync\auth\auth.json
```

这个文件包含登录凭证，不要提交到仓库。

## 代理注意事项

本机 Windows 系统代理曾指向：

```text
127.0.0.1:65532
```

如果代理不可用，`requests` 会报 `ProxyError`。本地已给命令增加 `--no-proxy` 参数，用于忽略系统代理。

建议访问小米接口时都加：

```powershell
--no-proxy
```

## 查看账号状态

```powershell
mi-fitness-sync auth-status
```

如果登录态过期，重新执行：

```powershell
mi-fitness-sync login --wait-verification --no-proxy
```

## 列出运动

列出最近 10 条：

```powershell
mi-fitness-sync list-activities --limit 10 --no-proxy
```

JSON 输出，方便脚本处理：

```powershell
mi-fitness-sync list-activities --limit 10 --json --no-proxy
```

按时间过滤：

```powershell
mi-fitness-sync list-activities --since 2026-07-01 --limit 50 --json --no-proxy
```

## 导出运动

运动 ID 来自 `list-activities` 的 `ID` 列，例如：

```text
749117614:outdoor_riding:1782904974
```

导出 FIT：

```powershell
mi-fitness-sync export-activity "749117614:outdoor_riding:1782904974" --format fit --no-proxy
```

指定输出路径：

```powershell
mkdir .\exports -ErrorAction SilentlyContinue
mi-fitness-sync export-activity "749117614:outdoor_riding:1782904974" --format fit --output ".\exports\2026-07-01-riding.fit" --no-proxy
```

导出 GPX：

```powershell
mi-fitness-sync export-activity "749117614:outdoor_riding:1782904974" --format gpx --output ".\exports\2026-07-01-riding.gpx" --no-proxy
```

注意：复制 ID 时不要带末尾空格。

## 已验证成功的命令

```powershell
mi-fitness-sync list-activities --limit 10
mi-fitness-sync export-activity "749117614:outdoor_riding:1782904974" --format fit --no-proxy
mi-fitness-sync export-activity "749117614:outdoor_riding:1782904974" --format gpx --output ".\exports\2026-07-01-riding.gpx" --no-proxy
```

已成功生成：

```text
C:\Users\86166\.mi_fitness_sync\exports\Outdoor_Riding_20260701_192254.fit
exports\2026-07-01-riding.gpx
```

## 二次开发入口

命令行入口：

```text
src\mi_fitness_sync\cli\app.py
```

登录相关：

```text
src\mi_fitness_sync\auth\client.py
src\mi_fitness_sync\auth\state.py
src\mi_fitness_sync\auth\store.py
```

运动列表、详情、云端请求：

```text
src\mi_fitness_sync\activity\client.py
src\mi_fitness_sync\activity\transport.py
```

导出逻辑：

```text
src\mi_fitness_sync\export\render.py
```

本地已改造点：

- `login --wait-verification`：支持打开临时浏览器完成小米二次验证
- `--no-proxy`：登录、列出、详情、导出、上传命令可忽略系统代理
- 活动请求客户端支持 `trust_env=False`

## 后续自动化建议

最小自动导出逻辑：

1. `list-activities --json --no-proxy`
2. 遍历活动 ID
3. 已存在的导出文件跳过
4. 新活动执行 `export-activity --format fit --no-proxy`
5. 用 Windows 任务计划程序定时运行

如果 `list-activities` 报认证失败，说明登录态可能过期，需要重新登录。
