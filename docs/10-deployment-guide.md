# ForgeRAG 部署指南

## 1. 文档目的

本文档用于说明 ForgeRAG 第一版的本地部署与运行方式，承接已有需求、架构、API、数据库、可观测性和评测设计。

本文档重点说明：

1. 本地开发环境如何准备。
2. Docker Compose 如何启动核心依赖。
3. `.env` 配置如何管理。
4. 数据库迁移如何执行。
5. 服务启动后如何验证。
6. 常见部署问题如何排查。
7. 第一版部署能力的边界。

本文档不展开 Kubernetes、高可用、生产监控告警、日志采集平台和云原生部署方案。

------

## 2. 部署范围

### 2.1 第一版部署目标

ForgeRAG 第一版部署目标是支持本地开发、课程项目展示和中小规模演示环境。

部署后应能运行以下组件：

| 组件                    | 说明                                      |
| ----------------------- | ----------------------------------------- |
| `forgerag-api`          | FastAPI 后端服务                          |
| `postgres`              | PostgreSQL 业务数据库                     |
| `qdrant`                | Qdrant 向量数据库                         |
| `langfuse`              | RAG / Agent 链路观测工具                  |
| `langfuse dependencies` | Langfuse 运行所需依赖，按官方部署模板接入 |
| `local storage`         | 本地上传文件存储目录                      |

### 2.2 第一版不覆盖范围

第一版暂不处理：

1. Kubernetes 部署。
2. 多副本高可用。
3. 服务注册与发现。
4. 分布式事务。
5. 自动扩缩容。
6. 完整生产监控告警。
7. ELK / Loki 日志平台。
8. Prometheus / Grafana 指标大屏。
9. 云对象存储正式接入。
10. 生产级密钥管理平台。

------

## 3. 推荐目录结构

部署相关文件建议放在项目根目录或 `deploy/` 目录下：

```text
forgerag/
├── app/
├── alembic/
├── scripts/
├── storage/
│   └── uploads/
├── deploy/
│   ├── docker-compose.yml
│   ├── docker-compose.langfuse.yml
│   └── nginx/
├── Dockerfile
├── .env.example
├── .env
├── pyproject.toml
├── alembic.ini
└── README.md
```

说明：

1. `Dockerfile` 用于构建 FastAPI 后端镜像。
2. `docker-compose.yml` 编排后端、PostgreSQL 和 Qdrant。
3. `docker-compose.langfuse.yml` 可单独维护 Langfuse 及其依赖。
4. `.env.example` 提供配置模板。
5. `.env` 存放本地真实配置，不提交到 Git。
6. `storage/uploads/` 用于保存本地上传文件。

------

## 4. 环境要求

本地机器需要准备：

| 工具           | 建议                   |
| -------------- | ---------------------- |
| Docker         | 使用较新稳定版本       |
| Docker Compose | 使用 Docker Compose V2 |
| Git            | 用于拉取项目代码       |
| Python         | 本地非容器开发时使用   |
| Make           | 可选，用于封装常用命令 |

检查命令：

```bash
docker --version
docker compose version
git --version
```

------

## 5. 环境变量配置

### 5.1 配置原则

ForgeRAG 通过 `.env` 管理运行配置。

原则：

1. 不在代码中硬编码数据库密码、模型密钥和服务地址。
2. `.env.example` 可以提交到仓库。
3. `.env` 不应提交到仓库。
4. 不同环境使用不同配置。
5. 配置缺失时应在启动阶段给出明确错误。

### 5.2 `.env.example`

示例：

