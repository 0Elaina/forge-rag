# ForgeRAG RAG 核心链路设计

## 1. 文档目的

本文档用于定义 ForgeRAG 第一版 RAG 核心链路设计，承接 `docs/02-requirements-analysis.md`、`docs/03-architecture-design.md`、`docs/04-database-design.md` 和 `docs/05-api-design.md` 中已经确定的需求、架构、数据模型和接口边界。

本文档重点说明：

1. 文档入库链路如何执行。
2. 文本解析、清洗、切分、向量化如何协作。
3. PostgreSQL 中的 chunk 与 Qdrant point 如何保持一致。
4. 语义检索、Rerank、Prompt 和 LLM 生成如何组成基础 RAG 问答链路。
5. 回答引用如何生成、保存和返回。
6. RAG 链路中的异常、降级、配置和可观测性如何设计。

本文档不重复定义 API 路径、数据库字段、Agentic RAG 状态图、评测指标和 Langfuse 接入细节。相关内容由 API 设计、数据库设计、Agentic RAG 设计、评测设计和可观测性设计文档负责。

------

## 2. 设计边界

### 2.1 本文档覆盖范围

本文档覆盖基础 RAG 主链路：

```text
文档上传
  → 文档解析
  → 文本清洗
  → 文本切分
  → 保存 chunk
  → Embedding
  → 写入 Qdrant
  → 用户提问
  → 问题向量化
  → 语义检索
  → Rerank
  → 构造 Prompt
  → LLM 生成
  → 返回答案和引用
```

### 2.2 本文档不覆盖范围

以下内容不在本文档展开：

1. Agentic RAG 的节点、状态、条件边和二次检索决策。
2. RAG 自动化评测的指标、评分规则和任务调度。
3. Langfuse Trace / Span 的完整字段设计。
4. 完整权限系统、多租户和审计能力。
5. 多模态 RAG、知识图谱 RAG 和复杂混合检索。
6. Prompt 在线版本管理和模型配置后台管理。

------

## 3. 核心链路总览

ForgeRAG 第一版 RAG 核心链路分为两个阶段：

1. **知识入库阶段**

   将原始文档转换为可检索的 chunk 和向量。

2. **检索问答阶段**

   根据用户问题检索相关 chunk，经过 Rerank 和 Prompt 构造后生成带引用回答。

整体流程如下：

```text
知识入库阶段：

Document
  → ParsedText
  → CleanText
  → Chunk[]
  → Embedding[]
  → Qdrant Point[]

检索问答阶段：

Question
  → QueryEmbedding
  → RetrievedChunk[]
  → RerankedChunk[]
  → Prompt
  → Answer
  → Citation[]
```

第一版目标不是实现所有高级 RAG 技术，而是保证主链路稳定、可测试、可追踪、可复现。

------

## 4. 文档入库链路设计

### 4.1 入库入口

文档入库由文档处理接口或内部 Service 触发。

输入：

| 输入                | 说明          |
| ------------------- | ------------- |
| `document_id`       | 文档 ID       |
| `knowledge_base_id` | 所属知识库 ID |
| `file_path`         | 文件存储路径  |
| `file_ext`          | 文件扩展名    |
| `metadata`          | 文档扩展信息  |

输出：

| 输出          | 说明            |
| ------------- | --------------- |
| `status`      | 文档处理状态    |
| `chunk_count` | 生成 chunk 数量 |
| `parse_error` | 失败原因        |
| `trace_id`    | 可选链路追踪 ID |

### 4.2 入库流程

```text
1. 校验文档状态
2. 将文档状态更新为 processing
3. 读取原始文件
4. 解析文本内容
5. 清洗文本
6. 切分 chunk
7. 保存 chunk 到 PostgreSQL
8. 调用 Embedding 模型生成向量
9. 写入 Qdrant
10. 更新 chunk 向量化状态
11. 更新文档状态为 completed
12. 记录日志和 Trace
```

### 4.3 状态流转

文档状态遵循数据库设计中的枚举：

```text
uploaded → processing → completed
                    └── failed
```

处理要求：

1. 开始处理前必须将状态更新为 `processing`。
2. 任一关键步骤失败时，文档状态更新为 `failed`。
3. 失败原因写入 `parse_error`。
4. 处理成功后更新 `chunk_count` 和处理完成时间。
5. 文档处理过程应具备幂等保护，避免重复入库产生脏数据。

