# price_compare_desktop 架构设计（arch.md）

## 1. 文档目标

本文档基于 [spec.md](/i:/biaoshu/price_compare/spec.md) ，补充 V1/MVP 可执行的代码架构设计，重点回答以下问题：

- 项目如何分层，模块边界怎么划分
- 一条物料从导入到比价完成的调用链是什么
- UI 线程、后台线程、Provider 调用如何解耦
- 缓存、AI、成本控制放在哪一层
- 第一版代码目录应该如何组织

本文档默认面向 Python Windows 桌面应用实现。

---

## 2. 架构原则

### 2.1 核心原则

1. UI 只负责展示和交互，不直接写业务逻辑。
2. 应用服务负责编排流程，不直接依赖具体 UI 控件。
3. Provider 统一接口，平台差异收敛在 Provider 内部。
4. AI 只做增强，不作为唯一判定来源。
5. 所有中间结果可追踪、可缓存、可复核。
6. 后台任务不直接更新 UI，只通过事件总线/消息对象回传。
7. 本地优先，所有配置、缓存、导出都可离线落盘。

### 2.2 V1 技术取舍

- GUI：建议直接使用 `PySide6`
- 原因：V1 虽然用 `CustomTkinter` 更快，但本项目核心是“批量表格 + 状态更新 + 详情面板 + 后台任务反馈”，Qt 的模型视图结构更稳，后续扩展成本更低。
- 保守方案：如果要极快验证 MVP，也可以先做 `CustomTkinter`，但应用层接口不变，UI 作为可替换适配层。

结论：架构设计按“UI 可替换”写，但推荐首版代码落在 `PySide6`。

---

## 3. 总体分层

```text
┌──────────────────────────────────────────────┐
│ UI Layer                                     │
│ MainWindow / ImportPanel / ResultTable       │
│ TaskPanel / DetailPanel / SettingsDialog     │
└──────────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────┐
│ Application Layer                            │
│ ImportAppService / SearchTaskService         │
│ CompareAppService / ExportAppService         │
│ SettingsAppService / CostGuardService        │
└──────────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────┐
│ Domain Layer                                 │
│ Entities / Value Objects / Policies          │
│ MaterialItem / SearchQuery / ProductOffer    │
│ CompareResult / ScoreDetail / TaskEvent      │
└──────────────────────────────────────────────┘
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
┌──────────────┐ ┌──────────────┐ ┌────────────────┐
│ Providers    │ │ AI Gateway   │ │ Repositories   │
│ JD / Taobao  │ │ DeepSeek     │ │ Cache / Config │
└──────────────┘ └──────────────┘ └────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────┐
│ Infrastructure Layer                         │
│ httpx / sqlite3 / pandas / openpyxl / loguru │
└──────────────────────────────────────────────┘
```

---

## 4. 模块职责

### 4.1 UI 层

职责：

- 文件选择、按钮点击、任务状态展示
- 结果表格渲染
- 展示单条物料候选详情和 AI 解释
- 响应后台事件并更新界面

禁止：

- 直接发 HTTP 请求
- 直接访问 SQLite
- 直接拼 Provider 参数
- 在控件回调里写完整搜索流程

建议组件：

- `MainWindow`：总布局和页面协调
- `ToolbarWidget`：导入、开始、停止、导出、设置
- `TaskPanel`：预算、Provider 开关、AI 开关、进度
- `ResultTableView`：主结果表
- `CandidateDetailPanel`：当前行候选详情
- `LogPanel`：可选日志视图

### 4.2 应用层

职责：

- 编排业务流程
- 调用领域服务、Provider、缓存、AI
- 产出面向 UI 的事件和 DTO
- 控制任务生命周期

核心服务：

- `ImportAppService`：导入 Excel，生成 `MaterialItem`
- `SearchTaskService`：批量任务调度、暂停/取消、进度回传
- `QueryBuilderService`：生成规则关键词，必要时调用 AI 优化
- `CompareAppService`：整合多平台候选、打分、选优、解释
- `ExportAppService`：生成导出 DataFrame 和 Excel
- `CostGuardService`：预算判断、调用统计、策略裁剪
- `SettingsAppService`：读取和保存本地配置

### 4.3 领域层

职责：

- 定义核心模型和业务规则
- 不关心 UI、不关心具体数据库、不关心具体第三方 API

