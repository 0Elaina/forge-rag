# ForgeRAG 数据库设计

## 1. 文档目的

本文档用于定义 ForgeRAG 第一版的 PostgreSQL 数据库设计，承接 `docs/02-requirements-analysis.md` 与 `docs/03-architecture-design.md` 中已经明确的数据需求和存储架构。

本文档重点说明：

1. 核心业务表如何设计。
2. 表之间如何建立关联。
3. PostgreSQL 与 Qdrant 如何通过业务 ID 对齐。
4. 问答、引用、Agentic RAG、评测和 Trace 如何关联。
5. 第一版哪些数据入库，哪些数据交给 Qdrant、Langfuse 或日志系统管理。
6. 不同数据表采用软删除还是物理删除。

本文档不重复说明项目背景、完整需求、系统架构和 API 细节。具体接口字段以后续 API 设计文档为准。

------

## 2. 数据库设计原则

1. **PostgreSQL 只保存结构化业务数据**

   知识库、文档、chunk、问答记录、引用来源、Agentic RAG 流程摘要、评测数据集、评测任务和评测结果由 PostgreSQL 管理。

2. **Qdrant 只保存向量和检索 payload**

   chunk 向量不存入 PostgreSQL。PostgreSQL 只保存 chunk 文本、来源信息和向量关联标识。

3. **Trace 细节交给 Langfuse**

   PostgreSQL 只保存 `trace_id`、`request_id` 和必要状态摘要。完整 Trace、Span、Prompt、模型输入输出和 Token 细节由 Langfuse 记录。

4. **核心资源软删除，高增长明细物理删除**

   知识库、文档、评测数据集、评测任务等核心资源可以软删除；chunk、引用、Agent 节点、评测结果等高增长明细数据默认物理删除。

5. **优先保证第一版闭环可运行**

   第一版不设计复杂用户、权限、多租户、审计和计费表。只保留 `created_by`、`owner_id`、`client_id` 等可空扩展字段。

6. **状态字段明确**

   文档处理、问答、Agentic RAG 和评测任务都必须有明确状态，避免长流程不可追踪。

7. **重要配置快照入库**

   评测任务和问答记录应保存关键配置快照，例如模型名称、检索参数、是否启用 Rerank、Prompt 版本等，便于复现结果。

------

## 3. 数据存储边界

| 数据类型         | 存储位置                         | 说明                             |
| ---------------- | -------------------------------- | -------------------------------- |
| 知识库数据       | PostgreSQL                       | 业务边界                         |
| 文档元数据       | PostgreSQL                       | 文件信息、处理状态、失败原因     |
| 原始文件         | 本地文件系统，后续可扩展对象存储 | PostgreSQL 只保存文件路径        |
| chunk 文本与来源 | PostgreSQL                       | 用于引用、展示、评测             |
| chunk 向量       | Qdrant                           | 用于语义检索                     |
| Qdrant payload   | Qdrant                           | 保存知识库、文档、chunk 关联标识 |
| 问答记录         | PostgreSQL                       | 保存问题、答案、状态、trace_id   |
| 引用来源         | PostgreSQL                       | 保存回答使用的 chunk 快照        |
| Agentic RAG 摘要 | PostgreSQL                       | 保存 run 和 step 摘要            |
| Trace / Span     | Langfuse                         | 保存完整链路观测数据             |
| 评测数据与结果   | PostgreSQL                       | 保存评测集、任务、样本结果       |
| 运行配置         | `.env` / 环境变量                | 不做配置中心                     |

------

## 4. 核心实体关系

```text
knowledge_bases
  ├── documents
  │     └── document_chunks
  │             └── Qdrant Point
  ├── qa_records
  │     └── qa_citations
  ├── agent_runs
  │     └── agent_steps
  ├── evaluation_datasets
  │     └── evaluation_samples
  └── evaluation_tasks
        └── evaluation_results
              ├── qa_records
              └── trace_id
```

核心关联标识：

| 标识                | 用途                       |
| ------------------- | -------------------------- |
| `knowledge_base_id` | 约束知识库范围             |
| `document_id`       | 关联原始文档               |
| `chunk_id`          | 关联 chunk 与 Qdrant point |
| `qa_record_id`      | 关联问答记录与引用         |
| `agent_run_id`      | 关联 Agentic RAG 一次执行  |
| `eval_dataset_id`   | 关联评测数据集             |
| `eval_sample_id`    | 关联评测样本               |
| `eval_task_id`      | 关联评测任务               |
| `eval_result_id`    | 关联单条评测结果           |
| `trace_id`          | 关联 Langfuse Trace        |
| `request_id`        | 关联应用日志               |

------

## 5. 通用字段约定

除特殊说明外，核心业务主表建议包含以下通用字段：

| 字段         | 类型          | 说明           |
| ------------ | ------------- | -------------- |
| `id`         | `UUID`        | 主键           |
| `created_at` | `TIMESTAMPTZ` | 创建时间       |
| `updated_at` | `TIMESTAMPTZ` | 更新时间       |
| `created_by` | `UUID NULL`   | 创建者扩展字段 |
| `updated_by` | `UUID NULL`   | 更新者扩展字段 |

软删除字段不作为所有表的默认字段，只在需要保留删除状态的核心资源表中使用：

| 字段         | 类型               | 说明                             |
| ------------ | ------------------ | -------------------------------- |
| `deleted_at` | `TIMESTAMPTZ NULL` | 软删除时间，仅用于需要软删除的表 |

设计约定：

1. 主键统一使用 `UUID`。
2. 时间字段统一使用 `TIMESTAMPTZ`。
3. 软删除只用于核心业务资源表。
4. 高增长明细表优先使用物理删除。
5. 状态字段使用字符串枚举，便于 SQLAlchemy 映射。
6. 复杂配置快照使用 `JSONB`。
7. 对列表查询常用字段建立索引。

------

## 6. 状态枚举设计

### 6.1 知识库状态

| 值         | 说明                             |
| ---------- | -------------------------------- |
| `active`   | 正常可用                         |
| `disabled` | 已禁用，不允许普通问答和文档入库 |
| `deleted`  | 已删除                           |

### 6.2 文档处理状态

| 值           | 说明                   |
| ------------ | ---------------------- |
| `uploaded`   | 已上传，尚未处理       |
| `processing` | 正在解析、切分或向量化 |
| `completed`  | 处理完成               |
| `failed`     | 处理失败               |
| `deleted`    | 已删除                 |

### 6.3 Chunk 向量化状态

| 值          | 说明       |
| ----------- | ---------- |
| `pending`   | 待向量化   |
| `completed` | 向量化完成 |
| `failed`    | 向量化失败 |

### 6.4 问答状态

| 值        | 说明                 |
| --------- | -------------------- |
| `success` | 成功生成回答         |
| `refused` | 因依据不足等原因拒答 |
| `failed`  | 执行失败             |

### 6.5 Agentic RAG 状态

