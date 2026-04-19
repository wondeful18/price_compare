from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen


ONEBOUND_SEARCH_URL = "https://api-gw.onebound.cn/taobao/item_search/"
ONEBOUND_DETAIL_URL = "https://api-gw.onebound.cn/taobao/item_get/"
DEEPSEEK_CHAT_URL = "https://api.deepseek.com/chat/completions"

PRICE_KEYS = ("promotion_price", "price", "sale_price", "orginal_price")
TITLE_KEYS = ("title", "item_title", "name")
URL_KEYS = ("detail_url", "item_url", "url")
SHOP_KEYS = ("nick", "seller_name", "shop_name")


@dataclass(slots=True)
class DemoConfig:
    onebound_key: str
    onebound_secret: str
    deepseek_api_key: str | None = None
    deepseek_model: str = "deepseek-chat"
    page_size: int = 20
    timeout_seconds: int = 30
    lang: str = "zh-CN"
    detail_promotion_only: bool = True
    max_price: float | None = None


@dataclass(slots=True)
class CandidateScore:
    item: dict[str, Any]
    score: float
    reasons: list[str]


@dataclass(slots=True)
class DetailMatch:
    score: float
    price_text: str
    link: str
    title: str
    sku_text: str
    source_path: str
    sku_id: str = ""


def main() -> int:
    args = parse_args()
    config = DemoConfig(
        onebound_key=args.onebound_key or os.getenv("ONEBOUND_KEY", ""),
        onebound_secret=args.onebound_secret or os.getenv("ONEBOUND_SECRET", ""),
        deepseek_api_key=args.deepseek_api_key or os.getenv("DEEPSEEK_API_KEY"),
        deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        page_size=args.page_size,
        detail_promotion_only=not args.detail_raw_price,
        max_price=args.max_price,
    )

    if not config.onebound_key:
        print("缺少 OneBound key。请先设置 ONEBOUND_KEY，或通过 --onebound-key 传入。", file=sys.stderr)
        return 1
    if not config.onebound_secret:
        print("缺少 OneBound secret。请先设置 ONEBOUND_SECRET，或通过 --onebound-secret 传入。", file=sys.stderr)
        return 1

    queries = normalize_queries(args.queries)
    if not 1 <= len(queries) <= 3:
        print("请传入 1 到 3 个商品词。", file=sys.stderr)
        return 1

    log_dir = Path("data") / "demo_logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    for index, query in enumerate(queries, start=1):
        print(f"\n===== 查询 {index}: {query} =====")
        optimized_query = query
        if not args.no_ai and config.deepseek_api_key:
            try:
                optimized_query, ai_reason = optimize_query_with_deepseek(config, query)
                print(f"DeepSeek 优化词: {optimized_query}")
                if ai_reason:
                    print(f"优化原因: {ai_reason}")
            except Exception as exc:
                print(f"DeepSeek 调用失败，已降级为原词搜索: {exc}")
        else:
            print("DeepSeek 未启用，直接使用原词搜索。")

        try:
            response = search_taobao(config, optimized_query)
        except Exception as exc:
            print(f"万邦淘宝搜索失败: {exc}", file=sys.stderr)
            continue

        dump_path = log_dir / f"onebound_{index}.json"
        dump_path.write_text(json.dumps(response, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"原始搜索响应已保存: {dump_path}")

        items = extract_items(response)
        print_results(items)
        if not items:
            continue

        picked = pick_top_candidates(items, optimized_query, top_n=args.pick_top)
        print_top_candidates(picked)

        if args.with_detail:
            fetch_and_print_details(config, picked, log_dir, index, optimized_query)

    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="最小联调 DEMO：DeepSeek + 万邦淘宝搜索/详情")
    parser.add_argument("queries", nargs="+", help="1 到 3 个商品词，例如：得力 活络扳手 6寸")
    parser.add_argument("--onebound-key", help="万邦 key；默认读取环境变量 ONEBOUND_KEY")
    parser.add_argument("--onebound-secret", default="", help="万邦 secret；默认读取环境变量 ONEBOUND_SECRET")
    parser.add_argument("--deepseek-api-key", help="DeepSeek API Key；未提供则不启用 AI")
    parser.add_argument("--page-size", type=int, default=20, help="搜索候选数量，默认 20")
    parser.add_argument("--pick-top", type=int, default=3, help="从搜索结果中筛选前 N 条做后续处理，默认 3")
    parser.add_argument("--with-detail", action="store_true", help="对筛出的候选继续调用 item_get 查询详情")
    parser.add_argument("--detail-raw-price", action="store_true", help="详情接口不带 is_promotion=1，默认带促销价")
    parser.add_argument("--max-price", type=float, help="最高限价；最终推荐只会在该价格及以下的 SKU 中选择")
    parser.add_argument("--no-ai", action="store_true", help="强制关闭 DeepSeek 优化")
    return parser.parse_args()


