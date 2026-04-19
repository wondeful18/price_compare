# price_compare

Windows 桌面端的工程采购批量比价工具。

当前已完成：`Phase 4 - AI 增强能力接入`

## 运行

1. 安装依赖

```bash
pip install -r requirements.txt
```

2. 启动应用

```bash
python app.py
```

## 当前能力

- 导入本地 `.xlsx`
- 读取首个工作表
- 自动按表头或列位置解析物料字段
- 在桌面界面中展示导入预览
- 通过 `JDOfficialProvider` 执行单平台搜索
- 批量搜索时异步刷新状态和推荐价格
- 搜索结果写入本地 SQLite 缓存
- 再次搜索相同查询时可直接命中缓存
- 支持导出带推荐结果的 Excel 文件
- 支持 AI 优化查询词
- 支持 AI 生成推荐解释
- 支持空结果后 AI 改写并重试一次
- 当前 JD 默认运行在 `mock` 模式，便于本地演示和验收

## 测试

```bash
python -m unittest discover -s tests
```

## 独立 DEMO

如果只想验证 `DeepSeek + 万邦淘宝搜索` 最小联调，不走 GUI，可看：

- [demo_onebound_taobao.py](/i:/biaoshu/price_compare/demo_onebound_taobao.py)
- [demo_onebound_taobao.md](/i:/biaoshu/price_compare/demo_onebound_taobao.md)