| 值        | 说明     |
| --------- | -------- |
| `running` | 执行中   |
| `success` | 成功完成 |
| `refused` | 最终拒答 |
| `failed`  | 执行失败 |

### 6.6 Agentic RAG 节点状态

| 值        | 说明         |
| --------- | ------------ |
| `success` | 节点执行成功 |
| `skipped` | 节点被跳过   |
| `failed`  | 节点执行失败 |

### 6.7 评测任务状态

| 值          | 说明     |
| ----------- | -------- |
| `pending`   | 待执行   |
| `running`   | 执行中   |
| `completed` | 执行完成 |
| `failed`    | 执行失败 |
| `cancelled` | 已取消   |

### 6.8 评测结果状态

| 值        | 说明         |
| --------- | ------------ |
| `success` | 样本执行成功 |
| `failed`  | 样本执行失败 |

------

## 7. 表结构设计

## 7.1 knowledge_bases

知识库表，用于表示一个独立知识边界。

| 字段             | 类型           | 约束      | 说明                              |
| ---------------- | -------------- | --------- | --------------------------------- |
| `id`             | `UUID`         | PK        | 知识库 ID                         |
| `name`           | `VARCHAR(100)` | NOT NULL  | 知识库名称                        |
| `description`    | `TEXT`         | NULL      | 知识库描述                        |
| `status`         | `VARCHAR(32)`  | NOT NULL  | `active` / `disabled` / `deleted` |
| `owner_id`       | `UUID`         | NULL      | 后续权限扩展字段                  |
| `document_count` | `INTEGER`      | DEFAULT 0 | 文档数量冗余字段                  |
| `chunk_count`    | `INTEGER`      | DEFAULT 0 | chunk 数量冗余字段                |
| `metadata`       | `JSONB`        | NULL      | 扩展信息                          |
| `created_by`     | `UUID`         | NULL      | 创建者扩展字段                    |
| `updated_by`     | `UUID`         | NULL      | 更新者扩展字段                    |
| `created_at`     | `TIMESTAMPTZ`  | NOT NULL  | 创建时间                          |
| `updated_at`     | `TIMESTAMPTZ`  | NOT NULL  | 更新时间                          |
| `deleted_at`     | `TIMESTAMPTZ`  | NULL      | 删除时间                          |

建议索引：

| 索引                | 字段                     |
| ------------------- | ------------------------ |
| `idx_kb_status`     | `status`                 |
| `idx_kb_created_at` | `created_at`             |
| `uk_kb_name_active` | `name`，仅未删除数据唯一 |

说明：

1. `document_count` 和 `chunk_count` 可用于列表页快速展示。
2. 删除知识库时第一版建议软删除，不立即物理删除关联问答和评测数据。
3. 后续接入权限系统后，`owner_id` 可关联用户或组织。

------

## 7.2 documents

文档表，用于保存上传文档的元数据和处理状态。

| 字段                  | 类型           | 约束      | 说明                         |
| --------------------- | -------------- | --------- | ---------------------------- |
| `id`                  | `UUID`         | PK        | 文档 ID                      |
| `knowledge_base_id`   | `UUID`         | FK        | 所属知识库                   |
| `file_name`           | `VARCHAR(255)` | NOT NULL  | 原始文件名                   |
| `file_ext`            | `VARCHAR(32)`  | NOT NULL  | 文件扩展名                   |
| `mime_type`           | `VARCHAR(100)` | NULL      | MIME 类型                    |
| `file_size`           | `BIGINT`       | NOT NULL  | 文件大小，单位 byte          |
| `file_path`           | `TEXT`         | NOT NULL  | 本地文件路径或对象存储 key   |
| `file_hash`           | `VARCHAR(128)` | NULL      | 文件哈希，用于去重或版本判断 |
| `status`              | `VARCHAR(32)`  | NOT NULL  | 文档处理状态                 |
| `parse_error`         | `TEXT`         | NULL      | 失败原因                     |
| `chunk_count`         | `INTEGER`      | DEFAULT 0 | 当前文档生成的 chunk 数量    |
| `embedding_model`     | `VARCHAR(100)` | NULL      | 入库时使用的 Embedding 模型  |
| `process_started_at`  | `TIMESTAMPTZ`  | NULL      | 处理开始时间                 |
| `process_finished_at` | `TIMESTAMPTZ`  | NULL      | 处理完成时间                 |
| `metadata`            | `JSONB`        | NULL      | 文档扩展元数据               |
| `created_by`          | `UUID`         | NULL      | 创建者扩展字段               |
| `updated_by`          | `UUID`         | NULL      | 更新者扩展字段               |
| `created_at`          | `TIMESTAMPTZ`  | NOT NULL  | 创建时间                     |
| `updated_at`          | `TIMESTAMPTZ`  | NOT NULL  | 更新时间                     |
| `deleted_at`          | `TIMESTAMPTZ`  | NULL      | 删除时间                     |

建议索引：

| 索引                 | 字段                |
| -------------------- | ------------------- |
| `idx_doc_kb_id`      | `knowledge_base_id` |
| `idx_doc_status`     | `status`            |
| `idx_doc_file_hash`  | `file_hash`         |
| `idx_doc_created_at` | `created_at`        |

说明：

1. `file_path` 不直接信任用户上传文件名，应由系统生成。
2. `parse_error` 用于保存解析、切分、Embedding 或写入 Qdrant 的失败原因。
3. 文档元数据采用软删除。
4. 文档删除时，该文档下的 chunk 和 Qdrant point 应物理删除。
5. 第一版不单独设计文档版本表，后续需要版本管理时再扩展。

------

## 7.3 document_chunks

chunk 表，用于保存文档切分后的文本块和来源信息。

| 字段                | 类型           | 约束     | 说明                               |
| ------------------- | -------------- | -------- | ---------------------------------- |
| `id`                | `UUID`         | PK       | chunk ID                           |
| `knowledge_base_id` | `UUID`         | FK       | 所属知识库                         |
| `document_id`       | `UUID`         | FK       | 所属文档                           |
| `chunk_index`       | `INTEGER`      | NOT NULL | 文档内 chunk 序号                  |
| `content`           | `TEXT`         | NOT NULL | chunk 文本内容                     |
| `content_hash`      | `VARCHAR(128)` | NULL     | chunk 内容哈希                     |
| `token_count`       | `INTEGER`      | NULL     | token 数量                         |
| `char_count`        | `INTEGER`      | NULL     | 字符数量                           |
| `page_number`       | `INTEGER`      | NULL     | 页码                               |
| `section_title`     | `VARCHAR(255)` | NULL     | 标题或章节                         |
| `start_offset`      | `INTEGER`      | NULL     | 原文起始位置                       |
| `end_offset`        | `INTEGER`      | NULL     | 原文结束位置                       |
| `splitter_name`     | `VARCHAR(100)` | NULL     | 切分器名称                         |
| `splitter_config`   | `JSONB`        | NULL     | 切分参数快照                       |
| `embedding_status`  | `VARCHAR(32)`  | NOT NULL | `pending` / `completed` / `failed` |
| `embedding_model`   | `VARCHAR(100)` | NULL     | Embedding 模型                     |
| `embedding_dim`     | `INTEGER`      | NULL     | 向量维度                           |
| `qdrant_collection` | `VARCHAR(100)` | NULL     | Qdrant collection                  |
| `qdrant_point_id`   | `VARCHAR(100)` | NULL     | Qdrant point ID                    |
| `metadata`          | `JSONB`        | NULL     | 扩展元数据                         |
| `created_at`        | `TIMESTAMPTZ`  | NOT NULL | 创建时间                           |
| `updated_at`        | `TIMESTAMPTZ`  | NOT NULL | 更新时间                           |