------

## 5. 文档解析与清洗设计

### 5.1 文档解析

第一版优先支持文本类和常见办公文档格式，例如：

| 类型     | 示例    |
| -------- | ------- |
| 纯文本   | `.txt`  |
| Markdown | `.md`   |
| PDF      | `.pdf`  |
| Word     | `.docx` |

解析输出统一为内部文本结构：

```text
ParsedDocument
  ├── document_id
  ├── text
  ├── pages
  └── metadata
```

设计要求：

1. 解析模块只负责从文件中提取文本。
2. 不在解析模块中执行 Embedding、检索或问答逻辑。
3. 解析失败时抛出明确异常，由 Service 层更新文档状态。
4. 对空文件或无有效文本的文件，应标记为处理失败。

### 5.2 文本清洗

文本清洗目标是减少明显噪声，不做过度语义改写。

第一版清洗规则：

1. 去除连续多余空白。
2. 规范换行。
3. 去除不可见控制字符。
4. 去除明显无意义的空段落。
5. 保留标题、段落、页码等可用于溯源的信息。

不做以下处理：

1. 不自动总结原文。
2. 不修改事实内容。
3. 不删除可能影响引用溯源的正文。
4. 不使用 LLM 对文档内容做重写。

------

## 6. Chunk 切分设计

### 6.1 切分目标

Chunk 是 ForgeRAG 检索、引用和评测的最小知识单元。

切分目标：

1. 保证每个 chunk 语义相对完整。
2. 控制每个 chunk 的长度，避免上下文过长。
3. 保留来源信息，支持引用溯源。
4. 支持后续对切分策略进行评测和调优。

### 6.2 第一版切分策略

第一版建议采用递归字符切分或按 Markdown / 段落结构优先切分。

默认策略：

```text
优先按标题切分
  → 再按段落切分
  → 再按句子或字符长度切分
```

默认配置建议：

| 参数             | 建议值     | 说明                |
| ---------------- | ---------- | ------------------- |
| `chunk_size`     | 800 - 1200 | 单个 chunk 目标长度 |
| `chunk_overlap`  | 100 - 200  | 相邻 chunk 重叠长度 |
| `min_chunk_size` | 100        | 过短文本可合并      |
| `max_chunk_size` | 1500       | 超出后强制切分      |

实际数值应通过配置管理，不写死在业务代码中。

### 6.3 Chunk 元数据

每个 chunk 至少需要包含以下元数据：

| 元数据              | 说明                 |
| ------------------- | -------------------- |
| `knowledge_base_id` | 所属知识库           |
| `document_id`       | 所属文档             |
| `chunk_index`       | 文档内序号           |
| `content`           | chunk 文本           |
| `page_number`       | 页码，可为空         |
| `section_title`     | 标题，可为空         |
| `start_offset`      | 原文起始位置，可为空 |
| `end_offset`        | 原文结束位置，可为空 |
| `splitter_name`     | 切分器名称           |
| `splitter_config`   | 切分参数快照         |

### 6.4 切分结果保存

切分后的 chunk 保存到 `document_chunks`。

保存要求：

1. chunk 文本必须保存到 PostgreSQL。
2. chunk 向量不保存到 PostgreSQL。
3. `chunk_index` 在同一文档内应保持顺序唯一。
4. `splitter_config` 应保存当前切分参数，便于复现。
5. chunk 默认不软删除，文档重新处理时旧 chunk 物理删除。

------

## 7. Embedding 与向量入库设计

### 7.1 Embedding 输入

Embedding 输入为 chunk 文本。

输入结构：

```text
EmbeddingInput
  ├── chunk_id
  ├── content
  ├── knowledge_base_id
  └── document_id
```

处理要求：

1. 支持批量 Embedding。
2. 空文本不得进入 Embedding。
3. 超长文本应在切分阶段处理，不应在 Embedding 阶段临时截断。
4. Embedding 模型名称、维度和服务地址通过配置管理。

### 7.2 向量写入 Qdrant

第一版使用单一 collection：

```text
forgerag_chunks
```

推荐设计：

```text
qdrant_point_id = chunk_id
```

这样 PostgreSQL 与 Qdrant 可以直接通过 `chunk_id` 对齐。

### 7.3 Qdrant Payload

每个 point 的 payload 至少包含：

