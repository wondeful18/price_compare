# DeepSeek + 万邦淘宝 搜索/详情 DEMO

## 目标

验证最小真实链路：

1. 输入 `1~3` 个商品词
2. 可选调用 DeepSeek 优化搜索词
3. 调用万邦 `taobao/item_search`
4. 从搜索结果里筛出前 `N` 条候选
5. 可选调用万邦 `taobao/item_get` 查询详情

## 运行

只做搜索：

```powershell
python .\demo_onebound_taobao.py 电钻 --page-size 20 --onebound-key <key> --onebound-secret <secret>
```

搜索后筛 3 条并查详情：

```powershell
python .\demo_onebound_taobao.py 电钻 --page-size 20 --pick-top 3 --with-detail --onebound-key <key> --onebound-secret <secret>
```

启用 DeepSeek：

```powershell
$env:DEEPSEEK_API_KEY="<deepseek-key>"
python .\demo_onebound_taobao.py 电钻 --page-size 20 --pick-top 3 --with-detail --onebound-key <key> --onebound-secret <secret>
```

关闭促销价详情：

```powershell
python .\demo_onebound_taobao.py 电钻 --with-detail --detail-raw-price --onebound-key <key> --onebound-secret <secret>
```

## 参数

- `--page-size`：搜索时拉取的候选数量，默认 `20`
- `--pick-top`：从搜索结果里筛选前几条，默认 `3`
- `--with-detail`：对筛出的候选继续调 `item_get`
- `--detail-raw-price`：详情接口不带 `is_promotion=1`
- `--no-ai`：不启用 DeepSeek

## 输出

- 搜索原始响应保存到 `data/demo_logs/onebound_{index}.json`
- 详情原始响应保存到 `data/demo_logs/onebound_{index}_detail_{rank}_{num_iid}.json`
- 控制台会打印：
  - 搜索命中的候选列表
  - 筛选出的前 N 条候选及筛选依据
  - 详情接口返回的核心字段摘要

## 当前筛选逻辑

当前是轻量规则筛选，不依赖 DeepSeek：

- 标题与搜索词的重合度
- 是否有价格
- 是否有店铺
- 是否能提取 `num_iid`
- 是否有详情链接

如果后面要把“筛 3 条”做得更稳，再接 AI 只会是增强项，不是这个全流程的前置条件。