建议索引：

| 索引                         | 字段                       |
| ---------------------------- | -------------------------- |
| `idx_chunk_kb_id`            | `knowledge_base_id`        |
| `idx_chunk_doc_id`           | `document_id`              |
| `idx_chunk_qdrant_point_id`  | `qdrant_point_id`          |
| `idx_chunk_embedding_status` | `embedding_status`         |
| `uk_chunk_doc_index`         | `document_id, chunk_index` |

说明：

1. `content` 保存在 PostgreSQL 中，用于引用展示、评测和回溯。
2. 向量本体不存 PostgreSQL。
3. `qdrant_point_id` 建议直接使用 `chunk_id` 字符串，降低双端关联复杂度。
4. `splitter_config` 用于复现切分策略。
5. `document_chunks` 是高增长明细表，不使用软删除。
6. 文档删除或重新入库时，chunk 应物理删除。

------

## 7.4 qa_records

问答记录表，用于保存基础 RAG 或 Agentic RAG 的最终结果。

| 字段                 | 类型           | 约束     | 说明                             |
| -------------------- | -------------- | -------- | -------------------------------- |
| `id`                 | `UUID`         | PK       | 问答记录 ID                      |
| `knowledge_base_id`  | `UUID`         | FK       | 目标知识库                       |
| `question`           | `TEXT`         | NOT NULL | 用户原始问题                     |
| `rewritten_question` | `TEXT`         | NULL     | 改写后的问题                     |
| `answer`             | `TEXT`         | NULL     | 最终回答                         |
| `qa_mode`            | `VARCHAR(32)`  | NOT NULL | `basic_rag` / `agentic_rag`      |
| `status`             | `VARCHAR(32)`  | NOT NULL | `success` / `refused` / `failed` |
| `refuse_reason`      | `TEXT`         | NULL     | 拒答原因                         |
| `error_message`      | `TEXT`         | NULL     | 失败原因                         |
| `retrieval_config`   | `JSONB`        | NULL     | 检索参数快照                     |
| `rerank_config`      | `JSONB`        | NULL     | Rerank 参数快照                  |
| `model_config`       | `JSONB`        | NULL     | LLM 参数快照                     |
| `prompt_version`     | `VARCHAR(100)` | NULL     | Prompt 版本                      |
| `latency_ms`         | `INTEGER`      | NULL     | 总耗时                           |
| `input_tokens`       | `INTEGER`      | NULL     | 输入 token                       |
| `output_tokens`      | `INTEGER`      | NULL     | 输出 token                       |
| `request_id`         | `VARCHAR(100)` | NULL     | 应用请求 ID                      |
| `trace_id`           | `VARCHAR(100)` | NULL     | Langfuse Trace ID                |
| `client_id`          | `VARCHAR(100)` | NULL     | 调用方扩展标识                   |
| `metadata`           | `JSONB`        | NULL     | 扩展信息                         |
| `created_at`         | `TIMESTAMPTZ`  | NOT NULL | 创建时间                         |
| `updated_at`         | `TIMESTAMPTZ`  | NOT NULL | 更新时间                         |

建议索引：

| 索引                | 字段                |
| ------------------- | ------------------- |
| `idx_qa_kb_id`      | `knowledge_base_id` |
| `idx_qa_status`     | `status`            |
| `idx_qa_mode`       | `qa_mode`           |
| `idx_qa_trace_id`   | `trace_id`          |
| `idx_qa_created_at` | `created_at`        |

说明：

1. 该表只保存最终问答结果和关键配置快照。
2. 详细检索、Rerank、Prompt、模型调用过程由 Langfuse 记录。
3. `rewritten_question` 用于保存 Agentic RAG 或查询改写结果。
4. 引用来源不直接塞进该表，单独放入 `qa_citations`。
5. 第一版默认不提供普通删除能力。
6. 历史清理时，可按时间范围物理删除，并级联删除 `qa_citations`。

------

## 7.5 qa_citations

引用来源表，用于保存一次问答使用到的 chunk 快照。

| 字段                | 类型               | 约束     | 说明         |
| ------------------- | ------------------ | -------- | ------------ |
| `id`                | `UUID`             | PK       | 引用 ID      |
| `qa_record_id`      | `UUID`             | FK       | 问答记录 ID  |
| `knowledge_base_id` | `UUID`             | FK       | 知识库 ID    |
| `document_id`       | `UUID`             | FK NULL  | 文档 ID      |
| `chunk_id`          | `UUID`             | FK NULL  | chunk ID     |
| `quote_text`        | `TEXT`             | NOT NULL | 引用片段快照 |
| `document_name`     | `VARCHAR(255)`     | NULL     | 展示用文档名 |
| `page_number`       | `INTEGER`          | NULL     | 页码         |
| `chunk_index`       | `INTEGER`          | NULL     | chunk 序号   |
| `retrieval_score`   | `DOUBLE PRECISION` | NULL     | 向量检索得分 |
| `rerank_score`      | `DOUBLE PRECISION` | NULL     | 重排得分     |
| `citation_order`    | `INTEGER`          | NOT NULL | 引用展示顺序 |
| `metadata`          | `JSONB`            | NULL     | 扩展信息     |
| `created_at`        | `TIMESTAMPTZ`      | NOT NULL | 创建时间     |

建议索引：

| 索引                    | 字段                           |
| ----------------------- | ------------------------------ |
| `idx_citation_qa_id`    | `qa_record_id`                 |
| `idx_citation_chunk_id` | `chunk_id`                     |
| `idx_citation_doc_id`   | `document_id`                  |
| `idx_citation_order`    | `qa_record_id, citation_order` |

说明：

1. 该表用于保证答案可追溯。
2. `quote_text` 保存当时使用的引用片段快照，避免后续 chunk 物理删除后历史问答失去依据。
3. 引用顺序由 `citation_order` 控制。
4. `qa_citations` 是问答明细表，不使用软删除。
5. 删除 `qa_records` 时，级联物理删除对应引用。
6. 删除文档或 chunk 时，不回删历史引用快照。

------

## 7.6 agent_runs

Agentic RAG 执行记录表，用于保存一次 Agentic RAG 流程的整体摘要。