| 字段                | 说明                |
| ------------------- | ------------------- |
| `knowledge_base_id` | 用于知识库过滤      |
| `document_id`       | 用于文档关联        |
| `chunk_id`          | 用于回查 PostgreSQL |
| `chunk_index`       | chunk 序号          |
| `document_name`     | 展示用文档名        |
| `page_number`       | 页码，可为空        |
| `section_title`     | 标题，可为空        |
| `content_preview`   | 文本预览            |
| `embedding_model`   | Embedding 模型      |
| `created_at`        | 写入时间            |

### 7.4 向量化状态

chunk 向量化状态遵循：

```text
pending → completed
       └── failed
```

处理要求：

1. chunk 创建后默认 `pending`。
2. 向量写入 Qdrant 成功后更新为 `completed`。
3. 向量生成或写入失败时更新为 `failed`。
4. 文档整体处理失败时，应记录失败原因并避免状态不一致。
5. 允许后续对 `failed` chunk 进行重试扩展。

------

## 8. 文档重新处理与删除一致性

### 8.1 重新处理文档

文档重新处理用于修复处理失败、调整切分策略或重新生成向量。

处理流程：

```text
1. 校验文档是否存在且未删除
2. 删除旧 Qdrant point
3. 物理删除旧 document_chunks
4. 重置文档状态为 processing
5. 重新解析、清洗、切分、向量化
6. 更新文档状态和 chunk_count
```

要求：

1. 旧 chunk 必须先清理，避免重复召回。
2. Qdrant point 必须同步删除。
3. 重新处理后的 chunk 重新生成 ID。
4. 历史问答引用不回删，因为 `qa_citations` 已保存引用快照。

### 8.2 删除文档

文档删除策略与数据库设计保持一致：

1. 文档元数据软删除。
2. chunk 物理删除。
3. Qdrant point 物理删除。
4. 历史问答记录不删除。
5. 历史引用快照不删除。
6. 后续检索不得召回已删除文档内容。

------

## 9. 语义检索设计

### 9.1 检索输入

检索输入来自检索接口、基础 QA 流程或 Agentic RAG 流程。

输入结构：

```text
RetrievalInput
  ├── knowledge_base_id
  ├── query
  ├── top_k
  ├── score_threshold
  └── metadata_filter
```

### 9.2 检索流程

```text
1. 校验知识库状态
2. 校验 query 非空
3. 调用 Embedding 模型生成 query 向量
4. 使用 knowledge_base_id 过滤 Qdrant
5. 执行向量相似度检索
6. 过滤低于 score_threshold 的结果
7. 根据 chunk_id 回查或补充 PostgreSQL 元数据
8. 返回结构化候选结果
9. 记录检索日志和 Trace
```

### 9.3 检索约束

1. 第一版必须传入 `knowledge_base_id`。
2. 第一版不支持默认全库检索。
3. 检索结果必须包含 `chunk_id`、`document_id`、`content`、`score` 和来源信息。
4. 无结果时返回空数组，不视为系统异常。
5. 检索参数应有默认配置，也允许调用方在接口层覆盖。

### 9.4 检索输出

```text
RetrievedChunk
  ├── chunk_id
  ├── document_id
  ├── document_name
  ├── content
  ├── score
  ├── page_number
  ├── section_title
  └── metadata
```

------

## 10. Rerank 重排设计

### 10.1 Rerank 目标

Rerank 用于对向量检索召回的候选 chunk 进行二次排序，提高最终上下文质量。

Rerank 解决的问题：

1. 向量相似度高但实际相关性不足。
2. 多个 chunk 内容相近，需要选择更准确的片段。
3. 最终传入 LLM 的上下文数量有限，需要优先保留高价值内容。

### 10.2 Rerank 输入

```text
RerankInput
  ├── query
  ├── candidates
  ├── top_n
  └── score_threshold
```

### 10.3 Rerank 输出

```text
RerankedChunk
  ├── chunk_id
  ├── content
  ├── retrieval_score
  ├── rerank_score
  ├── rank
  └── source_metadata
```

### 10.4 降级策略

Rerank 是增强能力，不应成为基础 RAG 链路的单点故障。

降级规则：

1. Rerank 未启用时，直接使用向量检索排序。
2. Rerank 服务异常时，记录日志和 Trace。
3. Rerank 异常不直接导致问答失败。
4. 降级后使用原始检索结果进入 Prompt 构造。
5. 响应或 Trace 中应能看出是否发生降级。