建议对象：

- 实体：`MaterialItem`、`CompareResult`
- 值对象：`SearchQuery`、`ProductOffer`、`ScoreDetail`
- 枚举：`TaskStatus`、`PlatformType`、`CacheType`、`AiTaskType`
- 策略：`ProviderPolicy`、`RetryPolicy`、`BudgetPolicy`

### 4.4 Provider 层

职责：

- 平台签名、参数适配、响应解析、字段标准化
- 不负责最终比价决策

统一接口：

```python
class SearchProvider(Protocol):
    provider_name: str
    provider_version: str
    platform: PlatformType

    def search(self, query: SearchQuery) -> list[ProductOffer]:
        ...
```

扩展原则：

- 新平台只新增文件，不改主流程
- 第三方淘宝供应商替换时，仅替换 Provider 实现和配置

### 4.5 基础设施层

职责：

- 封装 HTTP、SQLite、Excel 读写、日志、时间、配置
- 提供稳定的技术能力，不承载业务规则

---

## 5. 推荐目录结构

```text
price_compare/
├─ app.py
├─ spec.md
├─ arch.md
├─ requirements.txt
├─ README.md
├─ config/
│  ├─ settings.py
│  ├─ provider_config.py
│  ├─ prompts.py
│  └─ app_paths.py
├─ ui/
│  ├─ main_window.py
│  ├─ widgets/
│  │  ├─ toolbar_widget.py
│  │  ├─ task_panel.py
│  │  ├─ result_table.py
│  │  ├─ detail_panel.py
│  │  └─ log_panel.py
│  ├─ dialogs/
│  │  └─ settings_dialog.py
│  ├─ viewmodels/
│  │  ├─ result_row_vm.py
│  │  └─ task_state_vm.py
│  └─ mappers/
│     └─ ui_mapper.py
├─ application/
│  ├─ dto.py
│  ├─ events.py
│  ├─ import_app_service.py
│  ├─ search_task_service.py
│  ├─ compare_app_service.py
│  ├─ export_app_service.py
│  ├─ settings_app_service.py
│  └─ cost_guard_service.py
├─ domain/
│  ├─ models.py
│  ├─ enums.py
│  ├─ policies.py
│  └─ scoring.py
├─ providers/
│  ├─ base.py
│  ├─ jd_provider.py
│  ├─ taobao_provider.py
│  ├─ pdd_provider.py
│  └─ web_fallback_provider.py
├─ repositories/
│  ├─ cache_repository.py
│  ├─ task_repository.py
│  └─ settings_repository.py
├─ infra/
│  ├─ http_client.py
│  ├─ sqlite_db.py
│  ├─ excel_reader.py
│  ├─ excel_writer.py
│  ├─ deepseek_client.py
│  ├─ clock.py
│  └─ logger.py
├─ workers/
│  ├─ task_bus.py
│  ├─ task_runner.py
│  ├─ rate_limiter.py
│  └─ retry.py
├─ utils/
│  ├─ text_cleaner.py
│  ├─ price_parser.py
│  ├─ similarity.py
│  ├─ hash_utils.py
│  └─ dataframe_utils.py
├─ data/
│  ├─ cache.db
│  ├─ logs/
│  └─ exports/
└─ tests/
   ├─ unit/
   ├─ integration/
   └─ fixtures/
```

与 `spec.md` 相比，这里新增了 `application/`、`repositories/`、`workers/`，目的是把“流程编排”“存储抽象”“线程与任务机制”明确拆开，避免后面 UI 和服务层耦合。

---

## 6. 关键调用链

### 6.1 Excel 导入链路

```text
UI: 点击导入
  -> ImportAppService.import_file(path)
  -> infra.excel_reader.read_first_sheet()
  -> 表头识别 / 字段映射
  -> MaterialItem 列表
  -> DTO 映射为表格预览数据
  -> UI 展示预览
```

### 6.2 单条物料搜索链路

```text
SearchTaskService.process_item(material)
  -> QueryBuilderService.build(material)
  -> 可选 AI 优化查询
  -> CostGuardService.decide_providers(material, query)
  -> 逐个 Provider 查询
      -> 先查 cache_repository
      -> 未命中则调用 provider.search()
      -> 结果标准化并写缓存
  -> CompareAppService.rank_candidates()
  -> 可选 AI 解释
  -> 生成 CompareResult
  -> 发布 TaskEvent(item_finished)
```