| 字段                | 类型           | 约束      | 说明                                         |
| ------------------- | -------------- | --------- | -------------------------------------------- |
| `id`                | `UUID`         | PK        | Agent run ID                                 |
| `qa_record_id`      | `UUID`         | FK NULL   | 关联问答记录                                 |
| `knowledge_base_id` | `UUID`         | FK        | 知识库 ID                                    |
| `original_question` | `TEXT`         | NOT NULL  | 原始问题                                     |
| `final_question`    | `TEXT`         | NULL      | 最终检索问题                                 |
| `final_answer`      | `TEXT`         | NULL      | 最终回答                                     |
| `status`            | `VARCHAR(32)`  | NOT NULL  | `running` / `success` / `refused` / `failed` |
| `refuse_reason`     | `TEXT`         | NULL      | 拒答原因                                     |
| `error_message`     | `TEXT`         | NULL      | 错误信息                                     |
| `max_iterations`    | `INTEGER`      | NOT NULL  | 最大循环次数                                 |
| `actual_iterations` | `INTEGER`      | DEFAULT 0 | 实际循环次数                                 |
| `graph_version`     | `VARCHAR(100)` | NULL      | LangGraph 流程版本                           |
| `state_snapshot`    | `JSONB`        | NULL      | 最终状态摘要                                 |
| `request_id`        | `VARCHAR(100)` | NULL      | 请求 ID                                      |
| `trace_id`          | `VARCHAR(100)` | NULL      | Trace ID                                     |
| `latency_ms`        | `INTEGER`      | NULL      | 总耗时                                       |
| `created_at`        | `TIMESTAMPTZ`  | NOT NULL  | 创建时间                                     |
| `updated_at`        | `TIMESTAMPTZ`  | NOT NULL  | 更新时间                                     |

建议索引：

| 索引                     | 字段                |
| ------------------------ | ------------------- |
| `idx_agent_run_qa_id`    | `qa_record_id`      |
| `idx_agent_run_kb_id`    | `knowledge_base_id` |
| `idx_agent_run_status`   | `status`            |
| `idx_agent_run_trace_id` | `trace_id`          |

说明：

1. `agent_runs` 只保存流程摘要。
2. 节点级摘要放入 `agent_steps`。
3. 更细的 Span 仍由 Langfuse 记录。
4. `agent_runs` 可保留近期数据用于调试，后续支持按时间范围物理清理。
5. 清理 `agent_runs` 时，应级联物理删除对应 `agent_steps`。

------

## 7.7 agent_steps

Agentic RAG 节点记录表，用于保存关键节点的输入输出摘要和决策结果。

| 字段             | 类型           | 约束     | 说明                             |
| ---------------- | -------------- | -------- | -------------------------------- |
| `id`             | `UUID`         | PK       | 节点记录 ID                      |
| `agent_run_id`   | `UUID`         | FK       | Agent run ID                     |
| `step_name`      | `VARCHAR(100)` | NOT NULL | 节点名称                         |
| `step_order`     | `INTEGER`      | NOT NULL | 执行顺序                         |
| `input_summary`  | `JSONB`        | NULL     | 输入摘要                         |
| `output_summary` | `JSONB`        | NULL     | 输出摘要                         |
| `decision`       | `VARCHAR(100)` | NULL     | 决策结果                         |
| `next_step`      | `VARCHAR(100)` | NULL     | 下一节点                         |
| `status`         | `VARCHAR(32)`  | NOT NULL | `success` / `skipped` / `failed` |
| `error_message`  | `TEXT`         | NULL     | 节点错误                         |
| `latency_ms`     | `INTEGER`      | NULL     | 节点耗时                         |
| `trace_id`       | `VARCHAR(100)` | NULL     | Trace ID                         |
| `span_id`        | `VARCHAR(100)` | NULL     | Langfuse Span ID                 |
| `created_at`     | `TIMESTAMPTZ`  | NOT NULL | 创建时间                         |

建议索引：

| 索引                        | 字段                       |
| --------------------------- | -------------------------- |
| `idx_agent_step_run_id`     | `agent_run_id`             |
| `idx_agent_step_order`      | `agent_run_id, step_order` |
| `idx_agent_step_name`       | `step_name`                |
| `idx_agent_step_trace_span` | `trace_id, span_id`        |

说明：

1. 节点输入输出只保存摘要，避免 PostgreSQL 承担完整 Trace 存储。
2. Prompt、完整上下文和模型输出以 Langfuse 为主。
3. `decision` 用于记录是否检索、是否二次检索、是否拒答等判断。
4. `agent_steps` 是高增长明细表，不使用软删除。
5. 清理 Agent 记录时，该表应物理删除。

------

## 7.8 evaluation_datasets

评测数据集表，用于组织一组评测样本。

| 字段                | 类型           | 约束      | 说明                              |
| ------------------- | -------------- | --------- | --------------------------------- |
| `id`                | `UUID`         | PK        | 评测集 ID                         |
| `knowledge_base_id` | `UUID`         | FK NULL   | 默认关联知识库                    |
| `name`              | `VARCHAR(100)` | NOT NULL  | 评测集名称                        |
| `description`       | `TEXT`         | NULL      | 评测集描述                        |
| `status`            | `VARCHAR(32)`  | NOT NULL  | `active` / `disabled` / `deleted` |
| `sample_count`      | `INTEGER`      | DEFAULT 0 | 样本数量                          |
| `metadata`          | `JSONB`        | NULL      | 扩展信息                          |
| `created_by`        | `UUID`         | NULL      | 创建者扩展字段                    |
| `updated_by`        | `UUID`         | NULL      | 更新者扩展字段                    |
| `created_at`        | `TIMESTAMPTZ`  | NOT NULL  | 创建时间                          |
| `updated_at`        | `TIMESTAMPTZ`  | NOT NULL  | 更新时间                          |
| `deleted_at`        | `TIMESTAMPTZ`  | NULL      | 删除时间                          |

建议索引：

| 索引                          | 字段                |
| ----------------------------- | ------------------- |
| `idx_eval_dataset_kb_id`      | `knowledge_base_id` |
| `idx_eval_dataset_status`     | `status`            |
| `idx_eval_dataset_created_at` | `created_at`        |

说明：

1. 一个评测集可以默认绑定知识库，也可以在评测任务中指定知识库。
2. 第一版不做复杂数据集版本管理。
3. 评测数据集属于可复用资产，采用软删除。

------

## 7.9 evaluation_samples

评测样本表，用于保存问题、参考答案、期望引用和标签。

| 字段                    | 类型          | 约束     | 说明                   |
| ----------------------- | ------------- | -------- | ---------------------- |
| `id`                    | `UUID`        | PK       | 样本 ID                |
| `dataset_id`            | `UUID`        | FK       | 评测集 ID              |
| `question`              | `TEXT`        | NOT NULL | 评测问题               |
| `reference_answer`      | `TEXT`        | NULL     | 参考答案               |
| `expected_document_ids` | `JSONB`       | NULL     | 期望命中文档 ID 列表   |
| `expected_chunk_ids`    | `JSONB`       | NULL     | 期望命中 chunk ID 列表 |
| `tags`                  | `JSONB`       | NULL     | 标签                   |
| `difficulty`            | `VARCHAR(32)` | NULL     | 难度                   |
| `metadata`              | `JSONB`       | NULL     | 扩展信息               |
| `created_at`            | `TIMESTAMPTZ` | NOT NULL | 创建时间               |
| `updated_at`            | `TIMESTAMPTZ` | NOT NULL | 更新时间               |

