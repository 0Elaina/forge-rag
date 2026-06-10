# ForgeRAG 架构设计

## 1. 文档目的

本文档用于描述 ForgeRAG 的系统架构设计，承接 `docs/01-project-overview.md` 和 `docs/02-requirements-analysis.md` 中已经明确的项目定位、需求边界和技术约束。

本文档重点回答以下问题：

1. ForgeRAG 采用怎样的整体架构。
2. 后端代码如何分层。
3. RAG、Agentic RAG、评测和可观测性模块如何协作。
4. PostgreSQL、Qdrant、Langfuse、模型服务等组件如何划分职责。
5. 项目目录结构如何组织，才能支撑后续开发。

本文档不重复展开项目背景、完整需求列表、详细 API 字段、数据库字段和 Prompt 细节。这些内容分别由项目概述、需求分析、数据库设计、接口设计、RAG 链路设计和 Agentic RAG 设计文档负责。

------

## 2. 架构设计原则

ForgeRAG 的架构设计遵循以下原则：

1. **后端能力优先**

   系统定位为 RAG 后端能力服务，不绑定具体 Web 页面。前端、业务后端、自动化脚本和智能 Agent 都通过 API 调用系统能力。

2. **单体优先，模块清晰**

   当前阶段采用单体后端应用，不做微服务拆分。系统通过清晰的目录、分层和模块边界保证可维护性。

3. **核心链路闭环优先**

   架构优先服务于以下主链路：

   ```text
   文档入库 → 向量检索 → Rerank → 带引用问答 → Agentic RAG → 评测 → 观测
   ```

4. **业务逻辑与基础设施隔离**

   业务流程不直接依赖外部服务 SDK。数据库、向量库、模型服务和 Langfuse 等外部依赖统一封装在 Infrastructure 层。

5. **可配置、可替换、可扩展**

   LLM、Embedding、Rerank、切分策略、检索参数、Prompt 模板和观测工具都应通过配置或抽象接口管理，避免硬编码。

6. **关键链路默认可观测**

   文档处理、检索、问答、Agentic RAG 和评测流程都应保留 `request_id` 或 `trace_id`，便于问题定位和效果分析。

------

## 3. 总体架构

ForgeRAG 采用分层单体架构。外部调用方通过 REST API 访问 FastAPI 服务，服务内部通过业务层组织流程，通过核心能力层执行 RAG 和 Agentic RAG 逻辑，通过基础设施层访问 PostgreSQL、Qdrant、模型服务、文件存储和 Langfuse。

```text
调用方
  ├── 前端应用
  ├── 业务后端服务
  ├── 自动化脚本
  └── 智能 Agent
        │
        ▼
FastAPI API 层
        │
        ▼
Service 业务编排层
        │
        ├── Repository 数据访问层 ─── PostgreSQL
        │
        └── Core 核心能力层
              ├── 文档解析与切分
              ├── Embedding
              ├── Retrieval
              ├── Rerank
              ├── RAG QA
              ├── Agentic RAG Graph
              └── Evaluation
                    │
                    ▼
Infrastructure 基础设施层
  ├── Qdrant
  ├── LLM / Embedding / Rerank 模型服务
  ├── Langfuse
  ├── 文件存储
  └── 外部工具客户端
```

### 3.1 架构组件职责

| 组件           | 职责                                                |
| -------------- | --------------------------------------------------- |
| FastAPI        | 提供 REST API、参数校验、接口文档                   |
| Service        | 编排知识库、文档、问答、评测等业务流程              |
| Core           | 承载 RAG、Agentic RAG、Prompt、评测等核心逻辑       |
| Repository     | 封装 PostgreSQL 数据访问                            |
| Infrastructure | 封装 Qdrant、模型服务、Langfuse、文件存储等外部依赖 |
| PostgreSQL     | 存储业务元数据和结构化业务数据                      |
| Qdrant         | 存储 chunk 向量并执行语义检索                       |
| Langfuse       | 记录 Trace、Span、模型调用和评测观测数据            |
| Docker Compose | 编排本地开发和演示环境                              |

------

## 4. 后端分层架构

ForgeRAG 后端采用以下分层结构：

```text
API Layer
Schema Layer
Service Layer
Repository Layer
Core Layer
Infrastructure Layer
Common Layer
```

### 4.1 各层职责

| 层             | 职责                                                         | 不应负责                             |
| -------------- | ------------------------------------------------------------ | ------------------------------------ |
| API            | 接收请求、参数校验、调用 Service、返回统一响应               | 不写业务流程，不直接访问数据库和模型 |
| Schema         | 定义请求、响应和 DTO                                         | 不写业务逻辑                         |
| Service        | 编排业务流程、处理业务规则、控制事务边界                     | 不直接写外部 SDK 调用细节            |
| Repository     | 封装数据库增删改查                                           | 不处理 RAG、模型调用和接口响应       |
| Core           | 实现文档切分、检索、重排、问答、Agentic RAG、评测等核心能力  | 不绑定具体 Web 框架                  |
| Infrastructure | 封装 PostgreSQL、Qdrant、模型服务、Langfuse、文件存储等基础设施 | 不决定业务流程                       |
| Common         | 存放配置、异常、日志、统一响应、工具函数等通用能力           | 不承载具体业务模块                   |

