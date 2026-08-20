# 知客 ZhiKe AI：W4 数据、隐私与 ECS 部署说明

## 1. W4 应用架构

W4 版本以独立 Web 应用交付，不再以 Streamlit 作为部署入口：

```text
浏览器（React 响应式前端）
          │ HTTPS
          ▼
Nginx（80/443，静态资源与 /api 反向代理）
          │
          ▼
FastAPI（认证、客户、任务、KPI、Agent 调度）
          │
          ├── MiniMax API / 已配置模型服务
          └── SQLite 持久化卷（账户、客户、报告、任务、人工反馈）
```

前端适配电脑和手机；后端复用既有七步业务 Skills Workflow。原有 `app.py` 作为历史 Streamlit 原型保留，不是 ECS 最终运行入口。

## 2. 数据与隐私边界

- 客户原始记录、AI 报告、跟进任务、人工确认反馈和 KPI 数据保存于 ECS 挂载的 SQLite 数据卷，并按登录用户 ID 隔离。
- 生成 AI 分析时，客户原始记录会发送至当前配置的第三方模型 API；第三方的数据处理与留存以其服务政策为准。
- 不要输入身份证号、银行卡号、完整联系方式、合同密钥、账户密码或未授权敏感信息。
- 密码以 PBKDF2-HMAC-SHA256 加盐哈希保存；浏览器只持有 HttpOnly、签名且有过期时间的会话 Cookie。
- KPI 仅统计业务员确认的反馈事件。AI 的分析和建议不会自动计入业绩；确认事件可在后续版本保留撤销与审计记录。
- 不要将 `.env`、真实 API Key、会话密钥或 `data/` 数据目录上传到 GitHub。

## 3. 首次 ECS 部署

以下以 Ubuntu ECS 为例。赛事 ECS 不可使用 `80`、`443`、`8080`、`8443`，本项目将 Web 服务公开在 TCP `3000`；请确认服务器防火墙或安全组允许 TCP `3000`。服务器需预先安装 Docker Engine 与 Docker Compose Plugin。

```bash
git clone https://github.com/joycii-gu/zhike-ai.git
cd zhike-ai
cp .env.example .env
nano .env
```

在 `.env` 中至少填写：

```dotenv
MINIMAX_API_KEY=你的真实密钥
MINIMAX_BASE_URL=https://api.minimaxi.com/v1
MINIMAX_MODEL=MiniMax-M2.7
ZHIKE_ENV=production
ZHIKE_SESSION_SECRET=使用 openssl rand -hex 32 生成的随机值
ZHIKE_COOKIE_SECURE=false
```

启动应用：

```bash
docker compose up -d --build
docker compose ps
curl http://127.0.0.1:3000/api/health
```

访问 `http://<ECS 公网 IP>:3000/` 可以完成首次可访问部署。当前赛事服务器禁用 80/443，因此本次演示使用 HTTP 与 `ZHIKE_COOKIE_SECURE=false`。若后续迁移到可使用 HTTPS 的环境，应将其改为 `true` 并重启。

## 4. 持久化与更新

`docker-compose.yml` 使用名为 `zhike_data` 的 Docker 数据卷保存数据库。更新代码不会删除该卷：

```bash
git pull
docker compose up -d --build
docker compose ps
```

除非完成备份且确认不再需要业务数据，不要执行 `docker compose down -v`。建议在路演前备份数据卷：

```bash
docker run --rm -v zhike-ai_zhike_data:/data -v "$(pwd)":/backup \
  alpine tar czf /backup/zhike-data-backup.tgz -C /data .
```

## 5. 上线验收清单

- [ ] `docker compose ps` 中 `api` 显示 healthy，`web` 为 running。
- [ ] `http://<IP>:3000/api/health` 返回 `status: ok`。
- [ ] 能注册账号、登录、创建客户分析并看到七步执行结果。
- [ ] 在客户详情中确认一次跟进反馈，业务驾驶舱 KPI 随之变化。
- [ ] 手机浏览器能正常完成登录、查看驾驶舱和新建分析。
- [ ] `.env` 未被提交到仓库，真实 API Key 与 `ZHIKE_SESSION_SECRET` 仅存在服务器。

## 6. 本地开发

后端：

```bash
pip install -r backend/requirements.txt
$env:ZHIKE_COOKIE_SECURE="false"
uvicorn backend.main:app --reload --port 8000
```

前端：

```bash
cd frontend
npm install
npm run dev
```

在浏览器打开 Vite 输出的地址。开发服务器会将 `/api` 自动代理到 `http://localhost:8000`。
