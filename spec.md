# 电商自动搜索比价 Windows App 需求规格说明（spec.md）

## 1. 文档信息

- 项目代号：`price_compare_desktop`
- 文档名称：`spec.md`
- 文档目标：为后续使用 Codex / AI 编程工具实现本项目提供清晰、可执行、可拆解的需求说明
- 当前阶段：MVP / V1 规格文档
- 目标平台：Windows 桌面端（本地 EXE）
- 主要使用者：个人采购辅助 / 工程物料比价 / 批量 Excel 采购单分析

---

## 2. 项目背景

用户希望开发一个 Windows 桌面 App，用于对 Excel 中的商品/物料进行自动搜索、比价、记录和导出。

本项目场景不是普通消费品“随手搜最低价”，而更偏向：

- 工程物料 / 五金 / 电料 / 工具类采购辅助
- 批量 Excel 导入
- 自动搜索多个电商平台候选商品
- 对比价格
- 利用 AI 做商品名理解、规格归一、候选匹配、差异解释
- 输出可复核的比价结果表

当前已知条件：

- DeepSeek API Key 可用，计划用作 AI 能力
- 京东开发者权限可能可用，可作为首选官方数据源
- 淘宝可能通过第三方聚合 API（如万邦 / 聚鼎立等）接入
- 拼多多后续可扩展，不强依赖第一版上线

---

## 3. 产品目标

### 3.1 核心目标

开发一个 Windows 本地 EXE 工具，支持：

1. 导入 Excel 采购/物料清单
2. 自动解析每一行商品信息
3. 调用电商数据源搜索候选商品
4. 生成跨平台价格对比结果
5. 使用 AI 提升搜索词质量、规格理解和候选匹配精度
6. 导出新的 Excel 比价结果表

### 3.2 核心价值

本工具真正的价值不只是“搜到便宜货”，而是：

- 批量处理 Excel 清单
- 自动清洗混乱物料名称
- 理解品牌、规格、型号、单位
- 尽量少调用收费 API，但尽量搜准
- 给用户一个可人工复核的结果表

### 3.3 非目标（V1 暂不做）

以下内容不属于 V1 必做范围：

- 自动下单
- 登录用户电商账号
- 支付功能
- 云端多用户协作
- macOS / Linux 版本
- 手机端版本
- 完整商品监控系统（仅预留接口）
- 浏览器插件

---

## 4. 用户画像与使用场景

### 4.1 用户画像

- 有 Excel 采购单的人
- 需要批量比价的人
- 工程/物料/五金/工具采购辅助场景
- 对电商平台 API 和网页搜索不是特别熟悉，但希望一键完成比价

### 4.2 典型使用流程

#### 场景 A：批量采购单比价

1. 用户导入 Excel 文件
2. App 自动读取每一行物料
3. App 自动生成搜索关键词
4. App 调用京东 / 淘宝等数据源搜索
5. App 对候选结果进行排序和打分
6. App 展示比价结果表
7. 用户导出结果 Excel

#### 场景 B：高金额物料重点比价

1. 系统识别高单价物料
2. 优先执行多平台补搜
3. 对低金额物料仅执行主平台搜索
4. 控制整体 API 成本

#### 场景 C：规格复杂商品匹配

1. 一条物料名称描述不规范
2. App 先调用 AI 进行规格拆分与归一
3. AI 生成更适合搜索的关键词
4. 搜索返回多个候选商品
5. AI / 规则引擎判断哪一个更像同款

---

## 5. 功能范围（V1）

### 5.1 Excel 导入

支持导入 `.xlsx` 文件。

V1 要求：

- 用户选择本地 Excel 文件
- 读取首个工作表（后续可扩展为选择工作表）
- 自动识别表头
- 将每一行解析为物料记录
- 显示导入预览表

### 5.2 物料字段解析

根据 Excel 中已有列，尽量提取以下字段：

- 序号
- 名称
- 规格
- 数量
- 单位
- 品牌
- 投标单价
- 投标总价
- 状态
- 采购价（原始文本）

注意：

- 某些字段可能为空
- “采购价”可能是数字、文本、多个价格混合、含注释文本
- 要保留原始值，便于后续复核

### 5.3 搜索关键词生成