### 4.2 依赖方向

系统依赖方向应保持单向：

```text
API → Service → Core / Repository → Infrastructure
```

约束如下：

1. API 层只能调用 Service 层。
2. Service 层可以调用 Repository 和 Core。
3. Core 层应尽量依赖抽象接口，不直接绑定具体外部服务实现。
4. Repository 层只负责数据库访问。
5. Infrastructure 层负责具体外部依赖适配。
6. Common 层可被各层引用，但不能反向依赖业务模块。

------

## 5. 核心模块划分

ForgeRAG 按业务能力划分为以下核心模块：

| 模块           | 主要职责                                         |
| -------------- | ------------------------------------------------ |
| knowledge_base | 知识库创建、查询、更新、删除和状态管理           |
| document       | 文档上传、文档元数据、文档状态和删除             |
| ingestion      | 文档解析、清洗、切分、Embedding、向量入库        |
| retrieval      | 查询向量化、Qdrant 检索、检索结果封装            |
| rerank         | 候选 chunk 重排、过滤和降级                      |
| qa             | 基础 RAG 问答、Prompt 构造、引用返回、问答记录   |
| agent          | Agentic RAG 状态图、问题改写、二次检索、拒答判断 |
| evaluation     | 评测集、评测任务、评测结果和实验对比             |
| observability  | Trace、Span、日志、耗时和异常记录                |
| system         | 健康检查、配置摘要、运行状态和工程基础能力       |

模块之间应通过 Service 或 Core 的明确接口协作，避免跨模块直接访问内部实现。

------

## 6. RAG 核心链路架构

### 6.1 文档入库链路

文档入库链路负责将原始文档转化为可检索的 chunk 和向量数据。

```text
上传文档
  → 保存文档元数据
  → 解析文本
  → 清洗文本
  → 切分 chunk
  → 保存 chunk
  → 生成 Embedding
  → 写入 Qdrant
  → 更新文档状态
  → 记录日志和 Trace
```

架构要求：

1. 文档元数据先写入 PostgreSQL。
2. chunk 文本和来源信息写入 PostgreSQL。
3. chunk 向量写入 Qdrant。
4. Qdrant payload 必须包含 `knowledge_base_id`、`document_id`、`chunk_id` 等关联标识。
5. 处理失败时更新文档状态并记录失败原因。
6. 文档处理流程应支持后续重试和重新入库扩展。

### 6.2 基础 RAG 问答链路

基础 RAG 问答链路负责根据指定知识库生成带引用回答。

```text
接收问题
  → 校验知识库
  → 问题向量化
  → Qdrant 检索
  → Rerank 重排
  → 选择上下文
  → 构造 Prompt
  → 调用 LLM
  → 生成回答
  → 返回引用
  → 保存问答记录
  → 记录 Trace
```

架构要求：

1. 检索必须限定知识库范围。
2. Rerank 作为可选增强能力，异常时允许降级。
3. Prompt 构造逻辑集中管理，不散落在业务代码中。
4. 回答必须返回引用来源。
5. 无可靠上下文时应返回无法回答提示。
6. 问答记录应保存 `trace_id`，便于关联观测数据。

### 6.3 Agentic RAG 链路

Agentic RAG 由 LangGraph 编排，重点解决固定 RAG 链路不够灵活的问题。

建议第一版状态图如下：

```text
Start
  → AnalyzeQuestion
  → NeedRetrieval?
      ├── No  → DirectAnswer → End
      └── Yes → RewriteQuery
                → Retrieve
                → Rerank
                → NeedSecondRetrieval?
                    ├── Yes → RewriteQuery → Retrieve
                    └── No  → CheckContext
                              → CanAnswer?
                                  ├── Yes → GenerateAnswer → End
                                  └── No  → RefuseAnswer → End
```

架构要求：

1. 每个节点只负责单一决策或处理动作。
2. 状态对象统一保存问题、改写查询、检索结果、重排结果、判断结果、回答和拒答原因。
3. 二次检索必须设置最大次数，避免循环失控。
4. 节点输入、输出、判断结果和耗时应写入 Trace。
5. Agentic RAG 不直接替代基础 RAG，而是作为增强入口存在。

### 6.4 自动化评测链路

评测模块用于批量运行 RAG 或 Agentic RAG，并记录效果指标。

