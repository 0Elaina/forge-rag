# ForgeRAG 测试策略

## 1. 文档目的

本文档用于定义 ForgeRAG 第一版测试策略，承接已有需求、架构、数据库、API、RAG 核心链路、Agentic RAG、评测、可观测性和部署设计。

本文档重点说明：

1. ForgeRAG 第一版需要测试哪些内容。
2. 单元测试、集成测试、链路测试和评测任务如何分工。
3. 如何隔离外部模型、Qdrant、Langfuse 等依赖。
4. 如何在本地和 CI 中执行测试。
5. 第一版测试能力的验收标准。

本文档不展开具体测试代码实现，也不重复定义 API 字段、数据库字段和 RAG 流程细节。

------

## 2. 测试目标

ForgeRAG 测试策略的核心目标是：保证系统主链路可运行、关键逻辑可验证、外部依赖可隔离、回归问题可尽早发现。

具体目标：

| 目标      | 说明                                                |
| --------- | --------------------------------------------------- |
| 功能正确  | 核心业务逻辑符合需求和接口设计                      |
| 链路可用  | 文档入库、检索、问答、Agentic RAG、评测主链路可运行 |
| 异常可控  | 参数错误、业务异常和外部依赖异常返回统一结果        |
| 数据一致  | PostgreSQL、Qdrant 与业务 ID 的关联符合设计         |
| 观测可测  | `request_id`、`trace_id`、日志和降级逻辑可验证      |
| CI 可执行 | 基础测试可在 GitHub Actions 中自动运行              |

------

## 3. 测试边界

### 3.1 覆盖范围

第一版测试覆盖：

```text
配置加载
  → 统一响应
  → 全局异常
  → Repository
  → Service
  → 文档处理
  → 向量入库
  → 检索
  → Rerank
  → 基础 RAG
  → Agentic RAG
  → 自动化评测
  → 可观测性
  → API 接口
  → CI 检查
```

### 3.2 不覆盖范围

第一版暂不做：

1. 大规模压测。
2. 复杂性能基准测试。
3. 生产级混沌测试。
4. 完整安全渗透测试。
5. 多租户权限测试。
6. Kubernetes 部署测试。
7. 真实大模型效果稳定性测试。
8. 完整浏览器端到端测试。

------

## 4. 测试分层

ForgeRAG 第一版测试分为四层。

| 测试类型 | 目标                                   | 外部依赖                 |
| -------- | -------------------------------------- | ------------------------ |
| 单元测试 | 验证函数、类、核心规则                 | 全部 mock                |
| 集成测试 | 验证数据库、Repository、API 与依赖连接 | 使用测试数据库或容器     |
| 链路测试 | 验证 RAG / Agentic RAG 主流程          | 模型与部分外部服务可替身 |
| 评测测试 | 验证评测任务、指标和结果保存           | 使用小型固定样本         |

优先级：

```text
单元测试 > 集成测试 > 链路测试 > 评测测试 > 慢速端到端测试
```

第一版应避免所有测试都依赖真实模型服务，否则测试会慢、不稳定且成本不可控。

------

## 5. 推荐测试目录

建议目录结构：

```text
tests/
├── conftest.py
├── unit/
│   ├── test_config.py
│   ├── test_response.py
│   ├── test_exceptions.py
│   ├── test_prompt.py
│   ├── test_splitter.py
│   ├── test_retrieval.py
│   ├── test_rerank.py
│   └── test_agent_nodes.py
├── integration/
│   ├── test_repository.py
│   ├── test_knowledge_base_api.py
│   ├── test_document_api.py
│   ├── test_retrieval_api.py
│   ├── test_qa_api.py
│   └── test_evaluation_api.py
├── chain/
│   ├── test_ingestion_flow.py
│   ├── test_basic_rag_flow.py
│   ├── test_agentic_rag_flow.py
│   └── test_evaluation_flow.py
└── fixtures/
    ├── documents/
    ├── evaluation_samples.json
    └── fake_model_outputs.json
```

说明：