对每一行物料生成搜索查询对象，包括：

- 原始查询文本
- 清洗后的名称
- 品牌提示
- 规格提示
- 关键词候选列表

支持两种方式：

1. 规则生成（默认）
2. AI 优化生成（可开关）

### 5.4 电商搜索

V1 支持 Provider 抽象，至少实现以下 Provider：

- `JDOfficialProvider`（首选）
- `TaobaoThirdPartyProvider`（可选启用）

后续预留：

- `PddThirdPartyProvider`
- `WebFallbackProvider`

每个 Provider 需实现统一接口：

```python
class SearchProvider:
    def search(self, query: SearchQuery) -> list[ProductOffer]:
        ...
```

### 5.5 候选商品打分与排序

V1 需支持候选商品打分，排序因素包括：

- 品牌匹配度
- 型号 / 规格匹配度
- 标题相似度
- 类目匹配度
- 单位匹配度
- 价格异常惩罚

输出至少保留 Top N（默认 3）候选结果。

### 5.6 AI 规格归一与解释

AI 用途：

1. 从复杂商品名称中提取规格/品牌/型号/参数
2. 改写查询关键词，提高命中率
3. 判断两个候选商品是否疑似同款
4. 给出“为什么推荐这个候选”的解释文本

注意：

- AI 只做辅助，不做最终唯一裁决
- 最终结果必须可人工复核

### 5.7 比价结果展示

主界面需展示结果表格，至少包含以下列：

- 原始序号
- 原始名称
- 原始规格
- 数量
- 单位
- 品牌
- 投标单价
- 原始采购价
- 京东最低候选价
- 淘宝最低候选价
- 推荐平台
- 推荐价格
- 差价
- 匹配置信度
- AI 备注 / 解释
- 搜索状态

### 5.8 导出结果 Excel

V1 支持导出新的 Excel 文件，包含：

- 原始数据
- 各平台搜索结果摘要
- 推荐结果
- 差价
- 匹配说明

建议加入样式：

- 最优价格高亮
- 未匹配项高亮
- 可疑项高亮

---

## 6. 非功能需求

### 6.1 平台要求

- 必须支持 Windows 10 / 11
- 可打包成本地 EXE
- 首次版本仅支持中文界面

### 6.2 响应性

- UI 不允许因为网络请求而卡死
- 搜索任务必须在后台执行
- 批量处理时界面应可实时显示进度

### 6.3 稳定性

- 某个平台 API 失败时，不应导致整个任务崩溃
- 支持单条失败跳过
- 支持记录错误原因
- 支持重试策略

### 6.4 成本控制

如果某些第三方 API 为按次收费，则必须支持：

- 调用次数统计
- 预估调用成本
- 限制最大调用次数
- 限制单批任务预算

### 6.5 可扩展性

架构必须支持：

- 后续新增 Provider
- 后续替换淘宝第三方供应商
- 后续增加缓存策略
- 后续增加价格监控功能

---

## 7. 技术方案建议（V1）

### 7.1 GUI 框架

V1 推荐可选两套方案：

#### 方案 A（更快落地）

- `CustomTkinter`

优点：

- 上手快
- 原型开发快
- 打包成本地 EXE 较方便

缺点：

- 大型复杂表格 UI 能力中等
- 长期复杂界面扩展能力一般

#### 方案 B（中长期更强）

- `PySide6`

优点：

- 更强的桌面应用能力
- 更适合复杂表格、分栏、任务面板、状态展示

缺点：

- 开发成本略高

V1 可优先采用 `CustomTkinter`，但代码结构应避免过度绑定 UI 框架。

### 7.2 数据处理

- `pandas`
- `openpyxl`

分工建议：

- Pandas：表格读取、清洗、合并、分析、导出 DataFrame
- Openpyxl：导出样式、颜色、高亮、备注、冻结窗格

### 7.3 本地缓存

- `sqlite3`

缓存用途：

1. 搜索结果缓存
2. AI 解析结果缓存
3. 规格归一结果缓存

缓存 TTL 建议：

- 搜索结果：1~3 天
- 价格结果：1 天
- AI 规格解析：7~30 天

### 7.4 并发控制

V1 可采用：

- `ThreadPoolExecutor(max_workers=3~5)`