建议索引：

| 索引                         | 字段         |
| ---------------------------- | ------------ |
| `idx_eval_sample_dataset_id` | `dataset_id` |
| `idx_eval_sample_difficulty` | `difficulty` |
| `idx_eval_sample_created_at` | `created_at` |

说明：

1. 第一版 `expected_document_ids` 和 `expected_chunk_ids` 使用 `JSONB`，便于快速实现。
2. 如果后续需要强关系约束，可拆分为 `evaluation_sample_expected_refs` 表。
3. `tags` 用于标记问题类型、业务场景或错误类别。
4. 样本属于评测集明细，默认不使用软删除。
5. 删除错误导入或无效样本时，可直接物理删除。

------

## 7.10 evaluation_tasks

评测任务表，用于保存一次批量评测的配置和状态。

| 字段                | 类型               | 约束      | 说明                        |
| ------------------- | ------------------ | --------- | --------------------------- |
| `id`                | `UUID`             | PK        | 评测任务 ID                 |
| `dataset_id`        | `UUID`             | FK        | 评测集 ID                   |
| `knowledge_base_id` | `UUID`             | FK        | 目标知识库                  |
| `name`              | `VARCHAR(100)`     | NOT NULL  | 任务名称                    |
| `qa_mode`           | `VARCHAR(32)`      | NOT NULL  | `basic_rag` / `agentic_rag` |
| `status`            | `VARCHAR(32)`      | NOT NULL  | 评测任务状态                |
| `retrieval_config`  | `JSONB`            | NULL      | 检索配置                    |
| `rerank_config`     | `JSONB`            | NULL      | Rerank 配置                 |
| `model_config`      | `JSONB`            | NULL      | 模型配置                    |
| `prompt_version`    | `VARCHAR(100)`     | NULL      | Prompt 版本                 |
| `total_count`       | `INTEGER`          | DEFAULT 0 | 样本总数                    |
| `success_count`     | `INTEGER`          | DEFAULT 0 | 成功数                      |
| `failed_count`      | `INTEGER`          | DEFAULT 0 | 失败数                      |
| `average_score`     | `DOUBLE PRECISION` | NULL      | 平均得分                    |
| `error_message`     | `TEXT`             | NULL      | 任务级失败原因              |
| `started_at`        | `TIMESTAMPTZ`      | NULL      | 开始时间                    |
| `finished_at`       | `TIMESTAMPTZ`      | NULL      | 结束时间                    |
| `trace_id`          | `VARCHAR(100)`     | NULL      | 任务级 Trace                |
| `metadata`          | `JSONB`            | NULL      | 扩展信息                    |
| `created_by`        | `UUID`             | NULL      | 创建者扩展字段              |
| `updated_by`        | `UUID`             | NULL      | 更新者扩展字段              |
| `created_at`        | `TIMESTAMPTZ`      | NOT NULL  | 创建时间                    |
| `updated_at`        | `TIMESTAMPTZ`      | NOT NULL  | 更新时间                    |
| `deleted_at`        | `TIMESTAMPTZ`      | NULL      | 删除时间                    |

建议索引：

| 索引                       | 字段                |
| -------------------------- | ------------------- |
| `idx_eval_task_dataset_id` | `dataset_id`        |
| `idx_eval_task_kb_id`      | `knowledge_base_id` |
| `idx_eval_task_status`     | `status`            |
| `idx_eval_task_created_at` | `created_at`        |
| `idx_eval_task_trace_id`   | `trace_id`          |

说明：

1. 评测配置必须快照保存，否则后续难以复现实验结果。
2. 批量评测应通过任务状态查询，不应长时间阻塞接口。
3. `average_score` 是汇总值，样本级得分保存在 `evaluation_results`。
4. 评测任务属于实验资产，采用软删除或归档保留。
5. 删除或清理评测任务时，可物理删除对应 `evaluation_results`。

------

## 7.11 evaluation_results

评测结果表，用于保存单个样本在一次评测任务中的执行结果。

| 字段                 | 类型               | 约束     | 说明                      |
| -------------------- | ------------------ | -------- | ------------------------- |
| `id`                 | `UUID`             | PK       | 评测结果 ID               |
| `task_id`            | `UUID`             | FK       | 评测任务 ID               |
| `sample_id`          | `UUID`             | FK       | 评测样本 ID               |
| `qa_record_id`       | `UUID`             | FK NULL  | 关联问答记录              |
| `agent_run_id`       | `UUID`             | FK NULL  | 关联 Agentic RAG 执行记录，仅 agentic_rag 评测使用 |  
| `question`           | `TEXT`             | NOT NULL | 执行时的问题快照          |
| `generated_answer`   | `TEXT`             | NULL     | 生成答案                  |
| `reference_answer`   | `TEXT`             | NULL     | 参考答案快照              |
| `retrieved_chunks`   | `JSONB`            | NULL     | 检索结果摘要              |
| `citations`          | `JSONB`            | NULL     | 引用结果摘要              |
| `retrieval_score`    | `DOUBLE PRECISION` | NULL     | 检索相关性得分            |
| `answer_score`       | `DOUBLE PRECISION` | NULL     | 回答质量得分              |
| `citation_score`     | `DOUBLE PRECISION` | NULL     | 引用质量得分              |
| `faithfulness_score` | `DOUBLE PRECISION` | NULL     | 忠实度得分                |
| `overall_score`      | `DOUBLE PRECISION` | NULL     | 综合得分                  |
| `status`             | `VARCHAR(32)`      | NOT NULL | `success` / `failed`      |
| `error_message`      | `TEXT`             | NULL     | 失败原因                  |
| `judge_type`         | `VARCHAR(32)`      | NULL     | `manual` / `llm` / `rule` |
| `judge_comment`      | `TEXT`             | NULL     | 评分说明                  |
| `latency_ms`         | `INTEGER`          | NULL     | 样本执行耗时              |
| `trace_id`           | `VARCHAR(100)`     | NULL     | Trace ID                  |
| `created_at`         | `TIMESTAMPTZ`      | NOT NULL | 创建时间                  |
| `updated_at`         | `TIMESTAMPTZ`      | NOT NULL | 更新时间                  |

建议索引：

| 索引                        | 字段            |
| --------------------------- | --------------- |
| `idx_eval_result_task_id`   | `task_id`       |
| `idx_eval_result_sample_id` | `sample_id`     |
| `idx_eval_result_qa_id`     | `qa_record_id`  |
| `idx_eval_result_status`    | `status`        |
| `idx_eval_result_score`     | `overall_score` |
| `idx_eval_result_trace_id`  | `trace_id`      |