```env
# Application
APP_NAME=forgerag
APP_ENV=dev
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=INFO

# PostgreSQL
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=forgerag
POSTGRES_USER=forgerag
POSTGRES_PASSWORD=forgerag_password
DATABASE_URL=postgresql+asyncpg://forgerag:forgerag_password@postgres:5432/forgerag

# Qdrant
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_URL=http://qdrant:6333
QDRANT_COLLECTION=forgerag_chunks

# Local Storage
UPLOAD_DIR=/app/storage/uploads
MAX_UPLOAD_SIZE_MB=20

# LLM
LLM_PROVIDER=openai_compatible
LLM_API_BASE=
LLM_API_KEY=
LLM_MODEL=

# Embedding
EMBEDDING_PROVIDER=openai_compatible
EMBEDDING_API_BASE=
EMBEDDING_API_KEY=
EMBEDDING_MODEL=
EMBEDDING_DIM=

# Rerank
RERANK_ENABLED=false
RERANK_PROVIDER=
RERANK_API_BASE=
RERANK_API_KEY=
RERANK_MODEL=

# Langfuse
LANGFUSE_ENABLED=true
LANGFUSE_HOST=http://langfuse:3000
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_ENVIRONMENT=dev

# Observability
OBSERVABILITY_SAMPLE_RATE=1.0
```

说明：

1. 第一版不绑定具体模型厂商。
2. 模型、Embedding、Rerank 均通过配置切换。
3. `RERANK_ENABLED=false` 时，问答流程应降级使用原始检索排序。
4. `LANGFUSE_ENABLED=false` 时，只保留结构化日志。

------

## 6. Dockerfile 设计

第一版后端镜像只负责运行 FastAPI 服务。

示例：

```dockerfile
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml ./
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

说明：

1. 生产化构建可后续优化为多阶段构建。
2. 第一版优先保证简单、可运行、可调试。
3. 依赖管理方式以项目实际使用的 `pyproject.toml` 或 `requirements.txt` 为准。

------

## 7. Docker Compose 设计

### 7.1 核心服务编排

`docker-compose.yml` 建议包含：

```yaml
services:
  forgerag-api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: forgerag-api
    env_file:
      - .env
    ports:
      - "8000:8000"
    volumes:
      - ./storage/uploads:/app/storage/uploads
    depends_on:
      - postgres
      - qdrant
    networks:
      - forgerag-net

  postgres:
    image: postgres:16
    container_name: forgerag-postgres
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - forgerag-postgres-data:/var/lib/postgresql/data
    networks:
      - forgerag-net

  qdrant:
    image: qdrant/qdrant:latest
    container_name: forgerag-qdrant
    ports:
      - "6333:6333"
    volumes:
      - forgerag-qdrant-data:/qdrant/storage
    networks:
      - forgerag-net

volumes:
  forgerag-postgres-data:
  forgerag-qdrant-data:

networks:
  forgerag-net:
    driver: bridge