用途：

- 后台执行 API 请求
- 避免 UI 主线程阻塞
- 控制并发频率，降低被封风险

要求：

- UI 线程不得直接执行网络请求
- 工作线程不得直接更新 UI
- 统一通过任务事件/消息机制回传进度与结果

### 7.5 网络层

推荐：

- `httpx`（优先）
- 或 `requests`（简单版本）

建议：

- 封装统一 HTTP Client
- 支持超时、重试、代理、请求日志

### 7.6 日志

推荐：

- `loguru`

用途：

- 搜索日志
- 缓存命中日志
- API 错误日志
- 导出日志

---

## 8. 系统总体架构

建议采用分层架构：

```text
UI 层
  ├─ 主界面
  ├─ 导入界面
  ├─ 搜索任务面板
  ├─ 结果表格
  └─ 设置界面

应用服务层
  ├─ Excel 导入服务
  ├─ 搜索任务调度服务
  ├─ 成本控制服务
  ├─ 导出服务
  └─ AI 分析服务

领域层
  ├─ MaterialItem
  ├─ SearchQuery
  ├─ ProductOffer
  ├─ CompareResult
  └─ ProviderConfig

基础设施层
  ├─ Provider 接入层
  │    ├─ JDOfficialProvider
  │    ├─ TaobaoThirdPartyProvider
  │    ├─ PddThirdPartyProvider
  │    └─ WebFallbackProvider
  ├─ HTTP Client
  ├─ SQLite Cache
  ├─ DeepSeek Client
  └─ Excel IO
```

---

## 9. 目录结构建议

```text
price_compare_desktop/
├─ app.py
├─ spec.md
├─ requirements.txt
├─ README.md
├─ config/
│  ├─ settings.py
│  ├─ provider_config.py
│  └─ prompts.py
├─ ui/
│  ├─ main_window.py
│  ├─ import_panel.py
│  ├─ result_table.py
│  ├─ task_panel.py
│  └─ settings_dialog.py
├─ domain/
│  ├─ models.py
│  ├─ enums.py
│  └─ schemas.py
├─ services/
│  ├─ excel_import_service.py
│  ├─ query_builder_service.py
│  ├─ compare_service.py
│  ├─ export_service.py
│  ├─ ai_service.py
│  ├─ cost_control_service.py
│  └─ cache_service.py
├─ providers/
│  ├─ base.py
│  ├─ jd_provider.py
│  ├─ taobao_provider.py
│  ├─ pdd_provider.py
│  └─ web_fallback_provider.py
├─ infra/
│  ├─ http_client.py
│  ├─ sqlite_repo.py
│  ├─ logger.py
│  └─ deepseek_client.py
├─ utils/
│  ├─ text_cleaner.py
│  ├─ hash_utils.py
│  ├─ price_parser.py
│  ├─ similarity.py
│  └─ excel_utils.py
├─ data/
│  ├─ cache.db
│  └─ exports/
└─ tests/
   ├─ test_query_builder.py
   ├─ test_price_parser.py
   ├─ test_compare_service.py
   └─ test_cache_service.py
```

---

## 10. 核心数据模型

### 10.1 MaterialItem

表示 Excel 中的一条原始物料。

```python
class MaterialItem:
    row_id: int
    serial_no: str | None
    name: str
    spec: str | None
    quantity: float | None
    unit: str | None
    brand: str | None
    bid_unit_price: float | None
    bid_total_price: float | None
    status: str | None
    purchase_price_raw: str | None
```

### 10.2 SearchQuery

表示面向 Provider 的搜索请求。

```python
class SearchQuery:
    material_id: int
    original_text: str
    normalized_text: str
    brand_hint: str | None
    spec_hint: dict
    keywords: list[str]
```

### 10.3 ProductOffer

表示某平台返回的一个候选商品。

```python
class ProductOffer:
    platform: str
    title: str
    brand: str | None
    spec_text: str | None
    price: float | None
    shop_name: str | None
    product_url: str | None
    image_url: str | None
    source_type: str
    raw_payload: dict | None
```

### 10.4 CompareResult

表示最终用于展示和导出的比价结果。