说明：

1. `retrieved_chunks` 和 `citations` 保存摘要快照，便于评测结果独立分析。
2. 完整执行链路通过 `trace_id` 查看。
3. 第一版评分字段可为空，先支持人工或规则写入，后续扩展 LLM-as-Judge。
4. `evaluation_results` 是高增长样本级结果表，不使用软删除。
5. 删除或清理评测任务时，可级联物理删除对应评测结果。

------

## 8. Qdrant Payload 设计

第一版建议使用单一 Qdrant collection，例如：

```text
forgerag_chunks
```

每个 point 对应一个 `document_chunks.id`。

### 8.1 Point ID

建议：

```text
point_id = chunk_id
```

这样 PostgreSQL 与 Qdrant 的关联最直接。

### 8.2 Payload 字段

| 字段                | 类型           | 说明                |
| ------------------- | -------------- | ------------------- |
| `knowledge_base_id` | `string`       | 知识库 ID，用于过滤 |
| `document_id`       | `string`       | 文档 ID             |
| `chunk_id`          | `string`       | chunk ID            |
| `chunk_index`       | `integer`      | chunk 序号          |
| `document_name`     | `string`       | 文档名              |
| `page_number`       | `integer/null` | 页码                |
| `section_title`     | `string/null`  | 章节标题            |
| `content_preview`   | `string`       | 文本预览            |
| `embedding_model`   | `string`       | Embedding 模型      |
| `created_at`        | `string`       | 写入时间            |

### 8.3 检索过滤

按知识库检索时，必须使用：

```text
knowledge_base_id = 当前请求的 knowledge_base_id
```

第一版不支持默认全库检索，避免跨知识库误召回。

------

## 9. 删除与数据一致性策略

ForgeRAG 第一版不对所有表统一使用软删除。不同数据的业务价值、数据量增长速度、是否可重建、是否需要审计追溯并不相同，因此删除策略采用分级设计。

总体原则如下：

1. **核心业务主表优先软删除**

   对知识库、文档、评测数据集、评测任务等具备业务管理意义的数据，优先使用软删除，避免误删后完全无法恢复。

2. **高增长明细表优先物理删除**

   对 chunk、引用来源、Agent 节点、评测样本结果等数量增长快、可由上级记录或外部 Trace 追溯的数据，不默认软删除，避免长期污染数据库。

3. **历史结果表保留必要快照**

   对问答记录、引用来源和评测结果，如果需要保留历史分析能力，应保存必要快照字段，而不是强依赖被删除的 chunk 或文档记录。

4. **向量数据必须同步删除**

   文档或 chunk 被删除时，Qdrant 中对应 point 必须同步删除，避免检索召回已删除内容。

5. **Trace 细节不由 PostgreSQL 承担长期存储**

   Agentic RAG 节点细节、Prompt、模型调用和 Span 细节应主要由 Langfuse 管理，PostgreSQL 只保存必要摘要和关联 ID。

------

### 9.1 删除策略总表

| 表                    | 删除策略                                           | 原因                                             |
| --------------------- | -------------------------------------------------- | ------------------------------------------------ |
| `knowledge_bases`     | 软删除                                             | 知识库是核心业务边界，误删影响大                 |
| `documents`           | 软删除                                             | 文档是核心业务资源，需要保留处理状态和失败原因   |
| `document_chunks`     | 物理删除                                           | chunk 数量大，软删除会严重污染检索关联和列表查询 |
| Qdrant points         | 物理删除                                           | 已删除文档的向量不应继续被召回                   |
| `qa_records`          | 默认保留，不提供普通删除；必要时可物理清理历史数据 | 问答记录用于历史追踪、评测和问题分析             |
| `qa_citations`        | 随 `qa_records` 物理删除；不单独软删除             | 引用属于问答明细，数量可能较大，且已有快照       |
| `agent_runs`          | 可保留近期摘要；支持定期物理清理                   | Agent run 可用于调试，但长期增长较快             |
| `agent_steps`         | 物理删除或定期清理                                 | 节点明细数量大，详细 Trace 应交给 Langfuse       |
| `evaluation_datasets` | 软删除                                             | 评测集是可复用业务资产                           |
| `evaluation_samples`  | 默认物理删除；随数据集状态过滤                     | 样本属于评测集明细，不一定需要长期保留删除记录   |
| `evaluation_tasks`    | 软删除或归档保留                                   | 评测任务用于实验对比                             |
| `evaluation_results`  | 随任务定期物理清理或归档                           | 样本级结果增长快，长期软删除负担较大             |

------

### 9.2 知识库删除策略

知识库删除采用软删除。

处理方式：

1. 将 `knowledge_bases.status` 更新为 `deleted`。
2. 写入 `knowledge_bases.deleted_at`。
3. 普通知识库列表、文档上传、检索和问答接口默认过滤 `deleted` 状态。
4. 第一版不级联物理删除问答记录和评测任务。
5. 如果需要彻底清理知识库，可提供内部维护脚本执行硬删除。

说明：

知识库属于高层业务边界，误删影响较大，因此不建议默认物理删除。但知识库删除后，是否立即清理其下文档、chunk 和向量数据，需要结合文档删除策略执行。

------

### 9.3 文档删除策略

文档删除采用“文档元数据软删除 + chunk 和向量物理删除”的混合策略。

处理方式：

1. 将 `documents.status` 更新为 `deleted`。
2. 写入 `documents.deleted_at`。
3. 物理删除该文档下的 `document_chunks`。
4. 根据 `qdrant_point_id` 或 `document_id` 物理删除 Qdrant 中的向量 point。
5. 不删除历史 `qa_records`。
6. 不删除历史 `qa_citations` 中已经保存的引用快照。
7. 后续普通检索和问答不得再召回该文档内容。

原因：

1. 文档本身是业务资源，保留软删除记录有助于追踪上传历史和处理状态。
2. chunk 数量可能很大，如果只做软删除，会导致 chunk 表膨胀。
3. Qdrant 中的向量如果不删除，会导致已删除文档继续被召回。
4. 历史问答已经通过 `qa_citations.quote_text`、`document_name`、`page_number` 等字段保存了引用快照，不应强依赖原始 chunk 永久存在。

------

### 9.4 Chunk 删除策略

`document_chunks` 默认使用物理删除，不使用软删除。

适用场景：

1. 文档被删除。
2. 文档重新入库。
3. 文档处理失败后清理中间数据。
4. 维护脚本清理孤儿 chunk。
5. 知识库彻底清理。

原因：

1. chunk 是 RAG 系统中最容易膨胀的数据。
2. 一个文档可能产生几十到几千个 chunk。
3. 软删除 chunk 会导致所有检索关联、引用查询和统计查询都必须附加过滤条件。
4. chunk 可由文档重新解析和切分生成，不属于必须长期保留的业务主数据。
5. 历史问答引用应保存快照，而不是依赖 chunk 永久存在。

因此，`document_chunks` 表第一版不设计 `deleted_at` 字段，直接采用物理删除。

