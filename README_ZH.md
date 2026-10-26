# 大肥鱼标注台（feiyu-openlabel）

多租户视频片段标注平台。管理员发布视频任务，标注员逐帧选择时间段并提交，审核员匿名审核；系统记录按日有效时长，并支持成功/问题视频 CSV 导出。

[English README](README.md) · [实施报告](report.md)

## 核心功能

- 标注员通过空格键设置区间起点/终点，左右方向键逐帧移动，实时查看当前帧。
- 每个区间支持项目预设标签或自由标签；可修改起止时间、标签并删除区间。
- 提交前校验空区间、时间顺序、区间重叠、视频长度、必填标签、预设标签和最短时长。
- 审核员只看到匿名标注员，可播放视频、核对区间并通过或驳回。
- 驳回任务回到原标注员；第三次驳回进入租户管理员裁决。
- 租户管理员可创建、保存、登录和删除标注员/审核员账号。
- 租户管理员可查看待复核视频、通过/失败文件详情、统计图表和 CSV。
- 平台管理员可创建、查看和软删除租户。
- 租户隔离、任务分配、提交快照、审核状态和统计数据均由后端校验。

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue 3、TypeScript、Vite、Element Plus、Pinia、Vue Router |
| 后端 | Python 3.12、FastAPI、Tortoise ORM |
| 数据 | PostgreSQL、FerretDB（MongoDB 兼容）、Redis |
| 媒体 | OpenCV、浏览器原生 Video、Range 流式播放 |
| 部署 | Docker、Docker Compose、Nginx |
| 测试 | Pytest、Vitest、Vue Test Utils、vue-tsc |

## 演示账号

密码统一为 `feiyu`，也可以直接点击登录页的身份按钮：

| 邮箱 | 角色 |
|---|---|
| `Avery.Admin@example.com` | 平台管理员 |
| `Avery.Tenant@example.com` | 租户管理员 |
| `Avery.Annotator@example.com` | 标注员 |
| `Avery.Reviewer@example.com` | 审核员 |

这些是虚构演示账号，不接收真实邮件。本地演示模式由 `FY_DEMO_QUICK_LOGIN` 控制，生产环境必须设为 `false`。

## 环境要求

- Docker Desktop 及 Docker Compose
- 运行前端测试/构建：Node.js 20+、pnpm 10+
- 运行后端测试：Python 3.12+
- 至少约 2 GB 可用内存；Docker 镜像首次构建需要网络

## Docker 启动

确认 Docker Desktop 已经运行，然后在仓库根目录执行。

Windows PowerShell（本地体验，自动开启快捷演示登录）：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\docker-production\start-ce.ps1 -Demo
```

Linux / macOS（本地体验）：

```bash
bash ./docker-production/start-ce.bash --demo
```

启动脚本会自动完成以下工作：

- 首次运行时从模板创建 `docker-production/.env.ce`。
- 生成并写入 64 位十六进制随机 `FY_JWT_SECRET`；后续启动保留原密钥。
- `-Demo` / `--demo` 打开本机快捷演示登录。
- 默认使用 master 自动构建的 `snapshot-ce` 镜像，并通过南京大学 GHCR 镜像站下载；失败时自动重试，然后启动全部服务。

正式部署或共享环境不要加 `-Demo` / `--demo`。脚本会在这种情况下明确关闭快捷登录，正常邮箱密码登录不受影响。

启动后访问 <http://localhost:6600/guis/feiyu/auth.html>。默认端口：前端 `6600`，后端 API `6610`。

当前仓库尚未创建正式 `v*` 发布标签，因此没有 `latest-ce` 镜像；直接使用上述脚本即可。正式发布后，可在 `.env.ce` 中把 `FY_FRONTEND_IMAGE` 和 `FY_BACKEND_IMAGE` 的后缀改为 `latest-ce`。

`.env.ce` 中的四个 `FY_*_IMAGE` 默认指向国内镜像站 `ghcr.nju.edu.cn`。如果你更希望使用 GitHub 官方源，把其中的 `ghcr.nju.edu.cn` 改成 `ghcr.io`。

### 停止与卸载

一键删除本项目容器、镜像、数据目录和 `.env.ce`，保留源码：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\docker-production\clean-ce.ps1 -Yes
```

这条命令删除的是本项目明确列出的资源，不会执行 `docker system prune`，不会删除其他项目的镜像。