```python
class CompareResult:
    material_id: int
    best_platform: str | None
    best_price: float | None
    jd_price: float | None
    taobao_price: float | None
    pdd_price: float | None
    price_diff: float | None
    match_score: float | None
    ai_comment: str | None
    status: str
```

---

## 11. 缓存设计

### 11.1 缓存目标

减少重复调用收费 API，提高速度，降低成本。

### 11.2 缓存 key 设计

不建议仅使用：

- `MD5(商品名+参数)`

更建议使用：

- `MD5(platform + normalized_query + provider_version)`

同时数据库中保留：

- 原始 query 文本
- 归一化 query 文本
- provider 名称
- provider 版本

### 11.3 缓存表建议

#### search_cache

- id
- cache_key
- platform
- provider_name
- provider_version
- query_text
- normalized_query
- response_json
- created_at
- expires_at
- hit_count

#### ai_cache

- id
- cache_key
- task_type
- input_text
- output_json
- created_at
- expires_at

---

## 12. 成本控制设计

### 12.1 背景

淘宝等第三方聚合 API 可能按次收费，因此必须尽量少搜、搜准。

### 12.2 V1 要求

系统需支持：

- 单批任务调用次数统计
- 各平台调用次数统计
- 估算总成本
- 单批预算阈值
- 超预算停止补搜

### 12.3 策略建议

#### 低价值物料

- 只搜京东
- 或仅搜一个便宜数据源

#### 高价值物料

- 京东 + 淘宝双平台搜索
- 必要时做详情二次确认

#### 命中缓存时

- 不再调用外部 API

---

## 13. 搜索流程设计

### 13.1 单条物料流程

```text
读取原始物料
  ↓
字段清洗
  ↓
规则提取品牌/规格/单位
  ↓
生成基础关键词
  ↓
（可选）调用 AI 优化关键词
  ↓
先查缓存
  ↓
命中缓存 → 返回缓存结果
  ↓
未命中缓存 → 调用 Provider 搜索
  ↓
结果标准化
  ↓
候选打分与排序
  ↓
（可选）AI 辅助解释
  ↓
生成 CompareResult
```

### 13.2 批量 Excel 流程

```text
导入 Excel
  ↓
解析为 MaterialItem 列表
  ↓
逐条提交后台任务
  ↓
按平台限流执行搜索
  ↓
实时更新表格状态
  ↓
全部完成后生成导出结果
```

---

## 14. AI 设计（DeepSeek）

### 14.1 AI 使用边界

AI 只负责以下工作：

- 商品文本理解
- 规格抽取
- 查询词优化
- 候选解释
- 相似商品辅助判断

AI 不负责：

- 直接替代平台搜索
- 最终自动下单决策
- 无限制自动重试

### 14.2 AI 输入示例

输入：

- 原始物料名
- 规格字段
- 品牌字段
- 候选商品标题列表

输出：

- 提取的品牌
- 提取的规格参数
- 推荐搜索关键词
- 候选商品相似度说明
- 风险提示（疑似不同规格）

### 14.3 AI 缓存

AI 结果建议缓存，以减少重复调用。

---

## 15. Provider 设计要求

### 15.1 统一接口

所有 Provider 必须对外返回统一标准结构 `ProductOffer`。

### 15.2 Provider 必须负责

- 签名
- 参数构建
- HTTP 调用
- 原始响应解析
- 字段标准化
- 错误处理
- 限流配合

### 15.3 已知 Provider

#### JDOfficialProvider

- 优先级：高
- 数据来源：京东官方开放平台
- 作用：主搜索来源

#### TaobaoThirdPartyProvider

- 优先级：中
- 数据来源：第三方聚合 API
- 作用：补充比价搜索
- 注意：可能存在调用成本

#### PddThirdPartyProvider

- 优先级：低（V1 预留）
- 数据来源：第三方聚合 API 或后续官方/联盟接口

#### WebFallbackProvider

- 优先级：最低（V1 预留）
- 作用：当 API 路线失效时的后备方案

---

## 16. UI 需求（V1）

### 16.1 主界面区域

建议分为以下区域：

1. 顶部工具栏
   - 导入 Excel
   - 开始搜索
   - 停止任务
   - 导出结果
   - 设置

2. 左侧任务区
   - 当前任务状态
   - 平台启用开关
   - AI 开关
   - 预算设置

