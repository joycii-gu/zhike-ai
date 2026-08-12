# 知客 ZhiKe AI：W4 数据、隐私与部署说明

## 1. W4 应用数据闭环

W4 版本在现有 7 个 Agent Skills 之上，新增账号隔离与持久化业务对象：用户、客户、原始记录、AI 报告、跟进任务、人工确认反馈事件与 KPI 目标。

```text
注册/登录 → 新建客户分析 → 保存报告 → 创建任务 → 人工确认结果
→ KPI 与工作台更新 → 下次登录继续查看
```

KPI 只根据未撤销的人工确认反馈事件统计；模型生成的分析和建议不会自动计入业绩。

## 2. 数据范围与隐私边界

- 客户原始记录与应用内任务、反馈保存于部署该应用的服务器数据库，并按登录用户隔离。
- 生成 AI 分析时，客户原始记录会被发送到当前配置的第三方模型 API；第三方的数据处理与留存由其服务政策约束。
- 请勿输入身份证号、银行卡号、完整联系方式、合同密钥、账户密码或未经授权的敏感个人信息。
- 应用不在代码仓库中保存 API Key、密码明文或数据库文件。
- 本地 Mock 模式不会调用外部模型；页面会显示实际运行来源。

## 3. 账号与安全策略

- 密码以 PBKDF2-HMAC-SHA256 加盐哈希保存，不保存明文密码。
- 客户、报告、任务与反馈查询均以当前登录用户 ID 过滤。
- 反馈事件含唯一 ID 与创建时间，可撤销，防止误点直接永久影响 KPI。
- 当前为 W4 单实例应用。生产环境建议使用 HTTPS、定期备份数据库、限制服务器 SSH 访问，并在后续迁移到托管 Postgres 与专业身份服务。

## 4. ECS 首次部署

以 Ubuntu ECS 为例，服务器仅需安装 Docker。将仓库克隆到服务器后执行：

```bash
git clone https://github.com/joycii-gu/zhike-ai.git
cd zhike-ai
docker build -t zhike-ai .
docker run -d --name zhike-ai --restart unless-stopped \
  -p 8501:8501 \
  -v $(pwd)/data:/app/data \
  --env-file .env \
  zhike-ai
```

在 ECS 安全组放行 TCP `8501` 后，可以通过：

```text
http://<ECS-公网-IP>:8501
```

访问应用。后续建议使用 Nginx 反向代理到 80/443，并配置 HTTPS 域名。

## 5. 更新与恢复

更新代码时保留 `data/` 目录和 `.env` 文件：

```bash
git pull
docker rm -f zhike-ai
docker build -t zhike-ai .
docker run -d --name zhike-ai --restart unless-stopped \
  -p 8501:8501 -v $(pwd)/data:/app/data --env-file .env zhike-ai
```

不要将 `data/zhike.db`、`.env` 或 `.streamlit/secrets.toml` 上传到 GitHub。