------

### 9.5 Qdrant 向量删除策略

Qdrant point 必须采用物理删除。

删除触发场景：

1. 文档删除。
2. 文档重新处理。
3. chunk 清理。
4. 知识库彻底清理。
5. 发现 PostgreSQL 与 Qdrant 数据不一致。

删除依据：

1. 优先使用 `qdrant_point_id` 删除。
2. 如果需要批量清理，可以通过 payload 中的 `document_id` 或 `knowledge_base_id` 过滤删除。
3. 第一版建议 `qdrant_point_id = chunk_id`，降低清理复杂度。

要求：

1. PostgreSQL 删除 chunk 前，应先记录待删除 point ID。
2. 删除 Qdrant point 失败时，应记录错误日志。
3. 必要时提供补偿脚本，扫描 PostgreSQL 与 Qdrant 的不一致数据。
4. 已删除文档的向量不得继续参与普通检索。

------

### 9.6 问答记录删除策略

`qa_records` 第一版默认不提供普通删除能力，主要用于历史追踪、效果分析和问题排查。

处理原则：

1. 普通用户或调用方不直接删除问答记录。
2. 如果需要清理历史数据，应通过维护任务按时间范围物理删除。
3. 删除 `qa_records` 时，应级联物理删除对应 `qa_citations`。
4. `qa_records` 不建议使用软删除，避免历史记录表不断膨胀后还要维护 deleted 状态。
5. 如果后续出现合规或隐私删除需求，再单独设计数据清理策略。

原因：

1. 问答记录本身是运行结果，不是核心可管理资源。
2. 长期保留所有问答会产生大量数据。
3. 对问答记录做软删除意义有限，物理归档或按时间清理更合适。
4. 问答记录已经通过 `trace_id` 与外部观测系统关联，PostgreSQL 不应承担无限期日志存储职责。

------

### 9.7 引用来源删除策略

`qa_citations` 不单独使用软删除。

处理方式：

1. 创建问答记录时同步写入引用快照。
2. 删除问答记录时，级联物理删除对应引用。
3. 删除文档或 chunk 时，不回删历史引用。
4. 历史引用依靠 `quote_text`、`document_name`、`page_number`、`chunk_index` 等快照字段展示。

原因：

1. 引用来源是问答记录的明细数据。
2. 引用数量随问答次数增长较快。
3. 对引用表软删除会增加数据库负担。
4. 删除文档后，历史问答仍可通过引用快照保留当时回答依据。

------

### 9.8 Agentic RAG 记录删除策略

`agent_runs` 和 `agent_steps` 采用分级保留策略。

处理方式：

1. `agent_runs` 可保留近期摘要，用于调试和问题分析。
2. `agent_steps` 默认不使用软删除。
3. `agent_steps` 可按时间范围定期物理清理。
4. 对于已关联 `qa_records` 的重要 Agent run，可保留 `agent_runs` 摘要。
5. 详细节点输入输出、Prompt、模型调用细节应主要通过 Langfuse 查看。
6. 清理 `agent_runs` 时，应级联物理删除对应 `agent_steps`。

原因：

1. Agent 节点明细增长非常快。
2. 每次 Agentic RAG 可能产生多个 step。
3. 如果长期软删除 step，会造成明显数据膨胀。
4. PostgreSQL 只需要保存摘要，完整链路细节由 Langfuse 承担。

推荐策略：

| 数据           | 策略                                  |
| -------------- | ------------------------------------- |
| `agent_runs`   | 保留近期数据，支持定期物理清理        |
| `agent_steps`  | 随 run 级联物理删除，或按时间物理清理 |
| Langfuse Trace | 由 Langfuse 自身保留策略管理          |

------

### 9.9 评测数据删除策略

评测相关数据采用“评测资产软删除，执行结果可清理”的策略。

### 9.9.1 evaluation_datasets

评测数据集采用软删除。

原因：

1. 评测集是可复用资产。
2. 误删后影响评测任务复现。
3. 数据量相对可控。

处理方式：

1. 更新 `status = deleted`。
2. 写入 `deleted_at`。
3. 普通列表查询默认过滤已删除数据。

### 9.9.2 evaluation_samples

评测样本默认使用物理删除。

处理方式：

1. 删除单条无效样本时，直接物理删除。
2. 删除评测集时，普通查询通过评测集状态过滤样本。
3. 如需彻底清理评测集，可通过维护脚本物理删除其下样本。
4. 不建议对单条样本频繁做软删除管理。

原因：

1. 样本属于评测集明细。
2. 样本数量可能增长。
3. 单条样本删除历史通常没有长期保留价值。
4. 评测任务执行时会在 `evaluation_results` 中保存问题和参考答案快照。

### 9.9.3 evaluation_tasks

评测任务建议保留软删除或归档能力。

原因：

1. 评测任务体现一次实验配置。
2. 对比不同 RAG 参数时，需要保留任务记录。
3. 任务数量通常低于样本级结果数量。

### 9.9.4 evaluation_results

评测结果建议支持物理清理，不默认软删除。

处理方式：

1. 删除评测任务时，可级联物理删除对应 `evaluation_results`。
2. 对过旧的评测结果，可通过维护任务物理清理。
3. 重要实验结果可以通过任务状态或归档策略保留。

原因：

1. `evaluation_results` 是样本级执行明细，数量增长快。
2. 每次评测任务可能生成大量结果。
3. 对结果表使用软删除会导致评分查询、统计查询和对比查询变慢。
4. 评测结果如果需要长期保留，应考虑归档，而不是简单软删除。

------

### 9.10 物理删除与外键策略

对于使用物理删除的明细表，应合理使用外键级联。

建议：

| 父表                  | 子表                 | 删除策略                         |
| --------------------- | -------------------- | -------------------------------- |
| `documents`           | `document_chunks`    | 文档删除时物理删除 chunks        |
| `qa_records`          | `qa_citations`       | 问答记录删除时级联删除 citations |
| `agent_runs`          | `agent_steps`        | Agent run 删除时级联删除 steps   |
| `evaluation_datasets` | `evaluation_samples` | 彻底清理数据集时物理删除 samples |
| `evaluation_tasks`    | `evaluation_results` | 任务物理清理时级联删除 results   |

注意：

1. 对核心主表，不建议随意开启数据库级 `ON DELETE CASCADE`。
2. 对明显属于明细数据的表，可以使用级联删除。
3. Service 层仍应显式表达删除流程，避免误删。
4. 对 Qdrant 的删除不能只依赖数据库外键，必须由业务逻辑或补偿任务处理。

------

### 9.11 推荐保留 deleted_at 的表

以下表建议保留 `deleted_at`：

```text
knowledge_bases
documents
evaluation_datasets
evaluation_tasks
```

原因：

1. 它们属于核心业务资源或实验资产。
2. 误删除后有恢复价值。
3. 数据量相对可控。
4. 列表查询可以通过状态和索引过滤。

------

### 9.12 不建议保留 deleted_at 的表

