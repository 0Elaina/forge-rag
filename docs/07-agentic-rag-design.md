# ForgeRAG Agentic RAG 设计

## 1. 文档目的

本文档用于定义 ForgeRAG 第一版 Agentic RAG 流程设计，承接已有需求、架构、数据库、API 和 RAG 核心链路设计。

本文档重点说明：

1. Agentic RAG 的状态模型如何设计。
2. LangGraph 节点如何划分。
3. 节点之间如何根据条件路由。
4. 如何判断是否检索、是否改写问题、是否二次检索、是否拒答。
5. Agentic RAG 如何与基础 RAG、数据库记录和 Trace 关联。

本文档不重复展开文档解析、chunk 切分、Embedding、Qdrant 检索、Rerank、Prompt 模板和 API 字段细节。

------

## 2. 设计边界

### 2.1 覆盖范围

本文档覆盖 Agentic RAG 问答流程：

```text
接收问题
  → 分析问题
  → 判断是否需要检索
  → 改写检索问题
  → 检索与重排
  → 判断是否需要二次检索
  → 判断上下文是否足够
  → 生成回答或拒答
  → 保存执行记录
```

### 2.2 不覆盖范围

第一版不设计以下内容：

1. 多 Agent 协作。
2. 工具调用市场。
3. 长期记忆系统。
4. 多轮澄清对话。
5. 复杂规划型 Agent。
6. 自动网页搜索。
7. 人工审核流。
8. Agent 可视化编排平台。

------

## 3. 总体流程

第一版 Agentic RAG 使用 LangGraph 表达状态流转。

推荐流程：

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

设计原则：

1. 每个节点只负责一个明确动作。
2. 条件判断通过状态字段完成。
3. 检索、Rerank、Prompt、LLM 调用复用 `06-rag-core-design.md` 中的基础能力。
4. Agentic RAG 是增强入口，不替代基础 RAG。
5. 第一版优先保证流程可运行、可追踪、可测试。

------

## 4. 状态模型设计

### 4.1 AgentState

Agentic RAG 的核心状态对象建议定义为：

```text
AgentState
  ├── request_id
  ├── trace_id
  ├── agent_run_id
  ├── qa_record_id
  ├── knowledge_base_id
  ├── original_question
  ├── current_question
  ├── rewritten_question
  ├── need_retrieval
  ├── retrieval_results
  ├── reranked_results
  ├── selected_context
  ├── need_second_retrieval
  ├── actual_iterations
  ├── max_iterations
  ├── context_enough
  ├── answer
  ├── citations
  ├── refuse_reason
  ├── error_message
  └── status
```

### 4.2 状态字段说明

| 字段                    | 说明                                         |
| ----------------------- | -------------------------------------------- |
| `original_question`     | 用户原始问题                                 |
| `current_question`      | 当前节点使用的问题                           |
| `rewritten_question`    | 改写后的检索问题                             |
| `need_retrieval`        | 是否需要知识库检索                           |
| `retrieval_results`     | 原始召回结果                                 |
| `reranked_results`      | 重排后的结果                                 |
| `selected_context`      | 最终用于回答的上下文                         |
| `need_second_retrieval` | 是否需要二次检索                             |
| `actual_iterations`     | 实际检索轮次                                 |
| `max_iterations`        | 最大检索轮次                                 |
| `context_enough`        | 上下文是否足够回答                           |
| `answer`                | 最终回答                                     |
| `citations`             | 引用来源                                     |
| `refuse_reason`         | 拒答原因                                     |
| `status`                | `running` / `success` / `refused` / `failed` |

------

## 5. 节点设计

### 5.1 节点总览