3. 中央结果表格
   - 显示每条物料结果
   - 支持滚动
   - 支持状态列

4. 右侧详情面板（可选）
   - 展示当前选中物料的候选商品详情
   - 展示 AI 解释

5. 底部日志区（可选）
   - 显示错误、重试、缓存命中等信息

### 16.2 状态展示

每条记录至少支持以下状态：

- 未处理
- 搜索中
- 已完成
- 部分完成
- 失败
- 使用缓存

---

## 17. 错误处理与重试

### 17.1 错误分类

- 网络错误
- API 响应格式错误
- 签名错误
- 限流错误
- 空结果
- AI 解析失败
- Excel 读写错误

### 17.2 重试策略

V1 建议：

- 网络超时：最多重试 2 次
- 限流错误：指数退避后重试
- 空结果：可尝试用 AI 改写关键词后重搜 1 次
- 严重错误：记录日志并跳过该条

---

## 18. 测试要求

V1 至少编写以下测试：

- `price_parser` 单元测试
- `query_builder` 单元测试
- `cache_service` 单元测试
- `compare_service` 单元测试
- Provider 响应解析测试（mock 数据）

重点测试对象：

- 混乱采购价字段解析
- 规格归一
- 缓存命中逻辑
- 成本统计逻辑
- 候选排序逻辑

---

## 19. 里程碑建议

### M1：基础数据流跑通

- Excel 导入
- MaterialItem 解析
- 表格展示

### M2：京东搜索跑通

- 接入 JD Provider
- 单条物料搜索
- 候选结果展示

### M3：缓存与导出

- SQLite 缓存
- 导出 Excel

### M4：AI 能力接入

- DeepSeek 接入
- 查询优化
- 候选解释

### M5：淘宝第三方接入

- 接入 Taobao Provider
- 成本统计
- 预算控制

### M6：结果优化

- 候选打分完善
- UI 细节优化
- 批量稳定性增强

---

## 20. MVP 验收标准

满足以下条件可视为 V1 MVP 可用：

1. 可以导入 Excel 文件
2. 可以识别并展示物料列表
3. 可以对至少一个平台执行搜索
4. 可以生成候选商品结果
5. 可以输出推荐价格和推荐平台
6. 可以导出结果 Excel
7. UI 在批量处理中不会卡死
8. 有缓存能力
9. 有基本错误处理和日志
10. 可配置 API Key 和基础参数

---

## 21. 后续演进方向（V2+）

- 拼多多接入
- 多工作表支持
- 自定义列映射
- 用户手工确认“同款白名单”
- 历史价格走势
- 价格监控
- 云端同步配置
- 多项目采购单管理
- 生成采购建议报告
- 更智能的替代品推荐

---

## 22. 给 Codex / AI 编程工具的额外说明

后续使用 Codex 实现本项目时，请遵守以下原则：

1. 优先保持模块边界清晰，不要把 UI、网络、缓存、业务逻辑写在一个文件中
2. Provider 必须统一接口，便于后续切换数据源
3. 所有第三方 API Key 必须通过配置文件或环境变量加载，不要写死在代码里
4. 所有线程 / 后台任务不得直接更新 UI
5. 所有价格结果必须允许为空，不能假设每次都搜得到
6. 必须保留原始数据与中间结果，便于用户复核
7. Excel 导出时尽量保留原始列，并追加新列，而不是覆盖原始数据
8. 尽量先写小步可运行版本，再逐步扩展

---

## 23. 推荐的下一份文档

在 `spec.md` 基础上，后续建议再补两份文档：

1. `architecture.md`
   - 更详细的模块依赖、线程模型、调用链、数据库表结构

2. `tasks.md`
   - 按功能拆成可执行开发任务，方便 Codex 分阶段实现

---

## 24. 当前结论

本项目的第一版最适合定位为：

**面向工程/采购 Excel 的 Windows 本地批量比价助手**

而不是泛化的“全网购物比价软件”。

V1 应优先解决：

- Excel 批量导入
- 规则清洗
- 至少一个稳定 Provider
- 缓存
- 结果表导出
- AI 辅助规格理解与解释

当以上能力跑通后，再逐步增加更多平台和更复杂的比价策略。