1. `unit/` 放快速、稳定、无真实外部依赖的测试。
2. `integration/` 放数据库、API、Repository 和依赖连接测试。
3. `chain/` 放主链路测试。
4. `fixtures/` 放测试文档、评测样本和模型替身输出。

------

## 6. 测试标记

建议使用 pytest markers 区分测试类型：

```ini
[pytest]
markers =
    unit: fast unit tests
    integration: database or api integration tests
    chain: rag or agentic rag flow tests
    slow: slow tests
    external: tests requiring real external services
```

常用命令：

```bash
pytest -m unit
pytest -m integration
pytest -m "not external"
pytest
```

CI 默认执行：

```bash
pytest -m "not external"
```

真实外部模型测试只在本地手动执行，不作为第一版 CI 必跑项。

------

## 7. 测试环境

### 7.1 本地测试环境

本地可以使用两种方式：

| 方式                | 说明                                  |
| ------------------- | ------------------------------------- |
| 纯 mock 测试        | 不启动外部依赖，适合单元测试          |
| Docker Compose 测试 | 启动 PostgreSQL、Qdrant，适合集成测试 |

推荐本地依赖启动：

```bash
docker compose up -d postgres qdrant
```

运行测试：

```bash
pytest
```

### 7.2 测试配置

建议提供独立测试配置：

```env
APP_ENV=test
DATABASE_URL=postgresql+asyncpg://forgerag:forgerag_password@localhost:5432/forgerag_test
QDRANT_COLLECTION=forgerag_chunks_test
LANGFUSE_ENABLED=false
RERANK_ENABLED=false
```

测试环境要求：

1. 不使用正式数据库。
2. 不写入正式 Qdrant collection。
3. 默认关闭真实 Langfuse。
4. 默认不调用真实 LLM。
5. 测试数据可重复初始化和清理。

------

## 8. 外部依赖隔离策略

ForgeRAG 测试中应隔离以下外部依赖：

| 依赖       | 隔离方式                                     |
| ---------- | -------------------------------------------- |
| LLM        | 使用 FakeLLM 或 mock client                  |
| Embedding  | 使用固定维度的 FakeEmbedding                 |
| Rerank     | 使用规则排序或 mock rerank result            |
| Qdrant     | 单元测试 mock，集成测试可使用测试 collection |
| Langfuse   | 使用 NoopTraceClient 或 mock client          |
| 文件存储   | 使用临时目录                                 |
| PostgreSQL | 使用测试数据库或事务回滚                     |

### 8.1 FakeEmbedding

FakeEmbedding 应返回固定维度向量，保证测试稳定。

要求：

1. 相同文本返回相同向量。
2. 向量维度与测试 collection 一致。
3. 不访问真实模型服务。

### 8.2 FakeLLM

FakeLLM 应根据输入返回固定回答。

适用场景：

1. 测试 Prompt 构造。
2. 测试 QA 流程状态。
3. 测试拒答逻辑。
4. 测试引用结构。

### 8.3 NoopTraceClient

NoopTraceClient 用于替代 Langfuse。

要求：

1. 不访问真实 Langfuse。
2. 返回可为空的 `trace_id`。
3. 不阻断核心流程。
4. 可用于验证 Langfuse 降级逻辑。

------

## 9. 单元测试策略

单元测试用于验证不依赖真实外部服务的核心逻辑。

第一版至少覆盖：

| 模块         | 测试重点                         |
| ------------ | -------------------------------- |
| 配置管理     | 配置加载、默认值、缺失配置       |
| 统一响应     | 成功响应、失败响应、分页响应     |
| 异常处理     | 业务异常、参数异常、外部依赖异常 |
| 文本清洗     | 空白、换行、无效字符处理         |
| 文本切分     | chunk 数量、重叠、来源元数据     |
| Prompt       | 模板变量、上下文编号、拒答约束   |
| 检索结果处理 | 过滤阈值、排序、空结果           |
| Rerank       | 启用、关闭、异常降级             |
| 引用构造     | 引用顺序、chunk 关联、快照       |
| Agent 节点   | 状态输入输出、条件判断           |
| 评测评分     | 命中率、引用数量、失败状态       |
| 脱敏逻辑     | API Key、密钥、敏感字段不输出    |