def normalize_queries(raw_queries: list[str]) -> list[str]:
    tokens = [token.strip() for token in raw_queries if token.strip()]
    if tokens and tokens[0].lower() == "queries":
        tokens = tokens[1:]
    if not tokens:
        return []

    merged = " ".join(tokens).strip()
    bracket_match = re.fullmatch(r"\[(.*)\]", merged)
    if bracket_match:
        inner = bracket_match.group(1).strip()
        quoted = re.findall(r'"([^"]+)"|\'([^\']+)\'', inner)
        if quoted:
            return [(first or second).strip() for first, second in quoted if (first or second).strip()]
        if inner:
            return [inner]

    return tokens


def optimize_query_with_deepseek(config: DemoConfig, query: str) -> tuple[str, str | None]:
    prompt = (
        "你是采购商品搜索词优化助手，专门处理五金、建材、酒店用品等中文采购简称。"
        "你的任务是先把原始采购词标准化，再改写成适合淘宝搜索的简洁中文短语。"
        "优先识别品牌、品类、规格、材质、颜色、单位，不要照抄歧义简称。"
        "遇到五金建材常见简写时，优先按行业常见含义展开，例如："
        "+批=十字螺丝刀或十字螺丝批，-批=一字螺丝刀或一字螺丝批，活络扳手=活动扳手，"
        "梅花批=梅花螺丝刀，内六角=内六角扳手或内六角螺丝刀。"
        "遇到酒店用品时，优先展开成常见采购品类词，例如垃圾袋、卷纸、抽纸、洗手液、地巾、毛巾、牙具、拖鞋等。"
        "如果原词有歧义，优先选择最常见、最容易在电商中搜索到的商品叫法。"
        "不要编造品牌，不要编造不存在的规格，不要加入无关修饰词。"
        "输出的 optimized_query 应尽量采用 品牌 + 标准品类 + 关键规格 的形式，控制在 8 到 24 个中文字符左右。"
        '只返回 JSON，格式为 {"optimized_query":"...","reason":"..."}。'
    )
    payload = {
        "model": config.deepseek_model,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": query},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    data = post_json(
        DEEPSEEK_CHAT_URL,
        payload,
        headers={
            "Authorization": f"Bearer {config.deepseek_api_key}",
            "Content-Type": "application/json",
        },
        timeout_seconds=config.timeout_seconds,
    )
    content = data["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    optimized_query = str(parsed.get("optimized_query", query)).strip() or query
    reason = parsed.get("reason")
    return optimized_query, str(reason).strip() if reason else None


def search_taobao(config: DemoConfig, query: str) -> dict[str, Any]:
    params = {
        "key": config.onebound_key,
        "secret": config.onebound_secret,
        "q": query,
        "start_price": 0,
        "end_price": 0,
        "page": 1,
        "cat": 0,
        "discount_only": "",
        "sort": "",
        "page_size": config.page_size,
        "seller_info": "",
        "nick": "",
        "ppath": "",
        "imgid": "",
        "filter": "",
        "lang": config.lang,
    }
    url = f"{ONEBOUND_SEARCH_URL}?{urlencode(params)}"
    print(f"Search URL: {mask_secret(url, config.onebound_secret)}")
    return get_json(url, timeout_seconds=config.timeout_seconds)


def get_taobao_detail(config: DemoConfig, num_iid: str) -> dict[str, Any]:
    params = {
        "key": config.onebound_key,
        "secret": config.onebound_secret,
        "num_iid": num_iid,
        "is_promotion": 1 if config.detail_promotion_only else 0,
        "lang": config.lang,
    }
    url = f"{ONEBOUND_DETAIL_URL}?{urlencode(params)}"
    print(f"Detail URL: {mask_secret(url, config.onebound_secret)}")
    return get_json(url, timeout_seconds=config.timeout_seconds)


def print_results(items: list[dict[str, Any]]) -> None:
    if not items:
        print("未解析到商品结果。请检查响应结构，或确认当前 key 是否返回真实搜索数据。")
        return

    print(f"命中 {len(items)} 个候选：")
    for idx, item in enumerate(items, start=1):
        title = safe_get(item, *TITLE_KEYS)
        price = safe_get(item, *PRICE_KEYS)
        seller = safe_get(item, *SHOP_KEYS)
        url = safe_get(item, *URL_KEYS)
        print(f"{idx}. 标题: {title}")
        print(f"   价格: {price}")
        print(f"   店铺: {seller}")
        print(f"   链接: {url}")


def print_top_candidates(picked: list[CandidateScore]) -> None:
    if not picked:
        print("未筛出可继续处理的候选。")
        return

    print(f"\n筛选后的前 {len(picked)} 条候选：")
    for idx, candidate in enumerate(picked, start=1):
        item = candidate.item
        title = safe_get(item, *TITLE_KEYS)
        price = safe_get(item, *PRICE_KEYS)
        seller = safe_get(item, *SHOP_KEYS)
        num_iid = extract_num_iid(item) or "-"
        reason_text = "；".join(candidate.reasons) if candidate.reasons else "基础字段完整"
        print(f"{idx}. score={candidate.score:.2f} num_iid={num_iid}")
        print(f"   标题: {title}")
        print(f"   价格: {price}")
        print(f"   店铺: {seller}")
        print(f"   依据: {reason_text}")


def fetch_and_print_details(
    config: DemoConfig,
    picked: list[CandidateScore],
    log_dir: Path,
    query_index: int,
    query: str,
) -> None:
    if not picked:
        return

    print("\n开始查询详情：")
    final_matches: list[tuple[CandidateScore, DetailMatch]] = []
    for detail_index, candidate in enumerate(picked, start=1):
        num_iid = extract_num_iid(candidate.item)
        if not num_iid:
            print(f"{detail_index}. 跳过：未从候选结果中解析出 num_iid")
            continue

        try:
            detail = get_taobao_detail(config, num_iid)
        except Exception as exc:
            print(f"{detail_index}. 详情查询失败 num_iid={num_iid}: {exc}")
            continue

        dump_path = log_dir / f"onebound_{query_index}_detail_{detail_index}_{num_iid}.json"
        dump_path.write_text(json.dumps(detail, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{detail_index}. 详情响应已保存: {dump_path}")
        print_detail(detail_index, detail)

        match = find_best_detail_match(detail, query)
        if match is not None:
            final_matches.append((candidate, match))
            print(f"   SKU match price: {match.price_text}")
            print(f"   SKU match link: {match.link}")
            if match.sku_text:
                print(f"   SKU match attrs: {match.sku_text}")
            if match.sku_id:
                print(f"   SKU match id: {match.sku_id}")

    print_final_detail_match(final_matches, config.max_price)


def print_detail(detail_index: int, payload: dict[str, Any]) -> None:
    item = payload.get("item")
    if not isinstance(item, dict):
        print(f"{detail_index}. 未解析到 item 详情对象。")
        return

    title = safe_get(item, "title")
    price = safe_get(item, *PRICE_KEYS)
    shop_name = safe_get(item, "nick")
    brand = safe_get(item, "brand")
    stock = safe_get(item, "num")
    sold = safe_get(item, "sales")
    favcount = safe_get(item, "favcount")
    detail_url = safe_get(item, "detail_url")
    desc_short = safe_get(item, "desc_short")

    print(f"{detail_index}. 详情标题: {title}")
    print(f"   详情价格: {price}")
    print(f"   店铺: {shop_name}")
    print(f"   品牌: {brand}")
    print(f"   库存: {stock}")
    print(f"   销量: {sold}")
    print(f"   收藏: {favcount}")
    print(f"   链接: {detail_url}")
    if desc_short:
        print(f"   简述: {desc_short}")


def print_final_detail_match(final_matches: list[tuple[CandidateScore, DetailMatch]], max_price: float | None) -> None:
    if not final_matches:
        print("\n未从详情响应中解析出更细的 SKU 价格，当前仍只能使用商品主价格。")
        return

    if max_price is not None:
        limited_matches = [
            pair for pair in final_matches if (to_float(pair[1].price_text) is not None and to_float(pair[1].price_text) <= max_price)
        ]
        if not limited_matches:
            print(f"\n没有候选 SKU 满足最高限价 {max_price:.2f}。")
            return
        final_matches = limited_matches
        print(f"\n已应用最高限价: {max_price:.2f}")

    final_matches.sort(key=lambda pair: (pair[0].score + pair[1].score, pair[1].score), reverse=True)
    candidate, match = final_matches[0]
    print("\n最终推荐：")
    print(f"num_iid: {extract_num_iid(candidate.item) or '-'}")
    print(f"商品标题: {match.title}")
    print(f"最匹配价格: {match.price_text}")
    print(f"商品链接: {match.link}")
    if match.sku_text:
        print(f"匹配SKU: {match.sku_text}")
    if match.sku_id:
        print(f"SKU ID: {match.sku_id}")
    print(f"明细路径: {match.source_path}")


def find_best_detail_match(payload: dict[str, Any], query: str) -> DetailMatch | None:
    item = payload.get("item")
    if not isinstance(item, dict):
        return None

    query_terms = build_query_phrases(query, tokenize_text(query))
    size_terms = extract_size_tokens(query)
    base_link = safe_get(item, "detail_url")
    base_title = safe_get(item, "title")
    base_price = safe_get(item, *PRICE_KEYS)

    sku_match = find_best_sku_match(item, query, base_link, base_title)
    if sku_match is not None:
        return sku_match

    matches: list[DetailMatch] = []
    for path, node in walk_nodes(item, "item"):
        if not isinstance(node, dict):
            continue

        price_text = extract_price_text(node)
        if not price_text:
            continue

        blob = compact_text(flatten_scalar_text(node))
        local_score = 0.0
        local_hits: list[str] = []

        for term in query_terms:
            normalized = compact_text(term)
            if normalized and normalized in blob:
                local_score += 8
                local_hits.append(term)

        if size_terms:
            matched_sizes = [size for size in size_terms if size in blob]
            if matched_sizes:
                local_score += len(matched_sizes) * 16
                local_hits.extend(matched_sizes)
            else:
                local_score -= 8

        if "sku" in path.lower():
            local_score += 6
        if any(key in node for key in PRICE_KEYS):
            local_score += 4

        if local_score <= 0:
            continue

        sku_text = build_sku_text(node, local_hits)
        link = safe_get(node, *URL_KEYS) or base_link
        title = safe_get(node, *TITLE_KEYS) or base_title
        matches.append(
            DetailMatch(
                score=local_score,
                price_text=price_text,
                link=link,
                title=title,
                sku_text=sku_text,
                source_path=path,
                sku_id=safe_get(node, "sku_id"),
            )
        )

    if matches:
        matches.sort(key=lambda match: (match.score, to_float(match.price_text) is not None), reverse=True)
        return matches[0]

    if not base_price:
        return None
    return DetailMatch(
        score=1.0,
        price_text=base_price,
        link=base_link,
        title=base_title,
        sku_text="",
        source_path="item",
    )


def find_best_sku_match(item: dict[str, Any], query: str, base_link: str, base_title: str) -> DetailMatch | None:
    skus = item.get("skus")
    if not isinstance(skus, dict):
        return None

    sku_list = skus.get("sku")
    if not isinstance(sku_list, list):
        return None

    query_terms = build_query_phrases(query, tokenize_text(query))
    size_terms = extract_size_tokens(query)
    matches: list[DetailMatch] = []

    for index, sku in enumerate(sku_list):
        if not isinstance(sku, dict):
            continue

        price_text = extract_price_text(sku)
        if not price_text:
            continue

        properties_name = safe_get(sku, "properties_name", "properties", "name")
        blob = compact_text(flatten_scalar_text(sku))
        local_score = 20.0
        local_hits: list[str] = []

        for term in query_terms:
            normalized = compact_text(term)
            if normalized and normalized in blob:
                local_score += 10
                local_hits.append(term)

        if size_terms:
            matched_sizes = [size for size in size_terms if size in blob]
            if matched_sizes:
                local_score += len(matched_sizes) * 20
                local_hits.extend(matched_sizes)
            else:
                local_score -= 12

        if "颜色分类" in properties_name:
            local_score += 4

        if local_score <= 0:
            continue

        sku_id = safe_get(sku, "sku_id")
        link = build_sku_link(base_link, sku_id)
        sku_text = properties_name or build_sku_text(sku, local_hits)
        matches.append(
            DetailMatch(
                score=local_score,
                price_text=price_text,
                link=link,
                title=base_title,
                sku_text=sku_text,
                source_path=f"item.skus.sku[{index}]",
                sku_id=sku_id,
            )
        )

    if not matches:
        return None

    matches.sort(key=lambda match: (match.score, to_float(match.price_text) is not None), reverse=True)
    return matches[0]


def build_sku_link(base_link: str, sku_id: str) -> str:
    if not base_link or not sku_id:
        return base_link
    separator = "&" if "?" in base_link else "?"
    return f"{base_link}{separator}skuId={sku_id}"


def walk_nodes(node: Any, path: str) -> list[tuple[str, Any]]:
    nodes: list[tuple[str, Any]] = [(path, node)]
    if isinstance(node, dict):
        for key, value in node.items():
            nodes.extend(walk_nodes(value, f"{path}.{key}"))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            nodes.extend(walk_nodes(value, f"{path}[{index}]"))
    return nodes


def flatten_scalar_text(node: Any) -> str:
    parts: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            parts.append(str(key))
            parts.append(flatten_scalar_text(value))
    elif isinstance(node, list):
        for value in node:
            parts.append(flatten_scalar_text(value))
    elif node not in (None, ""):
        parts.append(str(node))
    return " ".join(part for part in parts if part)


def extract_price_text(node: dict[str, Any]) -> str:
    for key in PRICE_KEYS:
        value = node.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def build_sku_text(node: dict[str, Any], local_hits: list[str]) -> str:
    fields: list[str] = []
    for key in ("sku", "sku_name", "name", "spec", "spec_name", "prop_path", "properties", "value"):
        value = node.get(key)
        if value not in (None, ""):
            fields.append(str(value))
    for hit in local_hits:
        if hit not in fields:
            fields.append(hit)

    deduped: list[str] = []
    seen: set[str] = set()
    for field in fields:
        normalized = compact_text(field)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(field)
    return " | ".join(deduped[:6])


def extract_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = [
        payload.get("items"),
        payload.get("item"),
        payload.get("result"),
        payload.get("data"),
    ]
    for candidate in candidates:
        items = unwrap_items(candidate)
        if items:
            return items
    return []


def unwrap_items(candidate: Any) -> list[dict[str, Any]]:
    if isinstance(candidate, list):
        return [item for item in candidate if isinstance(item, dict)]
    if isinstance(candidate, dict):
        for key in ("items", "item", "data", "result", "list"):
            nested = candidate.get(key)
            if isinstance(nested, list):
                return [item for item in nested if isinstance(item, dict)]
    return []


def pick_top_candidates(items: list[dict[str, Any]], query: str, top_n: int) -> list[CandidateScore]:
    query_tokens = tokenize_text(query)
    compact_query = compact_text(query)
    query_phrases = build_query_phrases(query, query_tokens)
    negative_phrases = build_negative_phrases(compact_query)
    scored: list[CandidateScore] = []

    for item in items:
        score = 0.0
        reasons: list[str] = []
        title = safe_get(item, *TITLE_KEYS)
        compact_title = compact_text(title)
        title_tokens = tokenize_text(title)

        strong_hits = [phrase for phrase in query_phrases if phrase and phrase in compact_title]
        if strong_hits:
            score += len(strong_hits) * 12
            reasons.append(f"标题短语命中 {','.join(strong_hits)}")

        overlap = sorted(token for token in set(query_tokens) & set(title_tokens) if len(token) >= 2)
        if overlap:
            score += len(overlap) * 5
            reasons.append(f"关键词命中 {','.join(overlap)}")

        if compact_query and compact_query in compact_title:
            score += 18
            reasons.append("完整查询命中")

        query_sizes = extract_size_tokens(query)
        title_sizes = extract_size_tokens(title)
        if query_sizes and title_sizes:
            matched_sizes = sorted(set(query_sizes) & set(title_sizes))
            if matched_sizes:
                score += len(matched_sizes) * 8
                reasons.append(f"尺寸命中 {','.join(matched_sizes)}")
            else:
                score -= 6
                reasons.append("尺寸不一致")

        for negative_phrase, penalty in negative_phrases:
            if negative_phrase in compact_title:
                score -= penalty
                reasons.append(f"疑似跑偏 {negative_phrase}")

        if safe_get(item, *PRICE_KEYS):
            score += 3
            reasons.append("有价格")
        if safe_get(item, *SHOP_KEYS):
            score += 2
            reasons.append("有店铺")
        if extract_num_iid(item):
            score += 2
            reasons.append("有 num_iid")
        if safe_get(item, *URL_KEYS):
            score += 1
            reasons.append("有详情链接")
        scored.append(CandidateScore(item=item, score=score, reasons=reasons))

    scored.sort(
        key=lambda candidate: (
            candidate.score,
            to_float(safe_get(candidate.item, *PRICE_KEYS)) is not None,
            len(safe_get(candidate.item, *TITLE_KEYS)),
        ),
        reverse=True,
    )
    return scored[: max(top_n, 0)]


def tokenize_text(text: str) -> list[str]:
    expanded = re.sub(r"([0-9]+(?:\.[0-9]+)?(?:寸|mm|cm|v|伏|n\.m|nm))", r" \1 ", text, flags=re.IGNORECASE)
    tokens = [token.strip().lower() for token in re.split(r"[\s/,_|+\-]+", expanded) if token.strip()]
    if tokens:
        return tokens
    compact = compact_text(text)
    return [compact] if compact else []


def compact_text(text: str) -> str:
    return re.sub(r"\s+", "", text).strip().lower()


def build_query_phrases(query: str, query_tokens: list[str]) -> list[str]:
    compact_query = compact_text(query)
    phrases: list[str] = []
    if compact_query:
        phrases.append(compact_query)

    for token in query_tokens:
        if len(token) >= 2:
            phrases.append(token)

    synonym_groups = [
        {"活动扳手", "活络扳手", "活口扳手", "活扳手", "活动板手", "活络板手"},
        {"十字螺丝刀", "十字螺丝批", "十字批", "+批"},
        {"一字螺丝刀", "一字螺丝批", "一字批", "-批"},
        {"得力", "deli"},
        {"威力狮"},
    ]
    compact_query_tokens = set(query_tokens)
    compact_query_text = compact_text(query)
    for group in synonym_groups:
        if any(term in compact_query_text or term in compact_query_tokens for term in group):
            phrases.extend(sorted(group, key=len, reverse=True))

    seen: set[str] = set()
    ordered: list[str] = []
    for phrase in phrases:
        normalized = compact_text(phrase)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def build_negative_phrases(compact_query: str) -> list[tuple[str, float]]:
    penalties: list[tuple[str, float]] = []
    if any(term in compact_query for term in ("活动扳手", "活络扳手", "活口扳手", "活扳手")):
        penalties.extend(
            [
                ("扭力扳手", 16),
                ("力矩扳手", 16),
                ("冲击扳手", 16),
                ("电动扳手", 14),
                ("棘轮扳手", 10),
                ("套装", 8),
            ]
        )
    if any(term in compact_query for term in ("十字螺丝刀", "十字螺丝批", "十字批", "+批")):
        penalties.extend([("一字", 10), ("螺丝", 6), ("自攻", 10), ("钻尾丝", 10)])
    if any(term in compact_query for term in ("一字螺丝刀", "一字螺丝批", "一字批", "-批")):
        penalties.extend([("十字", 10), ("螺丝", 6), ("自攻", 10), ("钻尾丝", 10)])
    return penalties


def extract_size_tokens(text: str) -> list[str]:
    matches = re.findall(r"([0-9]+(?:[xX\*][0-9]+)?(?:mm|cm|寸|v|伏|n\.m|nm))", text, flags=re.IGNORECASE)
    return [match.lower().replace("*", "x") for match in matches]


def extract_num_iid(item: dict[str, Any]) -> str | None:
    direct = safe_get(item, "num_iid", "item_id", "id")
    if direct:
        return direct

    detail_url = safe_get(item, *URL_KEYS)
    if not detail_url:
        return None

    parsed = urlparse(detail_url)
    query = parse_qs(parsed.query)
    item_ids = query.get("id")
    if item_ids and item_ids[0]:
        return item_ids[0]
    return None


def safe_get(item: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def to_float(value: str) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def mask_secret(url: str, secret: str) -> str:
    return url.replace(secret, "********") if secret else url


def get_json(url: str, timeout_seconds: int) -> dict[str, Any]:
    request = Request(url, method="GET")
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
    except URLError as exc:
        raise RuntimeError(f"网络错误: {exc.reason}") from exc


def post_json(url: str, payload: dict[str, Any], headers: dict[str, str], timeout_seconds: int) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    request = Request(url, data=data, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
    except URLError as exc:
        raise RuntimeError(f"网络错误: {exc.reason}") from exc


if __name__ == "__main__":
    raise SystemExit(main())