| 节点              | 职责                       |
| ----------------- | -------------------------- |
| `AnalyzeQuestion` | 分析问题类型和是否需要检索 |
| `RewriteQuery`    | 改写或优化检索问题         |
| `Retrieve`        | 调用基础检索能力           |
| `Rerank`          | 调用重排能力               |
| `CheckRetrieval`  | 判断是否需要二次检索       |
| `CheckContext`    | 判断上下文是否足以支持回答 |
| `GenerateAnswer`  | 基于上下文生成带引用回答   |
| `DirectAnswer`    | 对无需检索的问题直接回答   |
| `RefuseAnswer`    | 在依据不足时拒答           |
| `HandleError`     | 处理流程异常               |

------

## 6. AnalyzeQuestion 节点

### 6.1 节点职责

`AnalyzeQuestion` 负责判断用户问题是否需要知识库支持。

输入：

```text
original_question
knowledge_base_id
```

输出：

```text
need_retrieval
question_type
decision
```

### 6.2 判断规则

第一版建议使用简单规则或轻量 LLM 判断：

| 情况                                   | 处理                 |
| -------------------------------------- | -------------------- |
| 问题与企业知识库、文档、项目资料相关   | 需要检索             |
| 问题明显是寒暄、格式说明或系统能力询问 | 可不检索             |
| 问题不完整但可能与知识库相关           | 需要检索，并进入改写 |
| 问题涉及知识库事实但缺少上下文         | 需要检索             |

### 6.3 节点输出示例

```json
{
  "need_retrieval": true,
  "question_type": "knowledge_question",
  "decision": "need_retrieval"
}
```

------

## 7. RewriteQuery 节点

### 7.1 节点职责

`RewriteQuery` 负责将用户问题改写为更适合检索的查询语句。

输入：

```text
original_question
current_question
retrieval_results
actual_iterations
```

输出：

```text
rewritten_question
current_question
decision
```

### 7.2 改写触发条件

以下情况进入问题改写：

1. 原问题表达过短。
2. 原问题包含代词或上下文不清晰。
3. 第一次检索结果为空。
4. 第一次检索得分过低。
5. 问题包含多个意图，需要提炼主要检索意图。

### 7.3 改写约束

1. 不改变用户原始意图。
2. 不引入知识库中未出现的新事实。
3. 改写结果应适合作为检索 query。
4. 改写结果需要写入状态，必要时写入 `qa_records.rewritten_question`。

------

## 8. Retrieve 节点

### 8.1 节点职责

`Retrieve` 负责调用基础检索能力，从指定知识库召回候选 chunk。

输入：

```text
knowledge_base_id
current_question
retrieval_config
```

输出：

```text
retrieval_results
actual_iterations
decision
```

### 8.2 处理规则

1. 必须限定 `knowledge_base_id`。
2. 每执行一次检索，`actual_iterations` 加一。
3. 检索结果为空不视为系统异常。
4. Qdrant 或 Embedding 服务异常才视为外部依赖异常。
5. 检索过程应记录到 Trace。

------

## 9. Rerank 节点

### 9.1 节点职责

`Rerank` 负责对召回结果进行重排，并生成候选上下文。

输入：

```text
current_question
retrieval_results
rerank_config
```

输出：

```text
reranked_results
selected_context
decision
```

### 9.2 降级规则

1. 如果未启用 Rerank，直接使用检索排序。
2. 如果 Rerank 服务异常，降级为原始检索排序。
3. 降级不应直接导致 Agentic RAG 失败。
4. 是否降级需要写入节点记录和 Trace。

------

## 10. CheckRetrieval 节点

### 10.1 节点职责

`CheckRetrieval` 判断是否需要二次检索。

输入：

```text
retrieval_results
reranked_results
actual_iterations
max_iterations
```

输出：

```text
need_second_retrieval
decision
```

### 10.2 二次检索条件

满足以下条件之一时，可以触发二次检索：

1. 检索结果为空。
2. 最高检索得分低于阈值。
3. Rerank 后有效结果数量不足。
4. 检索结果与问题明显不相关。
5. 当前检索轮次未达到 `max_iterations`。

### 10.3 禁止继续检索条件

以下情况不得继续检索：

