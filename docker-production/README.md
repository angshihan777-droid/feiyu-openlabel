# docker-production · CE 生产部署

feiyu-openlabel CE (Community Edition) 的生产部署。独立 compose、独立端口、独立数据卷,默认监听 6600/6610。

EE / SaaS 的部署资产分别在私有仓:
- [feiyu-openlabel-ee](https://github.com/angshihan777-droid/feiyu-openlabel-ee) 仓库的 `docker-production/`
- [feiyu-openlabel-saas](https://github.com/angshihan777-droid/feiyu-openlabel-saas) 仓库的 `docker-production/`

## 目录结构

```
docker-production/
├── README.md                     # 本文档
├── docker-compose.ce.yaml        # CE compose
├── start-ce.ps1                  # Windows 一键初始化 + 启动
├── start-ce.bash                 # Linux/macOS 一键初始化 + 启动
├── clean-ce.ps1                  # Windows 一键彻底清理
├── clean-ce.bash                 # Linux/macOS 一键彻底清理
├── app-config/
│   └── ce/feiyu.yaml           # CE 配置(最小化)
├── nginx-conf/
│   └── ce/app.conf               # 仅业务面
├── scripts/
│   └── ce/init-db.sh             # 建库 feiyu-ce
└── env-templates/
    └── .env.ce.template
```

## 启动

Windows PowerShell（仓库根目录，本地体验）：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\docker-production\start-ce.ps1 -Demo
```

Linux / macOS（仓库根目录，本地体验）：

```bash
bash ./docker-production/start-ce.bash --demo
```

脚本首次运行会自动创建 `.env.ce`、生成并保存随机 JWT 密钥，默认通过南京大学 GHCR 镜像站使用 master 自动构建的 `snapshot-ce` 镜像并启动服务。下载或启动失败会自动重试。重复运行会复用原密钥，不会使已有登录失效。

当前尚未创建正式 `v*` 发布标签，因此 GHCR 上不存在 `latest-ce`。正式发布后，可在 `.env.ce` 中把 `FY_FRONTEND_IMAGE` 和 `FY_BACKEND_IMAGE` 改为相应版本的 `latest-ce`。

四个 `FY_*_IMAGE` 默认指向 `ghcr.nju.edu.cn`。如需 GitHub 官方源，把它们中的域名改为 `ghcr.io`。

正式或共享部署去掉 `-Demo` / `--demo`，脚本会明确关闭快捷登录。只生成配置、不启动容器时使用 `-NoStart` / `--no-start`。

访问 `http://localhost:6600/guis/feiyu/auth.html`
演示账号 `Avery.Tenant@example.com` / 密码 `feiyu`

## 停止 / 重启

只停止容器并保留容器、镜像和数据：

```bash
docker compose --env-file .env.ce -f docker-compose.ce.yaml stop
```

重启已停止的容器：

```bash
docker compose --env-file .env.ce -f docker-compose.ce.yaml restart
```

删除容器和网络，保留镜像与数据：

```bash
docker compose --env-file .env.ce -f docker-compose.ce.yaml down
```

## 卸载

**一键删除本项目全部运行资源（推荐）：**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\docker-production\clean-ce.ps1 -Yes
```

该脚本只会删除本项目容器、网络、本项目镜像、`%USERPROFILE%\tmp\feiyu_ce_*` 数据目录和 `docker-production/.env.ce`，保留源码。不会执行全局 `docker system prune`。

预览删除内容而不实际删除：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\docker-production\clean-ce.ps1 -DryRun
```

Linux / macOS：

```bash
bash ./docker-production/clean-ce.bash --yes
```

**仅删除容器、网络和本项目镜像，保留数据：**

```bash
docker compose --env-file .env.ce -f docker-compose.ce.yaml \
  down --rmi all --remove-orphans -v
```

`--rmi all` 会删除前端、后端、PostgreSQL、FerretDB 和 Redis 镜像。下次启动会重新下载，因此不要把它当作普通的“停止服务”命令。

**彻底删除数据：** Compose 使用宿主机目录而不是命名卷，`down -v` 不会删除它们。确认不需要数据后，再删除：

```powershell
Remove-Item -LiteralPath 'C:\Users\EDY\tmp\feiyu_ce_user_data' -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath 'C:\Users\EDY\tmp\feiyu_ce_media' -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath 'C:\Users\EDY\tmp\feiyu_ce_logs' -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath 'C:\Users\EDY\tmp\feiyu_ce_redis_data' -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath 'C:\Users\EDY\tmp\feiyu_ce_postgres_data' -Recurse -Force -ErrorAction SilentlyContinue
```

删除本地配置和 JWT 密钥：

```powershell
Remove-Item -LiteralPath '.\docker-production\.env.ce' -Force -ErrorAction SilentlyContinue
```

## 镜像地址

默认使用南京大学 GHCR 镜像站：

```text
ghcr.nju.edu.cn
```

GitHub 官方地址是：

```text
ghcr.io
```

两者后面的仓库路径和标签相同，但 Docker 将不同域名视为不同镜像。Compose 当前默认统一使用 `ghcr.nju.edu.cn`，避免一部分镜像下载到官方地址、另一部分下载到镜像站。可在 `.env.ce` 的 `FY_FRONTEND_IMAGE`、`FY_BACKEND_IMAGE`、`FY_POSTGRES_IMAGE`、`FY_FERRETDB_IMAGE` 中查看或修改。

查看当前实际使用的镜像：

```bash
docker compose --env-file .env.ce -f docker-compose.ce.yaml config --images
```

## 数据卷

数据落宿主机的路径由 `.env.ce` 决定(默认 `~/tmp/feiyu_ce_*`)。删除对应目录即可重置。

## CE 镜像如何构建

镜像发布脚本统一走仓根 `scripts/release_docker_image.sh`,CE 通过 `--edition ce`(默认)自动追加 `-ce` 后缀:

```bash
export GITHUB_TOKEN=ghp_xxx   # 需 write:packages scope
scripts/release_docker_image.sh release --version 0.4.0
```

分步命令与全部选项见 `scripts/release_docker_image.sh --help`。CE 单独打 tarball 用 `scripts/build-ce.sh`。

## 已知坑

- **不要同端口跑多版**:CE/EE/SaaS 默认端口已错开,自行改 `.env` 时注意。
- **`.env` 不要入 git**:含宿主机路径与可能的 secret,已在仓库根 `.gitignore` 排除本目录的 `.env.*`。
- **快捷登录仅限本地**:`start-ce` 的 `-Demo` / `--demo` 会开启无密码演示登录,不要用于共享或生产环境。
- **后端 6610 根路径返回 404 是正常的**:直接访问 `http://localhost:6610/` 没有业务路由。请通过前端代理检查快捷登录状态 `http://localhost:6600/api/v1/b/u/a/noau/demo-login/status`，或查看 `docker compose ps` 中 `web-api` 是否为 `healthy`。