```

### 7.2 Langfuse 编排方式

Langfuse 及其依赖建议单独放在：

```text
deploy/docker-compose.langfuse.yml
```

接入原则：

1. 优先参考 Langfuse 官方 Docker Compose 模板。
2. 不把 Langfuse 内部依赖细节写死在业务代码中。
3. 后端只通过 `LANGFUSE_HOST`、`LANGFUSE_PUBLIC_KEY`、`LANGFUSE_SECRET_KEY` 连接 Langfuse。
4. Langfuse 不可用时，核心问答流程应降级为结构化日志。

启动时可以使用：

```bash
docker compose -f docker-compose.yml -f deploy/docker-compose.langfuse.yml up -d
```

如果暂不启用 Langfuse：

```env
LANGFUSE_ENABLED=false
```

------

## 8. 启动流程

### 8.1 准备配置

```bash
cp .env.example .env
```

然后修改 `.env` 中的数据库密码、模型配置和 Langfuse 配置。

### 8.2 启动依赖和后端

```bash
docker compose up -d --build
```

如果启用 Langfuse：

```bash
docker compose -f docker-compose.yml -f deploy/docker-compose.langfuse.yml up -d --build
```

### 8.3 查看容器状态

```bash
docker compose ps
```

期望看到：

```text
forgerag-api
forgerag-postgres
forgerag-qdrant
```

Langfuse 开启时，还应看到 Langfuse 相关容器。

------

## 9. 数据库迁移

ForgeRAG 使用 Alembic 管理 PostgreSQL 表结构。

### 9.1 执行迁移

容器启动后执行：

```bash
docker compose exec forgerag-api alembic upgrade head
```

### 9.2 回滚迁移

如需回滚最近一次迁移：

```bash
docker compose exec forgerag-api alembic downgrade -1
```

### 9.3 迁移原则

1. 表结构变更必须通过 Alembic 迁移脚本管理。
2. 不建议手动直接修改数据库结构。
3. 本地调试可以重建数据库卷，但应注意数据会丢失。
4. CI 中可使用临时数据库执行迁移检查。

------

## 10. Qdrant 初始化

第一版建议使用单一 collection：

```text
forgerag_chunks
```

初始化方式可以有两种：

| 方式               | 说明                           |
| ------------------ | ------------------------------ |
| 应用启动时自动检查 | 如果 collection 不存在，则创建 |
| 脚本初始化         | 通过脚本显式创建 collection    |

脚本方式示例：

```bash
docker compose exec forgerag-api python scripts/init_qdrant.py
```

设计要求：

1. collection 名称来自 `QDRANT_COLLECTION`。
2. 向量维度来自 `EMBEDDING_DIM`。
3. 不应在代码中写死 collection 名称和向量维度。
4. Qdrant point ID 建议与 `chunk_id` 对齐。

------

## 11. 服务验证

### 11.1 存活检查

```bash
curl http://localhost:8000/api/v1/health
```

期望返回：

```json
{
  "status": "ok",
  "service": "forgerag-api"
}
```

### 11.2 依赖就绪检查

```bash
curl http://localhost:8000/api/v1/health/ready
```

期望返回类似：

```json
{
  "status": "ok",
  "dependencies": {
    "postgres": "ok",
    "qdrant": "ok",
    "langfuse": "ok"
  }
}
```

说明：

1. PostgreSQL 和 Qdrant 不可用时，应视为核心依赖异常。
2. Langfuse 不可用时，应明确显示依赖异常，但不应阻断普通问答流程。
3. 具体返回结构以 API 实现为准。

### 11.3 API 文档访问

FastAPI 自动文档默认访问：

```text
http://localhost:8000/docs
```

------

## 12. 常用运维命令

### 12.1 查看日志

```bash
docker compose logs -f forgerag-api
```

查看数据库日志：

```bash
docker compose logs -f postgres
```

查看 Qdrant 日志：

```bash
docker compose logs -f qdrant
```

### 12.2 重启服务

```bash
docker compose restart forgerag-api
```

### 12.3 停止服务

```bash
docker compose down
```

### 12.4 停止并删除数据卷

```bash
docker compose down -v
```

注意：`down -v` 会删除 PostgreSQL 和 Qdrant 本地数据，仅适合本地重置环境。

------

## 13. 本地开发模式

如果不使用容器运行后端，也可以只通过 Docker Compose 启动依赖：

```bash
docker compose up -d postgres qdrant
```

本地启动后端：

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

本地开发时 `.env` 中服务地址需要调整：

```env
POSTGRES_HOST=localhost
QDRANT_URL=http://localhost:6333
LANGFUSE_HOST=http://localhost:3000
```

------

## 14. 测试与 CI

### 14.1 本地测试

运行测试：

```bash
pytest
```

建议至少覆盖：

1. 配置加载。
2. 统一响应。
3. 全局异常处理。
4. 知识库管理。
5. 文档管理。
6. RAG 核心链路基础逻辑。
7. Agentic RAG 状态流转。
8. 评测任务执行。
9. Langfuse 降级逻辑。

### 14.2 CI 检查

GitHub Actions 第一版建议执行：

1. 安装依赖。
2. 代码格式检查。
3. 单元测试。
4. Alembic 迁移检查。
5. Docker 构建检查。

第一版 CI 不负责自动部署到生产环境，只作为质量检查入口。

------

## 15. 数据与文件持久化

### 15.1 PostgreSQL

PostgreSQL 数据通过 Docker volume 持久化：

```text
forgerag-postgres-data
```

保存内容：

1. 知识库数据。
2. 文档元数据。
3. chunk 文本。
4. 问答记录。
5. 引用快照。
6. Agentic RAG 摘要。
7. 评测数据和结果。

### 15.2 Qdrant

Qdrant 数据通过 Docker volume 持久化：

```text
forgerag-qdrant-data
```

保存内容：

1. chunk 向量。
2. Qdrant payload。
3. collection 配置。

### 15.3 上传文件

上传文件保存在：

```text
storage/uploads/
```

第一版使用本地文件系统。后续如需生产化，可扩展为对象存储。

------

## 16. 配置与安全注意事项

第一版应遵守以下要求：

1. `.env` 不提交到 Git。
2. 模型 API Key 不写入代码。
3. 数据库密码不写入代码。
4. Langfuse Secret Key 不写入代码。
5. 日志中避免打印完整密钥和敏感配置。
6. 上传目录不直接信任用户文件名。
7. 外部异常不直接暴露原始堆栈给 API 调用方。
8. 演示环境中应使用独立测试密钥和测试数据。

------

## 17. 常见问题排查

### 17.1 后端无法连接 PostgreSQL

检查：

```bash
docker compose ps
docker compose logs postgres
```

重点确认：

1. `POSTGRES_HOST` 是否为 `postgres`。
2. `DATABASE_URL` 是否正确。
3. PostgreSQL 容器是否正常启动。
4. Alembic 迁移是否已执行。

### 17.2 后端无法连接 Qdrant

检查：

```bash
curl http://localhost:6333
docker compose logs qdrant
```

重点确认：

1. `QDRANT_URL` 是否正确。
2. Qdrant 容器是否正常启动。
3. collection 是否已创建。
4. `EMBEDDING_DIM` 是否与 collection 向量维度一致。

### 17.3 Langfuse 不可用

处理方式：

1. 检查 Langfuse 容器是否启动。
2. 检查 `LANGFUSE_HOST` 是否正确。
3. 检查 Public Key 和 Secret Key 是否配置。
4. 本地调试时可临时设置：

```env
LANGFUSE_ENABLED=false
```

Langfuse 不可用时，核心业务流程应继续运行，但 `trace_id` 可以为空。

### 17.4 模型调用失败

检查：

1. `LLM_API_KEY` 是否配置。
2. `LLM_API_BASE` 是否可访问。
3. `LLM_MODEL` 是否正确。
4. 网络代理是否影响请求。
5. 模型服务错误是否已转换为统一错误响应。

### 17.5 数据需要重置

本地开发可执行：

```bash
docker compose down -v
docker compose up -d --build
docker compose exec forgerag-api alembic upgrade head
```

注意：该操作会清空本地 PostgreSQL 和 Qdrant 数据。

------

## 18. 第一版验收标准

部署能力完成后，应满足以下验收标准：

| 验收项         | 标准                                    |
| -------------- | --------------------------------------- |
| Dockerfile     | 可以构建后端镜像                        |
| Docker Compose | 可以启动后端、PostgreSQL、Qdrant        |
| Langfuse       | 可以启动或通过配置关闭                  |
| `.env.example` | 覆盖核心配置项                          |
| 数据库迁移     | Alembic 可以执行到最新版本              |
| 健康检查       | `/api/v1/health` 可访问                 |
| 就绪检查       | `/api/v1/health/ready` 能反映依赖状态   |
| API 文档       | `/docs` 可访问                          |
| 日志           | 后端输出结构化日志                      |
| 数据持久化     | PostgreSQL、Qdrant 数据使用 volume 保存 |
| 测试           | pytest 可以执行基础测试                 |
| CI             | GitHub Actions 可执行基础检查           |

------

## 19. 部署总结

ForgeRAG 第一版部署设计以“简单、可复现、可调试”为核心。

关键结论：

1. 使用 Docker Compose 作为本地开发和演示部署方式。
2. 使用 PostgreSQL 保存结构化业务数据。
3. 使用 Qdrant 保存 chunk 向量。
4. 使用 Langfuse 记录 RAG 和 Agentic RAG 链路。
5. 使用 `.env` 管理运行配置。
6. 使用 Alembic 管理数据库迁移。
7. 使用健康检查接口验证服务和依赖状态。
8. 使用结构化日志兜底排查问题。
9. 第一版不引入 Kubernetes、高可用和复杂运维平台。
10. 后续生产化部署应单独设计云资源、监控告警、日志采集、密钥管理和高可用方案。