1. `actual_iterations >= max_iterations`。
2. 已经连续两次检索为空。
3. 问题本身超出知识库范围。
4. 外部依赖异常导致无法继续检索。

------

## 11. CheckContext 节点

### 11.1 节点职责

`CheckContext` 判断当前上下文是否足以支持回答。

输入：

```text
current_question
selected_context
reranked_results
```

输出：

```text
context_enough
decision
refuse_reason
```

### 11.2 判断规则

第一版采用可配置规则判断：

| 条件                      | 结果 |
| ------------------------- | ---- |
| `selected_context` 为空   | 不足 |
| 最高相关性得分低于阈值    | 不足 |
| 有效 chunk 数量少于最小值 | 不足 |
| 上下文只包含无关内容      | 不足 |
| 上下文可以直接支撑答案    | 足够 |

### 11.3 拒答原因

常见拒答原因：

```text
knowledge_not_found
context_not_enough
retrieval_empty
retrieval_score_too_low
out_of_scope
```

------

## 12. GenerateAnswer 节点

### 12.1 节点职责

`GenerateAnswer` 负责调用基础 RAG 生成能力，生成带引用回答。

输入：

```text
original_question
current_question
selected_context
model_config
prompt_version
```

输出：

```text
answer
citations
qa_record_id
status
```

### 12.2 处理要求

1. 回答必须基于 `selected_context`。
2. 引用必须来自最终进入 Prompt 的上下文。
3. 生成成功后写入 `qa_records`。
4. 引用快照写入 `qa_citations`。
5. `qa_mode` 设置为 `agentic_rag`。
6. `qa_record_id` 回写到 AgentState。

------

## 13. DirectAnswer 节点

### 13.1 节点职责

`DirectAnswer` 用于处理不需要知识库检索的问题。

适用场景：

1. 简单寒暄。
2. 对系统能力的简单说明。
3. 与知识库事实无关的格式类问题。

### 13.2 约束

1. 不得对企业知识库事实进行无依据回答。
2. 对可能涉及知识库事实的问题，应优先进入检索流程。
3. Direct Answer 也需要保存问答记录。
4. 如果无法判断是否需要检索，应默认检索。

------

## 14. RefuseAnswer 节点

### 14.1 节点职责

`RefuseAnswer` 在知识依据不足时返回拒答结果。

输入：

```text
refuse_reason
selected_context
trace_id
```

输出：

```text
status = refused
answer = null
citations = []
```

### 14.2 拒答策略

拒答文案应清晰、克制：

```text
知识库中没有足够依据回答该问题。
```

可附加建议：

```text
请补充更具体的问题，或上传相关文档后重试。
```

### 14.3 保存要求

1. `qa_records.status` 写入 `refused`。
2. `agent_runs.status` 写入 `refused`。
3. `refuse_reason` 写入业务表。
4. 低质量候选上下文可只记录到 Trace，不写入引用表。

------

## 15. 条件边设计

### 15.1 路由规则总览

| 起点              | 条件                     | 下一节点         |
| ----------------- | ------------------------ | ---------------- |
| `AnalyzeQuestion` | `need_retrieval = false` | `DirectAnswer`   |
| `AnalyzeQuestion` | `need_retrieval = true`  | `RewriteQuery`   |
| `RewriteQuery`    | 改写完成                 | `Retrieve`       |
| `Retrieve`        | 检索完成                 | `Rerank`         |
| `Rerank`          | 重排完成                 | `CheckRetrieval` |
| `CheckRetrieval`  | 需要二次检索且未达上限   | `RewriteQuery`   |
| `CheckRetrieval`  | 不需要二次检索           | `CheckContext`   |
| `CheckContext`    | `context_enough = true`  | `GenerateAnswer` |
| `CheckContext`    | `context_enough = false` | `RefuseAnswer`   |
| 任意节点          | 未恢复异常               | `HandleError`    |

### 15.2 默认路由原则

1. 不确定是否需要检索时，默认检索。
2. 不确定上下文是否足够时，默认拒答。
3. 不确定是否继续二次检索时，优先检查最大次数。
4. 外部依赖异常不进入二次检索死循环。