可选命令：

```powershell
# 只显示将删除的内容，不实际删除
powershell -NoProfile -ExecutionPolicy Bypass -File .\docker-production\clean-ce.ps1 -DryRun

# 不带 -Yes 时会要求输入 DELETE 二次确认
powershell -NoProfile -ExecutionPolicy Bypass -File .\docker-production\clean-ce.ps1
```

Linux / macOS 一键清理：

```bash
bash ./docker-production/clean-ce.bash --yes
```

只停止容器，保留容器、镜像和数据：

```powershell
docker compose `
  --env-file .\docker-production\.env.ce `
  -f .\docker-production\docker-compose.ce.yaml `
  stop
```

删除容器和网络，保留镜像及 `C:\Users\EDY\tmp\feiyu_ce_*` 数据：

```powershell
docker compose `
  --env-file .\docker-production\.env.ce `
  -f .\docker-production\docker-compose.ce.yaml `
  down
```

同时删除本项目镜像：

```powershell
docker compose `
  --env-file .\docker-production\.env.ce `
  -f .\docker-production\docker-compose.ce.yaml `
  down --rmi all --remove-orphans -v
```

`--rmi all` 会删除前端、后端和数据库镜像，下次启动必须重新下载。`-v` 只删除 Compose 命名卷，本项目使用宿主机目录，数据仍要按 [docker-production/README.md](docker-production/README.md) 的说明手动删除。

如需修改数据目录、端口或密钥，可直接运行脚本生成 `.env.ce` 后再编辑；同一份 `.env.ce` 会持续复用。仅生成配置而不启动服务时，添加 `-NoStart`（PowerShell）或 `--no-start`（Bash）。

如需按当前源码自行构建镜像：

```bash
pnpm --dir apps/web-app install --frozen-lockfile
pnpm --dir apps/web-app build
docker build -f apps/web-app/Dockerfile -t ghcr.nju.edu.cn/angshihan777-droid/feiyu-frontend-ce:snapshot-ce .
docker build -f services/web-api/Dockerfile -t ghcr.nju.edu.cn/angshihan777-droid/feiyu-backend-ce:snapshot-ce .
```

## 本地测试

前端：

```bash
cd apps/web-app
pnpm install --frozen-lockfile
pnpm test:unit --run
pnpm type-check
pnpm build
```

后端：

```bash
cd services/web-api
python -m pytest -q
```

后端完整测试应使用 Python 3.12，并安装 `test` 可选依赖：

```bash
python -m pip install -e ".[test]"
PYTHONPATH=src python -m pytest -q
```

## 项目结构

```text
apps/web-app/
  src/auth/                        登录与认证页面
  src/components/challenge/        视频标注共享面板
  src/components/challenge/video-studio/
                                   播放器、帧控制、区间编辑、审核动作
  src/home/views/challenge/        标注员与审核员页面
  src/home/views/tenant/           租户管理员工作台
  src/home/views/platform/         平台管理员工作台

services/web-api/src/feiyu_app/
  apps/challenge.py                HTTP 路由
  biz/challenge/assignment.py      任务分配
  biz/challenge/submission.py      草稿、提交、媒体
  biz/challenge/review.py          审核状态机
  biz/challenge/admin_review.py    管理员复核
  biz/challenge/reporting.py       统计与 CSV
  biz/challenge/tenant.py          租户人员与视频规则

docker-production/                 CE 版 Docker Compose、Nginx、初始化脚本
report.md                          挑战实施与验证报告
```

## 数据与配置

- 后端业务配置位于 `services/web-api/config/feiyu.yaml` 和 `docker-production/app-config/ce/feiyu.yaml`。
- 环境变量统一使用 `FY_` 前缀。
- 本地上传、日志、Postgres 和 Redis 数据目录由 `docker-production/.env.ce` 配置。
- `.env.ce`、播放器数据、构建产物和依赖目录已被 `.gitignore` 排除，不应提交。
- PostgreSQL 保存用户、任务和审核状态；FerretDB 保存 OpenLABEL 标注文档。

## 视觉资源

登录页角色形象来自[蓝色大肥鱼.com](https://xn--pssy23gqgbz2d718b.com/) 。图片版权归原作者所有，本项目只在演示界面中引用并保留来源链接。

## License

AGPL-3.0，详见 [LICENSE](LICENSE)。