以下表第一版不建议保留 `deleted_at`：

```text
document_chunks
qa_citations
agent_steps
evaluation_samples
evaluation_results
```

原因：

1. 它们是明细型或高增长数据。
2. 软删除会明显增加表体积。
3. 查询时长期携带过滤条件，容易污染业务逻辑。
4. 这些数据通常可以通过父级记录、快照或外部 Trace 追溯。
5. 对这类数据，物理删除、归档或定期清理更合理。

------

### 9.13 可按时间定期清理的表

以下表可以后续设计定期清理任务：

| 表                   | 建议清理条件                                     |
| -------------------- | ------------------------------------------------ |
| `qa_records`         | 清理超过保留周期且非评测关联的数据               |
| `qa_citations`       | 随 `qa_records` 删除                             |
| `agent_runs`         | 清理超过保留周期且非重要记录的数据               |
| `agent_steps`        | 随 `agent_runs` 删除或单独按时间删除             |
| `evaluation_results` | 清理过旧、非归档任务的结果                       |
| `documents`          | 对已删除超过保留期的文档元数据做硬删除           |
| `knowledge_bases`    | 对已删除超过保留期且确认无关联价值的数据做硬删除 |

第一版可以先不实现定时任务，但数据库设计应允许后续添加维护脚本或后台任务。

------

### 9.14 删除策略总结

ForgeRAG 第一版删除策略总结如下：

```text
核心业务资源：软删除
高增长明细数据：物理删除
向量数据：物理删除
历史结果数据：保留快照，支持定期清理
完整 Trace：交给 Langfuse 管理
```

最终建议：

1. `knowledge_bases`、`documents`、`evaluation_datasets`、`evaluation_tasks` 保留软删除。
2. `document_chunks`、`qa_citations`、`agent_steps`、`evaluation_samples`、`evaluation_results` 默认物理删除。
3. `qa_records` 默认保留，但历史清理时使用物理删除。
4. `agent_runs` 保留摘要，但支持定期物理清理。
5. Qdrant point 必须随 chunk 删除而物理删除。
6. 历史问答引用依赖引用快照，不依赖 chunk 永久存在。
7. 删除策略必须由 Service 层统一编排，避免 PostgreSQL 与 Qdrant 数据不一致。

------

## 10. 索引设计总结

| 表                    | 重点索引                                                     |
| --------------------- | ------------------------------------------------------------ |
| `knowledge_bases`     | `status`、`created_at`、未删除名称唯一                       |
| `documents`           | `knowledge_base_id`、`status`、`file_hash`、`created_at`     |
| `document_chunks`     | `knowledge_base_id`、`document_id`、`qdrant_point_id`、`embedding_status` |
| `qa_records`          | `knowledge_base_id`、`status`、`qa_mode`、`trace_id`、`created_at` |
| `qa_citations`        | `qa_record_id`、`chunk_id`、`document_id`                    |
| `agent_runs`          | `qa_record_id`、`knowledge_base_id`、`status`、`trace_id`    |
| `agent_steps`         | `agent_run_id`、`step_name`、`trace_id/span_id`              |
| `evaluation_datasets` | `knowledge_base_id`、`status`                                |
| `evaluation_samples`  | `dataset_id`、`difficulty`                                   |
| `evaluation_tasks`    | `dataset_id`、`knowledge_base_id`、`status`、`trace_id`      |
| `evaluation_results`  | `task_id`、`sample_id`、`qa_record_id`、`overall_score`、`trace_id` |

------

## 11. Alembic 迁移建议

第一版数据库迁移建议拆分为以下步骤：

```text
001_create_knowledge_bases
002_create_documents
003_create_document_chunks
004_create_qa_records_and_citations
005_create_agent_runs_and_steps
006_create_evaluation_tables
007_add_indexes
```

迁移原则：

1. 所有表结构变更必须通过 Alembic 管理。
2. 不直接手动修改数据库结构后跳过迁移文件。
3. 枚举字段第一版使用 `VARCHAR`，降低迁移复杂度。
4. `JSONB` 用于保存配置快照和扩展字段。
5. 索引单独检查，避免遗漏常用查询路径。
6. 迁移文件应能在本地 Docker Compose 环境中重复执行验证。
7. 软删除字段只添加到确实需要软删除的表。
8. 高增长明细表不添加 `deleted_at`，避免形成无意义字段。

------

## 12. 第一版暂不设计的表

为避免过度设计，以下表第一版暂不创建：

| 表                            | 暂不设计原因                               |
| ----------------------------- | ------------------------------------------ |
| `users`                       | 第一版不实现完整登录注册                   |
| `roles` / `permissions`       | 第一版不做复杂 RBAC                        |
| `organizations` / `tenants`   | 第一版不做多租户                           |
| `document_versions`           | 第一版文档重新入库采用简单替换策略         |
| `prompt_versions`             | 第一版用配置或文件管理 Prompt，后续再入库  |
| `model_configs`               | 第一版模型配置通过环境变量和配置文件管理   |
| `audit_logs`                  | 第一版只保留结构化日志和 Trace             |
| `billing_records`             | 项目不做商业化 SaaS                        |
| `archived_qa_records`         | 第一版暂不做归档表，后续数据量增大后再设计 |
| `archived_evaluation_results` | 第一版暂不做归档表，后续根据评测数据量扩展 |

这些能力后续可以根据项目进度逐步扩展。

------

## 13. 数据库设计总结

ForgeRAG 第一版数据库设计围绕以下核心表展开：

```text
knowledge_bases
documents
document_chunks
qa_records
qa_citations
agent_runs
agent_steps
evaluation_datasets
evaluation_samples
evaluation_tasks
evaluation_results
```

设计重点是：

1. 用 `knowledge_base_id` 保证知识库边界。
2. 用 `document_id` 和 `chunk_id` 保证引用溯源。
3. 用 `qdrant_point_id` 对齐 PostgreSQL 与 Qdrant。
4. 用 `qa_record_id` 和 `qa_citations` 保存带引用问答结果。
5. 用 `agent_runs` 和 `agent_steps` 保存 Agentic RAG 流程摘要。
6. 用 `evaluation_tasks` 和 `evaluation_results` 支撑 RAG 自动化评测。
7. 用 `trace_id` 和 `request_id` 关联 Langfuse 与结构化日志。
8. 用 Alembic 管理所有数据库结构变更。
9. 用分级删除策略控制数据膨胀和查询污染。

该设计保证第一版能够支撑文档入库、语义检索、Rerank、带引用问答、Agentic RAG、自动化评测和链路追踪，同时避免过早引入复杂权限、多租户和商业化平台表结构。

删除策略上，本设计不再对所有表统一使用软删除，而是采用：

```text
核心业务资源软删除
高增长明细数据物理删除
向量数据物理删除
历史问答保留引用快照
完整链路细节交给 Langfuse
```

这样可以在保证业务可追溯的同时，减少 chunk、引用、Agent 节点和评测结果等高增长数据对 PostgreSQL 的长期压力。