```text
选择评测集
  → 创建评测任务
  → 逐条执行问答链路
  → 记录检索结果
  → 记录生成结果
  → 记录引用来源
  → 计算或保存评分
  → 汇总任务结果
  → 关联 Trace
```

架构要求：

1. 评测任务必须具备状态。
2. 每条样本执行结果应能关联问答记录。
3. 低分样本应能通过 `trace_id` 追踪完整链路。
4. 评测配置需要记录关键参数，例如检索参数、是否启用 Rerank、模型名称和 Prompt 版本。
5. 自动评分能力作为扩展点，不在第一版中过度设计。

------

## 7. 数据与存储架构

ForgeRAG 采用 PostgreSQL、Qdrant、文件存储和 Langfuse 分工协作的存储架构。

| 数据类型                                  | 存储位置                         | 说明                   |
| ----------------------------------------- | -------------------------------- | ---------------------- |
| 知识库、文档、chunk、问答、引用、评测任务 | PostgreSQL                       | 结构化业务数据         |
| chunk 向量                                | Qdrant                           | 用于语义检索           |
| 原始上传文件                              | 本地文件系统，后续可扩展对象存储 | 当前阶段优先简单可运行 |
| Trace、Span、模型调用过程                 | Langfuse                         | 用于链路追踪和效果分析 |
| 运行日志                                  | 控制台或日志文件                 | 用于本地调试和异常排查 |
| 运行配置                                  | `.env` / 环境变量                | 避免硬编码敏感配置     |

### 7.1 PostgreSQL 与 Qdrant 的关系

PostgreSQL 负责业务事实，Qdrant 负责语义检索。

```text
PostgreSQL Chunk
  └── chunk_id
        │
        ▼
Qdrant Point Payload
  ├── knowledge_base_id
  ├── document_id
  ├── chunk_id
  └── source metadata
```

第一版建议使用单一 Qdrant collection，并通过 payload 中的 `knowledge_base_id` 进行过滤。这样可以降低本地开发复杂度，也便于后续支持多知识库检索。后续如果出现强隔离或大规模数据需求，再考虑按租户或知识库拆分 collection。

### 7.2 核心关联标识

系统应统一使用以下标识贯穿业务数据、向量数据、日志和 Trace：

1. `knowledge_base_id`
2. `document_id`
3. `chunk_id`
4. `qa_record_id`
5. `eval_task_id`
6. `eval_result_id`
7. `request_id`
8. `trace_id`

------

## 8. 可观测性架构

ForgeRAG 的可观测性由三部分组成：

1. **结构化日志**

   用于记录请求入口、业务状态、异常信息和关键耗时。

2. **Langfuse Trace**

   用于记录 RAG、Agentic RAG、模型调用、Prompt、检索结果和评测链路。

3. **业务记录关联**

   在 PostgreSQL 中保存 `trace_id` 或 `request_id`，使问答记录、文档处理记录和评测结果能够关联到观测数据。

### 8.1 Trace 记录范围

以下流程应创建或关联 Trace：

1. 文档入库。
2. 基础 RAG 问答。
3. Agentic RAG 问答。
4. 自动化评测任务。
5. 模型调用异常。
6. 外部依赖异常。

### 8.2 降级原则

Langfuse 或观测工具不可用时，不应直接阻断核心业务流程。系统应记录本地日志，并在必要时返回可控错误。

------

## 9. 异常与统一响应架构

ForgeRAG 采用统一异常处理和统一响应结构。

### 9.1 异常分类

| 异常类型     | 示例                                            |
| ------------ | ----------------------------------------------- |
| 参数异常     | 请求字段缺失、类型错误、非法枚举值              |
| 业务异常     | 知识库不存在、文档未处理完成、检索结果不足      |
| 外部依赖异常 | PostgreSQL、Qdrant、模型服务、Langfuse 调用失败 |
| 系统异常     | 未预期代码错误                                  |

### 9.2 处理原则

1. API 层不直接暴露原始异常堆栈。
2. Service 层抛出明确业务异常。
3. Infrastructure 层将外部 SDK 异常转换为系统内部异常。
4. 全局异常处理器统一转换响应结构。
5. 日志和 Trace 中记录内部错误细节，接口响应只返回必要错误信息。

------

## 10. 部署架构

当前阶段采用 Docker Compose 支撑本地开发和演示环境。

```text
docker-compose
  ├── forgerag-api
  ├── postgres
  ├── qdrant
  ├── langfuse
  └── langfuse dependencies
```

部署要求：

1. 后端服务通过环境变量读取配置。
2. PostgreSQL、Qdrant、Langfuse 地址不硬编码。
3. `.env.example` 提供本地配置模板。
4. 后端提供健康检查接口。
5. 数据库结构通过 Alembic 迁移管理。
6. 第一版不引入 Kubernetes、服务注册、分布式事务和复杂高可用部署。