------

## 11. 上下文选择设计

### 11.1 上下文选择目标

上下文选择负责从检索和重排结果中选出最终传入 LLM 的文本片段。

目标：

1. 控制上下文总长度。
2. 保留最相关 chunk。
3. 避免重复文本占用窗口。
4. 保证引用和上下文一致。

### 11.2 选择规则

第一版采用简单可控规则：

1. 按 `rerank_score` 或 `retrieval_score` 排序。
2. 选择前 `context_top_n` 个 chunk。
3. 限制总 token 数或总字符数。
4. 去除内容高度重复的 chunk。
5. 保留原始来源信息用于引用。

### 11.3 上下文输出

```text
SelectedContext
  ├── chunks
  ├── total_chars
  ├── total_tokens
  └── source_map
```

`source_map` 用于保证 Prompt 中的上下文编号与最终引用来源一致。

------

## 12. Prompt 构造设计

### 12.1 Prompt 目标

Prompt 应约束模型基于检索上下文回答，并在依据不足时拒答。

核心目标：

1. 明确用户问题。
2. 明确可用上下文。
3. 要求基于上下文回答。
4. 禁止编造知识库中不存在的信息。
5. 要求无法回答时给出明确提示。
6. 保持引用编号与上下文片段一致。

### 12.2 Prompt 输入

```text
PromptInput
  ├── question
  ├── selected_context
  ├── answer_policy
  └── output_format_instruction
```

### 12.3 Prompt 模板结构

第一版建议模板结构：

```text
你是企业知识库问答助手。
请只根据给定上下文回答用户问题。
如果上下文不足以回答，请说明无法从知识库中找到足够依据。

用户问题：
{question}

知识库上下文：
[1] {chunk_1}
[2] {chunk_2}
[3] {chunk_3}

回答要求：
1. 优先基于上下文回答。
2. 不要编造上下文中不存在的事实。
3. 如果无法回答，返回无法回答原因。
4. 回答应简洁、准确。
```

### 12.4 Prompt 管理要求

1. Prompt 模板集中放在 `core/prompt` 或配置目录。
2. 业务代码不应散落拼接 Prompt。
3. `prompt_version` 应写入问答记录或评测配置快照。
4. 第一版不单独设计 Prompt 数据表。
5. 后续需要在线管理时，再扩展 Prompt 版本表和管理接口。

------

## 13. LLM 生成设计

### 13.1 LLM 输入

LLM 输入为构造后的 Prompt 和模型配置。

```text
LLMInput
  ├── prompt
  ├── model_name
  ├── temperature
  ├── max_tokens
  └── timeout
```

### 13.2 LLM 输出

```text
LLMOutput
  ├── answer
  ├── input_tokens
  ├── output_tokens
  ├── latency_ms
  └── raw_response
```

`raw_response` 默认不直接返回给调用方，可写入 Trace 或日志摘要。

### 13.3 生成约束

1. 默认使用较低 temperature，降低随机性。
2. 控制最大输出长度。
3. 设置调用超时时间。
4. 模型服务异常时返回统一错误。
5. 不将模型原始异常堆栈暴露给 API 调用方。

------

## 14. 引用生成设计

### 14.1 引用来源

引用来源必须来自最终传入 Prompt 的 selected context，而不是来自未使用的召回结果。

引用来源包括：

| 字段              | 说明         |
| ----------------- | ------------ |
| `document_id`     | 文档 ID      |
| `chunk_id`        | chunk ID     |
| `document_name`   | 文档名       |
| `quote_text`      | 引用片段快照 |
| `page_number`     | 页码，可为空 |
| `chunk_index`     | chunk 序号   |
| `retrieval_score` | 检索得分     |
| `rerank_score`    | 重排得分     |
| `citation_order`  | 引用顺序     |

### 14.2 引用保存

问答成功或拒答时，按实际情况保存：

1. 成功回答：保存使用到的引用来源。
2. 拒答但存在低质量检索结果：第一版可以不保存引用，或只在 Trace 中记录。
3. 系统异常：不保存引用，只保存错误状态和 Trace。
4. 引用快照写入 `qa_citations`，避免后续 chunk 删除导致历史问答失去依据。

### 14.3 引用一致性要求