------

## 16. 循环控制

### 16.1 最大轮次

第一版默认：

```text
max_iterations = 2
```

含义：

1. 第一次检索为基础检索。
2. 第二次检索为补救检索。
3. 超过上限后不得继续改写和检索。

### 16.2 循环终止条件

任一条件满足即终止循环：

1. `context_enough = true`。
2. `actual_iterations >= max_iterations`。
3. 连续检索无结果。
4. 出现不可恢复异常。
5. 判断问题超出知识库范围。

------

## 17. 数据库存储映射

### 17.1 agent_runs

`agent_runs` 保存一次 Agentic RAG 执行摘要。

写入时机：

1. Agentic RAG 开始时创建记录。
2. 执行中状态为 `running`。
3. 成功、拒答或失败后更新最终状态。
4. 最终状态快照写入 `state_snapshot`。

保存内容：

```text
agent_run_id
qa_record_id
knowledge_base_id
original_question
final_question
final_answer
status
refuse_reason
error_message
max_iterations
actual_iterations
graph_version
state_snapshot
request_id
trace_id
latency_ms
```

### 17.2 agent_steps

`agent_steps` 保存关键节点摘要。

每个节点至少记录：

```text
agent_run_id
step_name
step_order
input_summary
output_summary
decision
next_step
status
error_message
latency_ms
trace_id
span_id
```

要求：

1. 只保存摘要，不保存完整 Prompt 和完整上下文。
2. 完整节点细节交给 Langfuse Trace。
3. `agent_steps` 是高增长明细，后续清理时随 `agent_runs` 物理删除。

### 17.3 qa_records 与 qa_citations

生成回答或拒答后，应写入问答记录：

1. `qa_mode = agentic_rag`。
2. `rewritten_question` 保存最终检索问题。
3. 成功回答写入 `answer`。
4. 拒答写入 `refuse_reason`。
5. 成功回答的引用写入 `qa_citations`。
6. `trace_id` 与 `request_id` 用于关联观测数据。

------

## 18. 可观测性要求

Agentic RAG 的可观测性重点是记录状态流转和决策依据。

### 18.1 必须记录的内容

| 阶段         | 记录内容                                 |
| ------------ | ---------------------------------------- |
| 请求入口     | `request_id`、`trace_id`、`agent_run_id` |
| 问题分析     | 问题类型、是否需要检索                   |
| 问题改写     | 原问题、改写问题、改写原因               |
| 检索         | query、top_k、召回数量、最高得分         |
| Rerank       | 候选数量、保留数量、是否降级             |
| 二次检索判断 | 是否继续检索、当前轮次、最大轮次         |
| 上下文判断   | 是否足够、拒答原因                       |
| 生成回答     | 模型名称、Prompt 版本、Token、耗时       |
| 结束状态     | `success` / `refused` / `failed`         |

### 18.2 Langfuse 降级

如果 Langfuse 不可用：

1. Agentic RAG 主流程应尽量继续。
2. `trace_id` 可以为空。
3. 节点摘要仍应写入 `agent_steps`。
4. 结构化日志应记录观测组件异常。
5. 不应因观测异常直接导致普通问答失败。

------

## 19. 异常处理

### 19.1 节点异常处理

| 异常位置               | 处理方式             |
| ---------------------- | -------------------- |
| `AnalyzeQuestion` 失败 | 默认进入检索流程     |
| `RewriteQuery` 失败    | 使用原问题检索       |
| `Retrieve` 失败        | 返回外部依赖错误     |
| `Rerank` 失败          | 降级使用原始检索排序 |
| `CheckContext` 失败    | 默认拒答             |
| `GenerateAnswer` 失败  | 标记为 `failed`      |
| `RefuseAnswer` 失败    | 标记为 `failed`      |

### 19.2 状态一致性

异常发生时必须保证：

