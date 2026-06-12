# ForgeRAG API 接口设计

## 1. 文档目的

本文档用于定义 ForgeRAG 第一版 REST API 设计，承接 `docs/02-requirements-analysis.md`、`docs/03-architecture-design.md` 与 `docs/04-database-design.md` 中已经明确的需求范围、架构边界和数据模型。

本文档重点说明：

1. API 的统一设计规范。
2. 请求、响应、分页和错误码约定。
3. 第一版需要提供的核心接口。
4. 各接口与知识库、文档、检索、问答、Agentic RAG、评测和观测模块的关系。
5. API 与 PostgreSQL、Qdrant、Langfuse 之间的业务关联方式。

本文档不重复展开项目背景、完整需求列表、数据库字段细节、Prompt 细节和 LangGraph 节点实现。具体字段以 Pydantic Schema 和数据库迁移脚本为准。

------

## 2. API 设计原则

ForgeRAG 第一版 API 遵循以下原则：

1. **REST 风格优先**

   使用清晰的资源路径和 HTTP Method 表达操作语义。

2. **统一版本前缀**

   第一版接口统一使用：

   ```text
   /api/v1
   ```

3. **统一响应结构**

   所有接口返回统一结构，方便前端、业务后端、脚本和 Agent 解析。

4. **结构化返回**

   问答、检索和评测接口不得只返回自然语言文本，应返回结构化结果、引用来源、状态和 `trace_id`。

5. **状态可查询**

   文档处理、Agentic RAG、评测任务等可能耗时的流程必须支持状态查询。

6. **引用可追溯**

   问答结果必须返回引用来源，引用应能关联到知识库、文档和 chunk。

7. **链路可追踪**

   核心接口应返回 `request_id` 或 `trace_id`，用于关联日志和 Langfuse Trace。

8. **不绑定完整 Web 前端**

   API 面向前端、业务后端、自动化脚本和智能 Agent，不为某个具体页面做过度定制。

------

## 3. 通用约定

### 3.1 请求格式

普通接口使用：

```http
Content-Type: application/json
```

文件上传接口使用：

```http
Content-Type: multipart/form-data
```

### 3.2 时间与 ID

| 类型    | 约定                     |
| ------- | ------------------------ |
| 主键 ID | UUID 字符串              |
| 时间    | ISO 8601 格式            |
| 时区    | 后端统一保存为带时区时间 |
| 状态值  | 使用小写字符串枚举       |

### 3.3 请求标识

客户端可以在请求头中传入：

```http
X-Request-Id: <request_id>
```

如果客户端未传入，服务端生成。

核心链路返回：

```json
{
  "request_id": "req_xxx",
  "trace_id": "trace_xxx"
}
```

`request_id` 用于关联应用日志，`trace_id` 用于关联 Langfuse Trace。

### 3.4 分页参数

列表接口统一支持：

| 参数        | 类型    | 默认值 | 说明       |
| ----------- | ------- | ------ | ---------- |
| `page`      | integer | 1      | 当前页     |
| `page_size` | integer | 20     | 每页数量   |
| `keyword`   | string  | null   | 关键词过滤 |
| `status`    | string  | null   | 状态过滤   |