------

## 11. 推荐目录结构

```text
forgerag/
├── app/
│   ├── main.py
│   ├── api/
│   │   └── v1/
│   │       ├── health.py
│   │       ├── knowledge_base.py
│   │       ├── document.py
│   │       ├── retrieval.py
│   │       ├── qa.py
│   │       ├── agent.py
│   │       └── evaluation.py
│   ├── schemas/
│   │   ├── common.py
│   │   ├── knowledge_base.py
│   │   ├── document.py
│   │   ├── retrieval.py
│   │   ├── qa.py
│   │   ├── agent.py
│   │   └── evaluation.py
│   ├── services/
│   │   ├── knowledge_base_service.py
│   │   ├── document_service.py
│   │   ├── ingestion_service.py
│   │   ├── retrieval_service.py
│   │   ├── qa_service.py
│   │   ├── agent_service.py
│   │   └── evaluation_service.py
│   ├── repositories/
│   │   ├── knowledge_base_repository.py
│   │   ├── document_repository.py
│   │   ├── chunk_repository.py
│   │   ├── qa_repository.py
│   │   └── evaluation_repository.py
│   ├── core/
│   │   ├── document_parser/
│   │   ├── text_splitter/
│   │   ├── embedding/
│   │   ├── retrieval/
│   │   ├── rerank/
│   │   ├── prompt/
│   │   ├── rag/
│   │   ├── agent_graph/
│   │   └── evaluation/
│   ├── infrastructure/
│   │   ├── database/
│   │   ├── qdrant/
│   │   ├── llm/
│   │   ├── langfuse/
│   │   └── storage/
│   └── common/
│       ├── config.py
│       ├── exceptions.py
│       ├── response.py
│       ├── logging.py
│       └── constants.py
├── alembic/
├── tests/
├── docs/
│   ├── 01-project-overview.md
│   ├── 02-requirements-analysis.md
│   └── 03-architecture-design.md
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── .env.example
└── README.md
```

### 11.1 目录设计说明

1. `api` 只放路由入口。
2. `schemas` 只放请求和响应模型。
3. `services` 负责编排业务流程。
4. `repositories` 负责数据库访问。
5. `core` 放 RAG、Agentic RAG、评测等核心能力。
6. `infrastructure` 放外部依赖适配。
7. `common` 放通用工程能力。
8. `tests` 按模块组织测试用例。
9. `docs` 按阶段维护设计文档。

------

## 12. 架构决策记录

### ADR-001：采用分层单体架构

当前阶段不拆分微服务。原因是 ForgeRAG 的核心目标是完成可运行、可测试、可评测、可观测的 RAG 后端闭环，而不是验证复杂分布式架构。

### ADR-002：API 面向能力而不是页面

ForgeRAG 不做完整 Web 前端，因此 API 应围绕知识库、文档、检索、问答、Agentic RAG 和评测能力设计，而不是围绕具体页面设计。

### ADR-003：PostgreSQL 与 Qdrant 职责分离

PostgreSQL 保存业务元数据和结构化数据，Qdrant 保存向量数据并提供语义检索能力。两者通过业务 ID 关联。

### ADR-004：LangChain 负责基础 RAG 能力封装

LangChain 用于封装模型调用、Embedding、Retriever、Prompt 和基础 RAG 链路。

### ADR-005：LangGraph 负责 Agentic RAG 状态流转

Agentic RAG 存在条件分支、二次检索和拒答判断，更适合通过 LangGraph 表达为状态图。

### ADR-006：Langfuse 作为可观测性入口

Langfuse 用于记录 RAG 和 Agentic RAG 的 Trace、Span、模型调用和评测观测数据。但系统应允许观测组件异常时降级。

### ADR-007：第一版不设计复杂权限系统

当前阶段仅保留用户、调用方和资源归属扩展点，不实现完整 RBAC、多租户和企业单点登录，避免偏离 RAG 主线。

------

## 13. 后续设计文档边界

本架构设计文档只定义系统结构和模块边界。后续文档按以下职责继续拆分：

| 文档             | 负责内容                                        |
| ---------------- | ----------------------------------------------- |
| 数据库设计       | 表结构、字段、索引、关系、迁移策略              |
| API 设计         | URL、方法、请求字段、响应字段、错误码           |
| RAG 核心链路设计 | 文档切分、Embedding、检索、Rerank、Prompt、引用 |
| Agentic RAG 设计 | LangGraph 状态、节点、边、条件分支和拒答策略    |
| 评测设计         | 评测集、指标、任务执行、评分和结果分析          |
| 可观测性设计     | Trace、Span、日志字段、Langfuse 接入方式        |
| 部署设计         | Docker Compose、环境变量、启动流程和健康检查    |

通过以上边界划分，可以避免单份文档过长，也能保证每份文档职责清晰。