1. 返回引用必须来自生成回答使用过的上下文。
2. 不返回未进入 Prompt 的 chunk 作为引用。
3. 引用顺序应与上下文编号或相关性排序一致。
4. 删除文档后，不回删历史引用快照。
5. 历史问答展示应优先使用 `qa_citations.quote_text`。

------

## 15. 基础 RAG 问答流程

### 15.1 流程输入

```text
QAInput
  ├── knowledge_base_id
  ├── question
  ├── retrieval_config
  ├── rerank_config
  ├── model_config
  └── client_id
```

### 15.2 流程步骤

```text
1. 创建 request_id 和 trace_id
2. 校验知识库状态
3. 校验问题内容
4. 执行语义检索
5. 判断检索结果是否为空
6. 执行 Rerank 或降级
7. 选择最终上下文
8. 判断上下文是否足够
9. 构造 Prompt
10. 调用 LLM
11. 生成答案
12. 保存 qa_records
13. 保存 qa_citations
14. 返回结构化结果
15. 记录日志和 Trace
```

### 15.3 拒答规则

以下情况应拒答或返回无法回答提示：

1. 检索结果为空。
2. 最高检索得分低于阈值。
3. Rerank 后无有效上下文。
4. 上下文与问题明显不相关。
5. LLM 输出无法基于上下文形成可靠回答。

拒答结果应保存到 `qa_records`：

```text
status = refused
answer = null
refuse_reason = "知识库中没有足够依据回答该问题"
```

### 15.4 成功输出

```text
QAOutput
  ├── qa_record_id
  ├── answer
  ├── status
  ├── answerable
  ├── citations
  ├── latency_ms
  ├── request_id
  └── trace_id
```

------

## 16. 异常与降级策略

### 16.1 文档入库异常

| 异常             | 处理方式                                        |
| ---------------- | ----------------------------------------------- |
| 文件不存在       | 文档状态更新为 `failed`                         |
| 文件类型不支持   | 拒绝处理并返回业务错误                          |
| 文本解析失败     | 文档状态更新为 `failed`，写入 `parse_error`     |
| 清洗后无有效文本 | 文档状态更新为 `failed`                         |
| chunk 保存失败   | 回滚事务或标记失败                              |
| Embedding 失败   | 文档状态更新为 `failed`                         |
| Qdrant 写入失败  | 文档状态更新为 `failed`，必要时清理已写入 point |

### 16.2 检索问答异常

| 异常          | 处理方式                     |
| ------------- | ---------------------------- |
| 知识库不存在  | 返回 `KB_NOT_FOUND`          |
| 知识库不可用  | 返回 `KB_DISABLED`           |
| 检索结果为空  | 返回拒答或空检索结果         |
| Qdrant 异常   | 返回 `VECTOR_STORE_ERROR`    |
| Rerank 异常   | 降级使用原始检索排序         |
| LLM 异常      | 返回 `MODEL_SERVICE_ERROR`   |
| Langfuse 异常 | 记录本地日志，不阻断核心流程 |

------

## 17. 配置参数设计

第一版 RAG 链路参数通过配置文件或环境变量管理，接口可以覆盖部分参数。

### 17.1 文档处理配置

| 参数                     | 说明               |
| ------------------------ | ------------------ |
| `allowed_file_types`     | 允许上传的文件类型 |
| `max_file_size_mb`       | 最大文件大小       |
| `storage_dir`            | 本地文件存储目录   |
| `parser_timeout_seconds` | 解析超时时间       |

### 17.2 切分配置

| 参数             | 说明            |
| ---------------- | --------------- |
| `chunk_size`     | chunk 目标长度  |
| `chunk_overlap`  | chunk 重叠长度  |
| `min_chunk_size` | 最小 chunk 长度 |
| `splitter_name`  | 切分器名称      |

### 17.3 Embedding 配置

| 参数                        | 说明               |
| --------------------------- | ------------------ |
| `embedding_model`           | Embedding 模型名称 |
| `embedding_dim`             | 向量维度           |
| `embedding_batch_size`      | 批量大小           |
| `embedding_timeout_seconds` | 调用超时           |

### 17.4 检索配置

| 参数                | 说明                   |
| ------------------- | ---------------------- |
| `top_k`             | 向量召回数量           |
| `score_threshold`   | 相似度阈值             |
| `qdrant_collection` | Qdrant collection 名称 |

### 17.5 Rerank 配置