单元测试要求：

1. 运行速度快。
2. 不依赖真实数据库。
3. 不依赖真实模型。
4. 不依赖真实 Qdrant。
5. 适合每次提交自动执行。

------

## 10. Repository 测试策略

Repository 测试用于验证 PostgreSQL 数据访问逻辑。

覆盖内容：

1. 创建知识库。
2. 查询知识库列表和详情。
3. 更新知识库状态。
4. 保存文档元数据。
5. 保存 chunk。
6. 保存问答记录。
7. 保存引用快照。
8. 保存 Agent run 和 step。
9. 保存评测任务和结果。
10. 常用索引字段查询。
11. 软删除和物理删除策略。

测试要求：

1. 使用测试数据库。
2. 每个测试之间数据隔离。
3. 可通过事务回滚或测试后清理恢复状态。
4. 不直接连接开发或演示数据库。

------

## 11. API 测试策略

API 测试用于验证接口行为、响应结构和错误码。

覆盖内容：

| 接口模块       | 测试重点                         |
| -------------- | -------------------------------- |
| System         | `/health`、`/health/ready`       |
| Knowledge Base | 创建、列表、详情、更新、删除     |
| Document       | 上传、详情、状态、删除、重新处理 |
| Retrieval      | 检索成功、空结果、非法知识库     |
| QA             | 成功回答、拒答、模型异常         |
| Agent          | 成功流程、拒答流程、最大迭代限制 |
| Evaluation     | 创建任务、执行任务、查询结果     |

API 测试应验证：

1. HTTP 状态码。
2. `success` 字段。
3. `code` 字段。
4. `message` 字段。
5. `data` 结构。
6. `request_id` 是否存在。
7. 核心链路是否返回或关联 `trace_id`。
8. 异常响应不暴露内部堆栈。

------

## 12. RAG 链路测试策略

RAG 链路测试用于验证基础 RAG 主流程是否可运行。

覆盖流程：

```text
文档解析
  → 文本切分
  → chunk 保存
  → Embedding
  → Qdrant 写入
  → 问题向量化
  → 向量检索
  → Rerank
  → Prompt 构造
  → LLM 生成
  → 引用返回
```

重点断言：

1. 文档状态从 `uploaded` 变为 `processing`，最终为 `completed` 或 `failed`。
2. chunk 能正确保存到 PostgreSQL。
3. Qdrant point payload 包含 `knowledge_base_id`、`document_id`、`chunk_id`。
4. 检索必须限定知识库范围。
5. 检索为空不视为系统异常。
6. Rerank 异常时可以降级。
7. Prompt 只使用选中的上下文。
8. 引用来源与最终上下文一致。
9. 上下文不足时返回拒答或无法回答。
10. 问答记录保存 `qa_record_id`、`request_id`、`trace_id`。

------

## 13. Agentic RAG 测试策略

Agentic RAG 测试用于验证状态流转和条件路由。

覆盖节点：

1. `AnalyzeQuestion`
2. `RewriteQuery`
3. `Retrieve`
4. `Rerank`
5. `CheckRetrieval`
6. `CheckContext`
7. `GenerateAnswer`
8. `DirectAnswer`
9. `RefuseAnswer`
10. `HandleError`

重点断言：

1. 问题需要知识库支持时进入检索流程。
2. 明显无需检索的问题可以进入直接回答。
3. 检索结果不足时可以触发二次检索。
4. 达到 `max_iterations` 后不得继续检索。
5. 上下文不足时进入拒答。
6. 生成回答时引用来自最终上下文。
7. 每个关键节点写入状态摘要。
8. `agent_runs` 保存最终状态。
9. `agent_steps` 保存节点摘要。
10. 节点异常时进入可控失败状态。

------

## 14. 自动化评测测试策略

评测模块测试用于验证评测任务能稳定执行和记录结果。

覆盖内容：

1. 创建评测数据集。
2. 创建评测样本。
3. 创建评测任务。
4. 运行基础 RAG 评测。
5. 运行 Agentic RAG 评测。
6. 保存 `evaluation_results`。
7. 统计成功数和失败数。
8. 计算规则评分。
9. 保存 `qa_record_id`、`agent_run_id`、`trace_id`。
10. 单条样本失败不导致整个任务失败。