### 6.3 批量任务链路

```text
UI: 点击开始搜索
  -> SearchTaskService.start_batch(items, options)
  -> TaskRunner 提交线程池
  -> Worker 逐条处理
  -> TaskBus 持续发出进度/结果/错误事件
  -> UI 主线程消费事件并刷新表格
  -> 全部完成
  -> UI 允许导出
```

### 6.4 导出链路

```text
UI: 点击导出
  -> ExportAppService.export(results, target_path)
  -> pandas 生成结果 DataFrame
  -> openpyxl 写样式、高亮、备注、冻结窗格
  -> 输出 xlsx
```

---

## 7. 线程模型与任务机制

### 7.1 线程约束

- UI 主线程：只做交互和界面刷新
- 工作线程：执行搜索、AI、缓存读写、导出
- 禁止工作线程直接操作 UI 控件

### 7.2 推荐实现

- `ThreadPoolExecutor(max_workers=4)` 处理物料任务
- 每个平台增加轻量限流器，避免高并发打爆 API
- 用 `TaskBus` 作为线程间消息通道

### 7.3 事件模型

建议定义统一事件：

```python
@dataclass
class TaskEvent:
    event_type: str
    task_id: str
    material_id: int | None = None
    payload: dict | None = None
    error: str | None = None
```

事件类型建议：

- `batch_started`
- `item_started`
- `item_progress`
- `item_finished`
- `item_failed`
- `budget_warning`
- `batch_finished`
- `log`

### 7.4 取消与停止

V1 不建议做真正的线程强杀。

采用方式：

- `CancellationToken` 共享取消标记
- 每条物料开始前检查
- Provider 调用前检查
- AI 调用前检查
- 正在执行的 HTTP 请求允许自然结束

这样实现简单，也更稳定。

---

## 8. 数据模型建议

### 8.1 领域模型补充

除了 `spec.md` 里的 4 个核心对象，建议再补以下模型：

```python
@dataclass
class ScoreDetail:
    brand_score: float
    spec_score: float
    title_score: float
    category_score: float
    unit_score: float
    price_penalty: float
    final_score: float
```

```python
@dataclass
class CandidateBundle:
    material_id: int
    offers_by_platform: dict[str, list[ProductOffer]]
```

```python
@dataclass
class BatchSearchOptions:
    enable_ai: bool
    enabled_platforms: list[str]
    top_n: int
    max_budget: float | None
    retry_enabled: bool
```

### 8.2 结果模型建议

`CompareResult` 最好保留更多可解释字段，不要只留下最终价格：

```python
@dataclass
class CompareResult:
    material_id: int
    best_platform: str | None
    best_price: float | None
    jd_price: float | None
    taobao_price: float | None
    pdd_price: float | None
    price_diff: float | None
    match_score: float | None
    match_level: str | None
    ai_comment: str | None
    top_offers: list[ProductOffer]
    score_detail: ScoreDetail | None
    search_status: str
    error_message: str | None = None
```

原因：

- UI 详情面板需要候选列表
- 导出表需要解释字段
- 排查问题时需要知道是“没搜到”还是“搜到但分低”

---

## 9. 缓存与数据库设计

### 9.1 SQLite 角色

SQLite 在 V1 负责三类数据：

- 搜索缓存
- AI 缓存
- 本地任务记录/日志摘要（可选）

### 9.2 建议表结构

#### `search_cache`

```sql
CREATE TABLE search_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_key TEXT NOT NULL UNIQUE,
    platform TEXT NOT NULL,
    provider_name TEXT NOT NULL,
    provider_version TEXT NOT NULL,
    query_text TEXT NOT NULL,
    normalized_query TEXT NOT NULL,
    response_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    hit_count INTEGER NOT NULL DEFAULT 0
);
```

#### `ai_cache`

```sql
CREATE TABLE ai_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_key TEXT NOT NULL UNIQUE,
    task_type TEXT NOT NULL,
    input_text TEXT NOT NULL,
    output_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
```

#### `task_run`（建议增加）