| 参数                     | 说明            |
| ------------------------ | --------------- |
| `rerank_enabled`         | 是否启用 Rerank |
| `rerank_top_n`           | 重排后保留数量  |
| `rerank_score_threshold` | Rerank 阈值     |
| `rerank_timeout_seconds` | 调用超时        |

### 17.6 LLM 配置

| 参数                  | 说明           |
| --------------------- | -------------- |
| `llm_model`           | 默认 LLM 模型  |
| `temperature`         | 生成随机性     |
| `max_output_tokens`   | 最大输出 token |
| `llm_timeout_seconds` | 调用超时       |
| `prompt_version`      | Prompt 版本    |

------

## 18. 可观测性要求

RAG 核心链路应记录以下信息：

| 阶段     | 记录内容                                            |
| -------- | --------------------------------------------------- |
| 文档入库 | 文档 ID、chunk 数量、Embedding 模型、失败原因、耗时 |
| 检索     | query、top_k、score_threshold、召回结果、耗时       |
| Rerank   | 输入候选数、输出结果、是否降级、耗时                |
| Prompt   | prompt_version、上下文数量、上下文长度              |
| LLM      | 模型名称、输入输出 token、耗时、异常                |
| 引用     | citation 数量、chunk_id、document_id                |
| 问答     | qa_record_id、status、latency_ms、trace_id          |

记录原则：

1. 结构化日志用于本地排查。
2. Langfuse 用于完整链路追踪。
3. PostgreSQL 只保存业务结果和必要关联 ID。
4. 不在日志和 Trace 中记录密钥。
5. 对敏感内容保留后续脱敏扩展点。

------

## 19. 测试要求

第一版 RAG 核心链路至少需要覆盖以下测试：

| 测试类型        | 测试内容                                |
| --------------- | --------------------------------------- |
| 文档解析测试    | 支持格式、空文档、解析失败              |
| 文本切分测试    | chunk 数量、顺序、重叠、来源信息        |
| Embedding 测试  | 批量调用、失败处理、状态更新            |
| Qdrant 写入测试 | point ID、payload、知识库过滤字段       |
| 检索测试        | top_k、score_threshold、无结果          |
| Rerank 测试     | 排序、过滤、异常降级                    |
| Prompt 测试     | 上下文编号、拒答约束、版本记录          |
| QA 流程测试     | 成功回答、拒答、模型异常                |
| 引用测试        | 引用来自 selected context，快照保存     |
| 删除一致性测试  | 文档删除后 chunk 和 Qdrant point 被清理 |

外部模型、Qdrant 和 Langfuse 应支持 mock 或测试替身，避免测试强依赖真实外部服务。

------

## 20. 第一版实现范围

第一版必须实现：

1. 文档解析、清洗和切分。
2. chunk 保存到 PostgreSQL。
3. chunk 向量写入 Qdrant。
4. 按 `knowledge_base_id` 过滤检索。
5. 基础语义检索接口。
6. 基础 RAG 问答流程。
7. 可选 Rerank 和异常降级。
8. Prompt 模板集中管理。
9. 无依据时拒答。
10. 回答引用保存和返回。
11. 问答记录保存。
12. `request_id` 和 `trace_id` 关联。
13. 文档重新处理和删除时清理旧 chunk 与 Qdrant point。

第一版暂不实现：

1. 多模态文档解析。
2. 知识图谱增强检索。
3. 复杂混合检索。
4. Prompt 在线管理后台。
5. 模型配置管理后台。
6. 大规模异步任务队列。
7. 高级 Agentic RAG 决策逻辑。
8. 自动化评分细节。

------

## 21. RAG 核心链路总结

ForgeRAG 第一版 RAG 核心链路设计重点是：

1. 文档入库必须形成 PostgreSQL chunk 与 Qdrant point 的稳定关联。
2. 检索必须限定知识库范围，避免跨知识库误召回。
3. Rerank 是增强能力，异常时允许降级。
4. Prompt 必须约束模型基于上下文回答。
5. 无可靠依据时应拒答，而不是强行生成。
6. 引用必须来自最终进入 Prompt 的上下文。
7. 历史引用依靠 `qa_citations` 快照保存。
8. 核心链路必须记录 `request_id` 和 `trace_id`。
9. 配置参数必须集中管理，避免硬编码。
10. 第一版优先保证链路可运行、可测试、可观测、可复现。