第一版测试样本应保持小规模，例如 3 到 5 条，避免测试过慢。

------

## 15. 可观测性测试策略

可观测性测试用于验证日志、Trace 和降级行为。

覆盖内容：

1. 请求进入时生成 `request_id`。
2. 客户端传入 `X-Request-Id` 时优先使用该值。
3. 核心响应返回 `request_id`。
4. RAG、Agentic RAG、评测记录关联 `trace_id`。
5. Langfuse 不可用时核心流程继续执行。
6. `trace_id` 为空时业务记录仍可保存。
7. 结构化日志携带关键业务 ID。
8. 日志和 Trace 不记录 API Key、数据库密码和 Secret Key。

------

## 16. CI 测试策略

GitHub Actions 第一版建议执行：

```text
安装依赖
  → 代码格式检查
  → 静态检查
  → 单元测试
  → Alembic 迁移检查
  → Docker 构建检查
```

CI 默认不执行真实外部模型调用。

建议 CI 命令：

```bash
pytest -m "not external"
alembic upgrade head
docker build -t forgerag-api:test .
```

CI 失败应能区分：

1. 依赖安装失败。
2. 代码格式失败。
3. 单元测试失败。
4. 数据库迁移失败。
5. Docker 构建失败。

------

## 17. 测试数据管理

测试数据应满足：

1. 数据量小。
2. 内容固定。
3. 可重复执行。
4. 不依赖真实企业私有数据。
5. 不包含密钥、个人隐私或敏感配置。

建议测试数据：

| 类型                | 示例                   |
| ------------------- | ---------------------- |
| 文本文档            | 一小段项目规范         |
| Markdown 文档       | 带标题和段落的说明文档 |
| 评测样本            | 3 到 5 条固定问题      |
| Fake LLM 输出       | 固定回答和拒答案例     |
| Fake Embedding 输出 | 固定维度向量           |

------

## 18. 测试通过标准

第一版测试通过标准：

| 模块          | 标准                                      |
| ------------- | ----------------------------------------- |
| 配置          | 测试环境配置可正常加载                    |
| 响应          | 成功和失败响应结构一致                    |
| 异常          | 常见异常能返回统一错误码                  |
| Repository    | 核心表可完成基础读写                      |
| API           | 核心接口可通过基础测试                    |
| 文档处理      | 文档可生成 chunk 或记录失败原因           |
| 检索          | 能按知识库返回候选结果或空结果            |
| Rerank        | 能正常排序或降级                          |
| QA            | 能返回答案、引用或拒答                    |
| Agent         | 能完成主要状态流转                        |
| Evaluation    | 能执行小型评测任务                        |
| Observability | `request_id`、`trace_id` 和降级行为可验证 |
| CI            | GitHub Actions 可执行基础检查             |

------

## 19. 第一版实施优先级

建议按以下顺序补充测试：

1. 配置、响应、异常测试。
2. Repository 基础测试。
3. 知识库和文档 API 测试。
4. 文本清洗、切分、引用构造测试。
5. 检索、Rerank、Prompt 测试。
6. 基础 RAG 链路测试。
7. Agentic RAG 节点和流程测试。
8. 评测任务测试。
9. 可观测性和 Langfuse 降级测试。
10. CI 测试流程。

------

## 20. 测试总结

ForgeRAG 第一版测试策略以“轻量、稳定、可持续执行”为核心。

关键结论：

1. 使用 pytest 作为主要测试框架。
2. 单元测试优先，保证核心规则稳定。
3. 集成测试验证数据库、API 和关键依赖。
4. RAG 链路测试验证文档入库、检索、重排、生成和引用。
5. Agentic RAG 测试重点验证状态流转和条件路由。
6. 评测测试验证小型评测任务可重复执行。
7. 外部模型、Qdrant、Langfuse 应支持 mock 或测试替身。
8. CI 默认不依赖真实模型调用。
9. 每个核心功能新增时，应同步补充测试用例。
10. 测试能力服务于持续迭代，而不是一次性验收。