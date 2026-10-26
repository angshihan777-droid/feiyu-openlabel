# 快速启动

## 系统环境

```bash
# 确认docker已经安装
docker --version
```

## clone 代码

```bash
git clone https://github.com/angshihan777-droid/feiyu-openlabel.git
```

## 一键启动 CE

回到仓库根目录执行以下任一命令。脚本会自动创建 `.env.ce`、生成随机 JWT 密钥，并通过国内 GHCR 镜像站使用 `master` 自动构建的 `snapshot-ce` 镜像启动服务，不需要手动修改文件。网络失败会自动重试。

Windows PowerShell（本地体验）：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\docker-production\start-ce.ps1 -Demo
```

Linux / macOS（本地体验）：

```bash
bash ./docker-production/start-ce.bash --demo
```

`-Demo` / `--demo` 只用于本机演示；正式部署去掉该参数。脚本重复运行时会复用已有 `FY_JWT_SECRET`，不会让登录令牌莫名失效。

如果只需要生成配置文件、暂不启动，添加 `-NoStart` / `--no-start`。生成后可按需编辑 `docker-production/.env.ce` 中的路径和端口。

## 访问

浏览器打开 `http://localhost:6600/guis/feiyu/home.html`(EE/SaaS 换 6700/6800)

- 账号:`prod@feiyu.example.com`
- 密码:`feiyu`

首次启动会自动建库并写入管理员账号,数据卷落在 `.env` 里配置的宿主机目录(默认 `~/tmp/feiyu_ce_*`)。停止/重置见 `docker-production/README.md`。