1. `agent_runs.status` 最终不应停留在 `running`。
2. 已执行节点应写入 `agent_steps`。
3. 如果生成了问答记录，应关联 `qa_record_id`。
4. 未生成回答时，应保存 `error_message`。
5. API 层返回统一错误结构。

------

## 20. 配置项设计

第一版 Agentic RAG 配置项：

| 配置项                     | 说明               |
| -------------------------- | ------------------ |
| `agent_graph_version`      | 图版本             |
| `max_iterations`           | 最大检索轮次       |
| `enable_query_rewrite`     | 是否启用问题改写   |
| `enable_direct_answer`     | 是否允许直接回答   |
| `min_retrieval_score`      | 最低检索得分       |
| `min_context_chunks`       | 最少有效上下文数量 |
| `context_enough_threshold` | 上下文充分性阈值   |
| `llm_model`                | 默认 LLM           |
| `prompt_version`           | Prompt 版本        |
| `node_timeout_seconds`     | 单节点超时时间     |

配置要求：

1. 默认值由配置文件管理。
2. 接口可覆盖部分参数，例如 `max_iterations`。
3. 不在节点代码中硬编码模型名称和阈值。
4. 评测任务运行 Agentic RAG 时，应保存关键配置快照。

------

## 21. 测试要求

第一版至少覆盖以下测试：

| 测试类型     | 测试内容                                 |
| ------------ | ---------------------------------------- |
| 状态模型测试 | AgentState 初始化、字段更新              |
| 路由测试     | 是否检索、是否二次检索、是否拒答         |
| 节点测试     | 每个节点输入输出是否符合预期             |
| 循环控制测试 | 超过 `max_iterations` 后终止             |
| 降级测试     | Rerank 失败后继续生成                    |
| 拒答测试     | 无上下文时返回 refused                   |
| 异常测试     | 节点异常后状态不残留 running             |
| 存储测试     | `agent_runs` 和 `agent_steps` 正确写入   |
| 观测测试     | `request_id`、`trace_id`、节点耗时可关联 |
| 集成测试     | 完整 Agentic RAG 成功路径和拒答路径      |

外部模型、Qdrant、Langfuse 应支持 mock 或测试替身。

------

## 22. 第一版实现范围

第一版必须实现：

1. LangGraph 基础状态图。
2. AgentState 状态对象。
3. 问题分析节点。
4. 问题改写节点。
5. 检索节点。
6. Rerank 节点及降级。
7. 二次检索判断。
8. 上下文充分性判断。
9. 回答生成节点。
10. 拒答节点。
11. 最大循环次数限制。
12. `agent_runs` 执行摘要保存。
13. `agent_steps` 节点摘要保存。
14. `qa_records` 与 `qa_citations` 关联。
15. `request_id` 和 `trace_id` 关联。
16. 成功路径、拒答路径和异常路径测试。

第一版暂不实现：

1. 多 Agent 协作。
2. 复杂任务规划。
3. 人工确认节点。
4. 长期记忆。
5. 工具调用市场。
6. 多轮澄清。
7. Agent 可视化编排。
8. 自动网页搜索。
9. 复杂自反思循环。

------

## 23. 设计总结

ForgeRAG 第一版 Agentic RAG 的核心设计目标是：在基础 RAG 之上增加有限、清晰、可控的流程决策能力。

设计重点如下：

1. 用 LangGraph 表达状态流转。
2. 用 AgentState 统一传递中间结果。
3. 用节点拆分问题分析、改写、检索、重排、判断、生成和拒答。
4. 用条件边控制是否检索、是否二次检索、是否生成或拒答。
5. 用 `max_iterations` 防止循环失控。
6. 用 `agent_runs` 保存流程摘要。
7. 用 `agent_steps` 保存节点摘要。
8. 用 `qa_records` 和 `qa_citations` 保存最终问答结果。
9. 用 `trace_id` 关联 Langfuse 和结构化日志。
10. 第一版保持流程简单可运行，后续再扩展更复杂的 Agent 能力。