```sql
CREATE TABLE task_run (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL UNIQUE,
    file_path TEXT NOT NULL,
    total_count INTEGER NOT NULL,
    success_count INTEGER NOT NULL DEFAULT 0,
    failed_count INTEGER NOT NULL DEFAULT 0,
    cache_hit_count INTEGER NOT NULL DEFAULT 0,
    api_call_count INTEGER NOT NULL DEFAULT 0,
    estimated_cost REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    finished_at TEXT
);
```

### 9.3 TTL 建议

- 搜索结果：`1~3 天`
- AI 查询优化：`7 天`
- AI 规格抽取：`30 天`

### 9.4 缓存实现原则

- 缓存 key 必须包含 `platform + normalized_query + provider_version`
- Provider 升级后自然绕过旧缓存
- 命中缓存时仍需记录 `hit_count`

---

## 10. Provider 架构

### 10.1 抽象层次

```text
SearchTaskService
  -> SearchProvider
      -> ProviderRequestBuilder
      -> HttpClient
      -> ProviderResponseParser
      -> ProductOfferMapper
```

### 10.2 基类建议

```python
class BaseProvider(SearchProvider):
    def search(self, query: SearchQuery) -> list[ProductOffer]:
        request = self.build_request(query)
        response = self.http_client.send(request)
        payload = self.parse_response(response)
        return self.map_offers(payload)
```

子类只重写：

- `build_request`
- `parse_response`
- `map_offers`

### 10.3 错误分类

Provider 层抛出的错误建议统一成可识别异常：

- `ProviderTimeoutError`
- `ProviderRateLimitError`
- `ProviderAuthError`
- `ProviderPayloadError`
- `ProviderEmptyResultError`

这样应用层才能决定“重试 / 跳过 / AI 改写重搜”。

---

## 11. AI 集成设计

### 11.1 AI 服务职责

`AiService` 建议只暴露几个明确方法：

```python
class AiService:
    def normalize_material(self, material: MaterialItem) -> dict: ...
    def optimize_query(self, material: MaterialItem, base_query: SearchQuery) -> SearchQuery: ...
    def explain_match(self, material: MaterialItem, offer: ProductOffer) -> str: ...
```

### 11.2 AI 调用原则

- 先规则，后 AI
- 优先只对复杂项、高价值项、空结果项触发 AI
- AI 输出必须结构化，尽量要求 JSON
- AI 返回异常时直接降级，不阻断主流程

### 11.3 AI 触发时机

建议 V1 只在以下三种场景触发：

1. 物料文本过乱，规则提取失败
2. 首次搜索空结果
3. 最优候选需要生成解释文案

这能有效控制成本。

---

## 12. 候选打分设计

### 12.1 打分责任归属

打分逻辑应放在 `domain/scoring.py` 或 `CompareAppService` 内的纯函数模块中，不放在 Provider。

### 12.2 建议打分公式

```text
final_score =
  brand_score * 0.20 +
  spec_score * 0.30 +
  title_score * 0.20 +
  category_score * 0.10 +
  unit_score * 0.10 -
  price_penalty * 0.10
```

V1 先做可解释的规则分，不急着上学习模型。

### 12.3 排序策略

- 先过滤明显不相关项
- 再按 `final_score` 倒序
- 分数接近时优先价格更完整、平台优先级更高的结果
- 默认保留 Top 3

### 12.4 可疑项判定

以下场景标记为“需复核”：

- 品牌不一致但价格极低
- 规格缺失严重
- 单位不一致
- 标题虽相似但型号冲突
- 价格偏离投标单价过大

---

## 13. 成本控制设计

### 13.1 成本控制位置

不要把预算判断散在 Provider 内部。

统一由 `CostGuardService` 决定：

- 是否允许调用某平台
- 是否允许 AI 优化
- 是否在空结果后执行二次重搜

### 13.2 建议策略

```text
低价值 + 查询简单：
  JD only

中价值 + 查询普通：
  JD first, miss 后 Taobao

高价值 或 规格复杂：
  JD + Taobao

预算接近阈值：
  停止补搜，保底仅主平台
```

### 13.3 统计指标

V1 需要实时统计：

- 总调用次数
- 各平台调用次数
- AI 调用次数
- 缓存命中次数
- 预估成本

这些数据应直接展示在任务区。

---

## 14. UI 结构建议

### 14.1 主界面布局