分页响应统一放入 `data`：

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 0
}
```

------

## 4. 统一响应结构

### 4.1 成功响应

```json
{
  "success": true,
  "code": "OK",
  "message": "success",
  "data": {},
  "request_id": "req_xxx",
  "trace_id": null
}
```

字段说明：

| 字段         | 说明                |
| ------------ | ------------------- |
| `success`    | 是否成功            |
| `code`       | 业务状态码          |
| `message`    | 返回信息            |
| `data`       | 响应数据            |
| `request_id` | 请求 ID             |
| `trace_id`   | 链路追踪 ID，可为空 |

### 4.2 失败响应

```json
{
  "success": false,
  "code": "KB_NOT_FOUND",
  "message": "knowledge base not found",
  "data": null,
  "request_id": "req_xxx",
  "trace_id": null
}
```

接口响应不直接暴露内部异常堆栈。内部错误详情写入日志和 Trace。

------

## 5. 错误码设计

| 错误码                   | HTTP 状态码 | 说明             |
| ------------------------ | ----------- | ---------------- |
| `OK`                     | 200         | 成功             |
| `VALIDATION_ERROR`       | 422         | 参数校验失败     |
| `BAD_REQUEST`            | 400         | 请求不合法       |
| `KB_NOT_FOUND`           | 404         | 知识库不存在     |
| `KB_DISABLED`            | 409         | 知识库不可用     |
| `DOC_NOT_FOUND`          | 404         | 文档不存在       |
| `DOC_NOT_READY`          | 409         | 文档尚未处理完成 |
| `UNSUPPORTED_FILE_TYPE`  | 400         | 不支持的文件类型 |
| `FILE_TOO_LARGE`         | 400         | 文件过大         |
| `RETRIEVAL_EMPTY`        | 200         | 检索结果为空     |
| `QA_REFUSED`             | 200         | 因依据不足拒答   |
| `EVAL_TASK_NOT_FOUND`    | 404         | 评测任务不存在   |
| `EXTERNAL_SERVICE_ERROR` | 502         | 外部服务异常     |
| `DATABASE_ERROR`         | 500         | 数据库异常       |
| `VECTOR_STORE_ERROR`     | 502         | Qdrant 异常      |
| `MODEL_SERVICE_ERROR`    | 502         | 模型服务异常     |
| `INTERNAL_ERROR`         | 500         | 未预期系统异常   |

说明：

1. 业务可控的拒答不视为系统异常。
2. 检索为空可以返回成功响应，但应在业务字段中明确 `answerable=false` 或 `citations=[]`。
3. 外部依赖异常统一转换为可控错误响应。

------

## 6. 接口总览

| 模块           | 接口范围                                  |
| -------------- | ----------------------------------------- |
| System         | 健康检查、依赖就绪检查                    |
| Knowledge Base | 知识库创建、查询、更新、删除              |
| Document       | 文档上传、查询、删除、状态查询            |
| Ingestion      | 文档处理、chunk 查询、重新处理            |
| Retrieval      | 语义检索、调试检索结果                    |
| QA             | 基础 RAG 问答、问答记录查询               |
| Agent          | Agentic RAG 问答、执行记录查询            |
| Evaluation     | 评测集、评测样本、评测任务、评测结果      |
| Observability  | 返回 trace_id，不直接替代 Langfuse 控制台 |

------

## 7. System 接口

### 7.1 健康检查

```http
GET /api/v1/health
```

用于检查 FastAPI 服务是否存活。

响应示例：

```json
{
  "status": "ok",
  "service": "forgerag-api"
}
```

### 7.2 依赖就绪检查

```http
GET /api/v1/health/ready
```

用于检查关键依赖是否可用。

响应示例：

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

1. `/health` 只做轻量存活检查。
2. `/health/ready` 可检查 PostgreSQL、Qdrant 和 Langfuse。
3. Langfuse 不可用时，应明确返回依赖异常，但不代表核心服务进程不可用。

------

## 8. Knowledge Base 接口

### 8.1 创建知识库

```http
POST /api/v1/knowledge-bases
```

请求示例：

```json
{
  "name": "研发知识库",
  "description": "用于存放项目规范、接口文档和技术方案",
  "metadata": {}
}
```

响应数据：

```json
{
  "id": "uuid",
  "name": "研发知识库",
  "description": "用于存放项目规范、接口文档和技术方案",
  "status": "active",
  "document_count": 0,
  "chunk_count": 0,
  "created_at": "2026-06-10T10:00:00+08:00"
}
```

### 8.2 查询知识库列表

```http
GET /api/v1/knowledge-bases
```

支持分页和状态过滤：

```text
?page=1&page_size=20&status=active&keyword=研发
```

### 8.3 查询知识库详情

```http
GET /api/v1/knowledge-bases/{knowledge_base_id}
```

### 8.4 更新知识库

```http
PATCH /api/v1/knowledge-bases/{knowledge_base_id}
```

请求示例：

```json
{
  "name": "研发知识库 V2",
  "description": "更新后的描述",
  "status": "active",
  "metadata": {}
}
```

### 8.5 删除知识库

```http
DELETE /api/v1/knowledge-bases/{knowledge_base_id}
```

删除策略：

1. 第一版对知识库执行软删除。
2. 软删除后知识库状态变为 `deleted`。
3. 已删除知识库不能继续上传文档、检索或问答。
4. 第一版不提供物理清空知识库接口。
5. 后续如需彻底清理，可单独设计维护脚本或后台任务。

------

## 9. Document 与 Ingestion 接口

### 9.1 上传文档

```http
POST /api/v1/knowledge-bases/{knowledge_base_id}/documents
```

请求类型：

```http
multipart/form-data
```

字段：

| 字段       | 类型   | 说明             |
| ---------- | ------ | ---------------- |
| `file`     | file   | 上传文件         |
| `metadata` | string | 可选 JSON 字符串 |

响应数据：

```json
{
  "id": "uuid",
  "knowledge_base_id": "uuid",
  "file_name": "architecture.md",
  "file_ext": "md",
  "file_size": 10240,
  "status": "uploaded",
  "created_at": "2026-06-10T10:00:00+08:00"
}
```

说明：

1. 上传时必须指定知识库。
2. 系统校验文件类型和文件大小。
3. 上传成功只代表文档元数据保存成功，不代表已经完成向量化入库。

### 9.2 查询文档列表

```http
GET /api/v1/knowledge-bases/{knowledge_base_id}/documents
```

支持：

```text
?page=1&page_size=20&status=completed&keyword=架构
```

### 9.3 查询文档详情

```http
GET /api/v1/documents/{document_id}
```

返回文档元数据、处理状态、失败原因和 chunk 数量。

### 9.4 触发文档处理

```http
POST /api/v1/documents/{document_id}/process
```

用于触发解析、切分、Embedding 和写入 Qdrant。

响应数据：

```json
{
  "document_id": "uuid",
  "status": "processing",
  "message": "document processing started"
}
```

说明：

1. 第一版可以同步实现内部流程，但接口语义仍按可查询状态设计。
2. 后续接入后台任务或队列时，接口不需要大改。

### 9.5 查询文档处理状态

```http
GET /api/v1/documents/{document_id}/status
```

响应数据：

```json
{
  "document_id": "uuid",
  "status": "completed",
  "chunk_count": 128,
  "parse_error": null,
  "process_started_at": "2026-06-10T10:00:00+08:00",
  "process_finished_at": "2026-06-10T10:01:30+08:00"
}
```

### 9.6 查询文档 chunk

```http
GET /api/v1/documents/{document_id}/chunks
```

用于调试文档切分结果和引用溯源。

### 9.7 重新处理文档

```http
POST /api/v1/documents/{document_id}/reprocess
```

处理策略：

1. 物理删除旧 chunk。
2. 删除 Qdrant 中旧 point。
3. 重新解析、切分、向量化并写入 Qdrant。
4. 更新文档状态和 chunk 数量。

### 9.8 删除文档

```http
DELETE /api/v1/documents/{document_id}
```

删除策略：

1. 文档元数据软删除。
2. 文档下的 chunk 物理删除。
3. Qdrant 中对应向量 point 必须同步删除。
4. 历史问答引用不回删，依靠引用快照继续展示。

------

## 10. Retrieval 接口

### 10.1 语义检索

```http
POST /api/v1/retrieval/search
```

请求示例：

```json
{
  "knowledge_base_id": "uuid",
  "query": "系统如何记录 RAG 链路？",
  "top_k": 10,
  "score_threshold": 0.3
}
```

响应数据：

```json
{
  "query": "系统如何记录 RAG 链路？",
  "knowledge_base_id": "uuid",
  "results": [
    {
      "chunk_id": "uuid",
      "document_id": "uuid",
      "document_name": "03-architecture-design.md",
      "chunk_index": 12,
      "content": "文本片段内容",
      "score": 0.82,
      "page_number": null,
      "section_title": "可观测性架构",
      "metadata": {}
    }
  ],
  "trace_id": "trace_xxx"
}
```

约束：

1. 必须传入 `knowledge_base_id`。
2. 第一版不支持默认全库检索。
3. 无结果时返回空数组，不抛出系统异常。
4. 检索结果必须能通过 `chunk_id` 关联 PostgreSQL 和 Qdrant。

### 10.2 Rerank 调试接口

```http
POST /api/v1/retrieval/rerank
```

该接口主要用于开发调试和评测分析，不是普通调用方的必需接口。

请求示例：

```json
{
  "query": "系统如何记录 RAG 链路？",
  "candidates": [
    {
      "chunk_id": "uuid",
      "content": "候选文本"
    }
  ],
  "top_n": 5
}
```

响应数据：

```json
{
  "results": [
    {
      "chunk_id": "uuid",
      "content": "候选文本",
      "rerank_score": 0.91
    }
  ]
}
```

说明：

1. Rerank 在正式问答流程中由 QA Service 内部调用。
2. Rerank 服务不可用时，问答流程可以降级使用原始检索排序。

------

## 11. QA 接口

### 11.1 基础 RAG 问答

```http
POST /api/v1/qa
```

请求示例：

```json
{
  "knowledge_base_id": "uuid",
  "question": "ForgeRAG 的可观测性如何设计？",
  "retrieval_config": {
    "top_k": 10,
    "score_threshold": 0.3
  },
  "rerank_config": {
    "enabled": true,
    "top_n": 5
  },
  "model_config": {
    "model_name": "default"
  },
  "client_id": "frontend"
}
```

响应数据：

```json
{
  "qa_record_id": "uuid",
  "knowledge_base_id": "uuid",
  "question": "ForgeRAG 的可观测性如何设计？",
  "answer": "ForgeRAG 通过结构化日志、Langfuse Trace 和业务记录关联来实现可观测性。",
  "status": "success",
  "answerable": true,
  "citations": [
    {
      "citation_order": 1,
      "document_id": "uuid",
      "chunk_id": "uuid",
      "document_name": "03-architecture-design.md",
      "quote_text": "引用片段快照",
      "page_number": null,
      "chunk_index": 12,
      "retrieval_score": 0.82,
      "rerank_score": 0.91
    }
  ],
  "latency_ms": 2500,
  "request_id": "req_xxx",
  "trace_id": "trace_xxx"
}
```

拒答响应中的 `success` 仍可为 `true`，业务状态由 `status` 表达：

```json
{
  "qa_record_id": "uuid",
  "status": "refused",
  "answerable": false,
  "answer": null,
  "refuse_reason": "知识库中没有足够依据回答该问题",
  "citations": [],
  "trace_id": "trace_xxx"
}
```

约束：

1. 问答必须限定知识库。
2. 回答必须返回引用来源。
3. 无可靠上下文时应拒答，不强行生成确定性答案。
4. 问答记录写入 `qa_records`。
5. 引用快照写入 `qa_citations`。
6. 详细检索、Prompt、模型调用过程写入 Langfuse Trace。

### 11.2 查询问答记录列表

```http
GET /api/v1/qa-records
```

支持过滤：

```text
?knowledge_base_id=uuid&qa_mode=basic_rag&status=success&page=1&page_size=20
```

### 11.3 查询问答记录详情

```http
GET /api/v1/qa-records/{qa_record_id}
```

返回问答最终结果、引用来源、状态、耗时和 `trace_id`。

说明：

1. 问答记录第一版不提供普通软删除。
2. 后续可按时间范围做物理清理或归档。

------

## 12. Agentic RAG 接口

### 12.1 发起 Agentic RAG 问答

```http
POST /api/v1/agent/qa
```

请求示例：

```json
{
  "knowledge_base_id": "uuid",
  "question": "这套系统接口怎么设计更合理？",
  "max_iterations": 2,
  "retrieval_config": {
    "top_k": 10,
    "score_threshold": 0.3
  },
  "rerank_config": {
    "enabled": true,
    "top_n": 5
  },
  "model_config": {
    "model_name": "default"
  },
  "client_id": "agent"
}
```

响应数据：

```json
{
  "agent_run_id": "uuid",
  "qa_record_id": "uuid",
  "knowledge_base_id": "uuid",
  "original_question": "这套系统接口怎么设计更合理？",
  "final_question": "ForgeRAG API 接口设计原则和模块划分是什么？",
  "answer": "最终回答内容",
  "status": "success",
  "refuse_reason": null,
  "citations": [],
  "steps": [
    {
      "step_name": "AnalyzeQuestion",
      "status": "success",
      "decision": "need_retrieval"
    },
    {
      "step_name": "RewriteQuery",
      "status": "success",
      "decision": "rewritten"
    },
    {
      "step_name": "Retrieve",
      "status": "success",
      "decision": "enough_candidates"
    }
  ],
  "latency_ms": 4200,
  "request_id": "req_xxx",
  "trace_id": "trace_xxx"
}
```

约束：

1. Agentic RAG 通过 LangGraph 编排。
2. 每次执行生成 `agent_run_id`。
3. 关键节点摘要写入 `agent_steps`。
4. 详细节点输入输出、Prompt 和模型调用写入 Langfuse。
5. 必须限制最大循环次数，避免无限二次检索。
6. 上下文不足时返回拒答结果。

### 12.2 查询 Agent 执行记录

```http
GET /api/v1/agent/runs/{agent_run_id}
```

返回 Agentic RAG 执行摘要、最终状态、关联问答记录和 `trace_id`。

### 12.3 查询 Agent 节点记录

```http
GET /api/v1/agent/runs/{agent_run_id}/steps
```

返回节点名称、执行顺序、决策结果、状态、耗时和错误信息摘要。

------

## 13. Evaluation 接口

### 13.1 创建评测数据集

```http
POST /api/v1/evaluation/datasets
```

请求示例：

```json
{
  "knowledge_base_id": "uuid",
  "name": "RAG 基础评测集",
  "description": "用于验证检索、问答和引用质量",
  "metadata": {}
}
```

### 13.2 查询评测数据集列表

```http
GET /api/v1/evaluation/datasets
```

### 13.3 创建评测样本

```http
POST /api/v1/evaluation/datasets/{dataset_id}/samples
```

请求示例：

```json
{
  "question": "ForgeRAG 使用什么组件存储向量？",
  "reference_answer": "ForgeRAG 使用 Qdrant 存储 chunk 向量。",
  "expected_document_ids": [],
  "expected_chunk_ids": [],
  "tags": ["retrieval", "vector-store"],
  "difficulty": "easy"
}
```

### 13.4 查询评测样本列表

```http
GET /api/v1/evaluation/datasets/{dataset_id}/samples
```

### 13.5 创建评测任务

```http
POST /api/v1/evaluation/tasks
```

请求示例：

```json
{
  "dataset_id": "uuid",
  "knowledge_base_id": "uuid",
  "name": "基础 RAG 参数评测",
  "qa_mode": "basic_rag",
  "retrieval_config": {
    "top_k": 10,
    "score_threshold": 0.3
  },
  "rerank_config": {
    "enabled": true,
    "top_n": 5
  },
  "model_config": {
    "model_name": "default"
  },
  "prompt_version": "rag_qa_v1"
}
```

响应数据：

```json
{
  "eval_task_id": "uuid",
  "status": "pending",
  "total_count": 0
}
```

说明：

1. 评测任务保存关键配置快照。
2. 第一版可以先支持手动触发执行。
3. 后续可以接入后台任务或定时任务。

### 13.6 启动评测任务

```http
POST /api/v1/evaluation/tasks/{task_id}/run
```

响应数据：

```json
{
  "eval_task_id": "uuid",
  "status": "running",
  "trace_id": "trace_xxx"
}
```

### 13.7 查询评测任务详情

```http
GET /api/v1/evaluation/tasks/{task_id}
```

返回任务状态、样本总数、成功数、失败数、平均分、错误信息和配置快照。

### 13.8 查询评测结果

```http
GET /api/v1/evaluation/tasks/{task_id}/results
```

返回样本级评测结果，包括问题快照、生成答案、检索结果摘要、引用摘要、得分和 `trace_id`。

### 13.9 删除评测资源

```http
DELETE /api/v1/evaluation/datasets/{dataset_id}
DELETE /api/v1/evaluation/tasks/{task_id}
```

删除策略：

1. 评测数据集软删除。
2. 评测任务软删除。
3. 评测样本和评测结果作为明细数据，后续清理时可物理删除。
4. 删除评测任务时，可以级联物理删除对应 `evaluation_results`。

------

## 14. 可观测性约定

ForgeRAG 不在第一版中重新实现 Langfuse 控制台。API 只负责返回可关联的观测标识。

核心接口应返回：

| 字段           | 说明                |
| -------------- | ------------------- |
| `request_id`   | 应用请求标识        |
| `trace_id`     | Langfuse Trace 标识 |
| `qa_record_id` | 问答记录 ID         |
| `agent_run_id` | Agentic RAG 执行 ID |
| `eval_task_id` | 评测任务 ID         |

调用方可以通过这些标识关联：

1. PostgreSQL 中的业务记录。
2. 应用结构化日志。
3. Langfuse 中的 Trace 和 Span。
4. 评测结果中的失败样本。

如果 Langfuse 不可用：

1. 核心问答流程应尽量继续执行。
2. 系统记录本地结构化日志。
3. 响应中 `trace_id` 可以为空。
4. 不应因观测工具异常直接阻断普通问答。

------

## 15. 接口与数据表映射

| API 模块       | 主要数据表                                                   | 外部组件                         |
| -------------- | ------------------------------------------------------------ | -------------------------------- |
| Knowledge Base | `knowledge_bases`                                            | -                                |
| Document       | `documents`, `document_chunks`                               | 文件存储                         |
| Ingestion      | `documents`, `document_chunks`                               | Qdrant、Embedding 模型           |
| Retrieval      | `document_chunks`                                            | Qdrant、Embedding 模型           |
| QA             | `qa_records`, `qa_citations`                                 | LLM、Qdrant、Rerank、Langfuse    |
| Agent          | `agent_runs`, `agent_steps`, `qa_records`                    | LangGraph、LLM、Qdrant、Langfuse |
| Evaluation     | `evaluation_datasets`, `evaluation_samples`, `evaluation_tasks`, `evaluation_results` | QA Service、Langfuse             |
| Observability  | 业务表中的 `trace_id` / `request_id`                         | Langfuse、结构化日志             |

------

## 16. 第一版不提供的接口

为避免第一版范围膨胀，以下接口暂不设计：

| 接口能力            | 暂不设计原因                             |
| ------------------- | ---------------------------------------- |
| 用户注册登录接口    | 第一版不实现完整权限系统                 |
| 角色权限接口        | 第一版不做复杂 RBAC                      |
| 多租户组织接口      | 第一版不做 SaaS 平台                     |
| Prompt 版本管理接口 | Prompt 第一版使用配置或文件管理          |
| 模型配置管理接口    | 模型配置第一版通过环境变量和配置文件管理 |
| 复杂审计日志接口    | 第一版依靠结构化日志和 Langfuse          |
| 数据归档接口        | 第一版先保留清理扩展点                   |
| 全库检索接口        | 第一版避免跨知识库误召回                 |

------

## 17. API 设计总结

ForgeRAG 第一版 API 围绕以下主线设计：

```text
健康检查
  → 知识库管理
  → 文档上传与处理
  → 语义检索
  → 基础 RAG 问答
  → Agentic RAG 问答
  → 自动化评测
  → Trace 关联与观测
```

设计重点如下：

1. 使用 `/api/v1` 作为统一版本前缀。
2. 使用统一响应结构和错误码。
3. 列表接口统一分页。
4. 文档处理、Agentic RAG 和评测任务支持状态查询。
5. 问答结果必须返回引用来源。
6. 核心接口返回 `request_id` 和 `trace_id`。
7. 知识库删除、文档删除和评测删除策略与数据库设计保持一致。
8. API 层只负责请求入口、参数校验和响应，不直接访问数据库、Qdrant、模型服务或 Langfuse。
9. 第一版接口优先保证 RAG 后端闭环可运行、可测试、可观测，不提前扩展复杂权限、多租户和商业化接口。