```text
┌──────────────── 顶部工具栏 ────────────────┐
├──── 左侧任务区 ────┬──── 中央结果表 ─────┬── 右侧详情 ──┤
├──────────────────────────────────────────────────────────┤
│ 底部日志区（可折叠）                                      │
└──────────────────────────────────────────────────────────┘
```

### 14.2 结果表设计

表格建议列：

- 序号
- 名称
- 规格
- 数量
- 单位
- 品牌
- 投标单价
- 原采购价
- 京东价
- 淘宝价
- 推荐平台
- 推荐价
- 差价
- 置信度
- 状态

详情面板展示：

- Top N 候选商品
- 每个候选的得分拆解
- AI 解释
- 错误/重试记录

### 14.3 UI 更新方式

UI 不直接订阅底层服务，而是通过 ViewModel 或事件适配层接收：

- `TaskEvent -> UIMapper -> ResultRowViewModel -> TableModel`

这样后续换 UI 框架，应用层可以不动。

---

## 15. 配置设计

### 15.1 配置来源

优先级建议：

1. 本地配置文件
2. 环境变量
3. 代码默认值

### 15.2 配置项分类

- 应用配置：线程数、导出目录、日志级别
- Provider 配置：API Key、密钥、域名、超时、重试
- AI 配置：模型名、温度、超时、开关
- 预算配置：单批预算、平台启用、平台调用单价

### 15.3 文件建议

- `config/settings.py`：统一配置加载
- `data/config.json`：用户落盘配置
- `.env`：开发环境密钥

---

## 16. 日志与可观测性

### 16.1 日志分层

- 应用日志：任务开始、结束、取消、导出
- Provider 日志：请求摘要、耗时、错误、重试
- 缓存日志：命中、失效、写入
- AI 日志：触发原因、耗时、是否命中缓存

### 16.2 日志原则

- 不打印完整敏感密钥
- 不记录过大的原始响应全文
- 每条日志带 `task_id`
- 能定位到 `material_id`

---

## 17. 测试策略

### 17.1 单元测试优先

优先覆盖纯逻辑模块：

- `price_parser`
- `text_cleaner`
- `query_builder`
- `scoring`
- `cost_guard_service`
- `cache_repository`

### 17.2 集成测试

对以下模块做 mock 集成测试：

- Excel 导入链路
- JD Provider 解析
- Taobao Provider 解析
- 导出 Excel
- 批量任务事件流

### 17.3 不建议的测试方式

V1 不要依赖真实外部 API 做 CI 测试，否则成本和稳定性都差。

---

## 18. 开发顺序建议

### M1

- 搭目录
- 建领域模型
- 完成 Excel 导入
- 完成结果表展示

### M2

- 打通任务线程模型
- 实现 `JDOfficialProvider`
- 完成单平台搜索和展示

### M3

- 加 SQLite 缓存
- 加结果导出
- 加基础日志

### M4

- 加 AI 查询优化
- 加 AI 候选解释
- 加空结果重搜

### M5

- 加 `TaobaoThirdPartyProvider`
- 加成本统计
- 加预算控制

### M6

- 优化打分
- 增加详情面板
- 补齐错误处理和测试

---

## 19. V1 最小实现建议

如果目标是尽快做出可运行 MVP，建议先只做以下闭环：

1. 导入 Excel
2. 映射成 `MaterialItem`
3. 用规则生成搜索词
4. 只接一个 `JDOfficialProvider`
5. 做基础打分
6. 表格展示推荐价
7. 导出 Excel
8. 加本地缓存

AI、淘宝、预算控制都放在第二阶段接入。

这样风险最低，且最符合 `spec.md` 对“小步可运行版本”的要求。

---

## 20. 当前建议结论

V1 最合适的代码组织方式是：

- 采用分层架构，不把流程塞进 UI
- 以 `SearchTaskService` 作为任务编排核心
- 以 `SearchProvider` 作为平台扩展核心
- 以 `CompareAppService + scoring` 作为推荐决策核心
- 以 `TaskBus` 作为线程解耦核心
- 以 `SQLite + AI cache` 作为性能和成本控制基础

如果要马上开始编码，第一步应先落：

- 目录骨架
- 核心 dataclass / enum
- ImportAppService
- SearchTaskService 空实现
- JD Provider 接口骨架
- ResultTable UI 骨架

这套结构能直接支撑后续继续拆 `tasks.md`。
