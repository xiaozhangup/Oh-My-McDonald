"""Business transformations. Prices are integer fen at the pricing boundary."""
import calendar
import csv
import io
import json
import os
import random
import re
import tempfile
from collections import Counter
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo
from .mcp import McdError

TZ = ZoneInfo('Asia/Shanghai')


def now():
    return datetime.now(TZ).isoformat(timespec='seconds')


def context(store):
    if not str(store).isdigit():
        raise ValueError('门店编码必须是数字')
    return {'storeCode': str(store), 'orderType': 1, 'beType': 1}


def money(fen):
    return f'¥{Decimal(str(fen)) / 100:.2f}'


def yuan_to_fen(value):
    try:
        amount = Decimal(str(value))
    except InvalidOperation:
        raise ValueError('金额需要是最多两位小数的有限数字') from None
    if not amount.is_finite() or amount.as_tuple().exponent < -2:
        raise ValueError('金额需要是最多两位小数的有限数字')
    return int(amount * 100)


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def private_write(path, value):
    path = Path(path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def load_state(path):
    return read_json(path) if Path(path).expanduser().exists() else {'foods': {}, 'stores': {}}


def menu_rows(menu):
    return [{'code': str(code), 'name': item['name'], 'menuPriceFen': yuan_to_fen(item['currentPrice'])}
            for code, item in menu['meals'].items()]


def default_item(detail):
    rounds = []
    for group in detail.get('rounds', []):
        children = [{'code': str(c['code']), 'quantity': c['quantity']}
                    for c in group['choices'] if c.get('isDefault') == 1 and c['quantity'] > 0]
        count = sum(c['quantity'] for c in children)
        if count < group['minQuantity'] or count > group['maxQuantity']:
            raise ValueError(f"{detail['name']} 需要手动选择套餐子项")
        if children:
            rounds.append({'round': str(group['id']), 'comboItemList': children})
    result = {'productCode': str(detail['code']), 'quantity': 1}
    if rounds:
        result['roundList'] = rounds
    return result


def validate_basket(client, store, items):
    """Resolve actual names and quantities; reject unavailable rounds/variants."""
    if not isinstance(items, list) or not items:
        raise ValueError('items 需要至少一个商品')
    parts, normalized, detail_cache = [], [], {}
    for item in items:
        allowed = {'productCode', 'quantity', 'roundList'}
        if set(item) - allowed:
            raise ValueError('输入只接受 productCode、quantity、roundList；优惠券由门店查询取得')
        code, qty = str(item['productCode']), item['quantity']
        if type(qty) is not int or not 1 <= qty <= 20:
            raise ValueError('商品数量范围为 1 至 20')
        if code not in detail_cache:
            detail_cache[code] = client.call('query-meal-detail', dict(context(store), code=code))
        detail = detail_cache[code]
        selection = item.get('roundList')
        if selection is None:
            selection = default_item(detail).get('roundList', [])
        groups = {str(g['id']): g for g in detail.get('rounds', [])}
        selected = {}
        for group in selection:
            rid = group['round']
            if not isinstance(rid, str) or rid not in groups or rid in selected:
                raise ValueError('套餐 round 必须为详情中的字符串 ID，且不可重复')
            choices = {str(c['code']): c for c in groups[rid]['choices']}
            children = group['comboItemList']
            seen = set()
            for child in children:
                n, child_code = child['quantity'], str(child['code'])
                if type(n) is not int or n < 1 or child_code not in choices or child_code in seen:
                    raise ValueError('套餐子项编码或数量无效')
                maximum = choices[child_code]['maxQuantity']
                if maximum >= 0 and n > maximum:
                    raise ValueError('套餐子项超过可选数量')
                seen.add(child_code)
            count = sum(c['quantity'] for c in children)
            if not groups[rid]['minQuantity'] <= count <= groups[rid]['maxQuantity']:
                raise ValueError('套餐选择数量不符合详情约束')
            selected[rid] = children
        for rid, group in groups.items():
            if rid not in selected and group['minQuantity'] > 0:
                raise ValueError('缺少套餐必选项')
        clean = {'productCode': code, 'quantity': qty}
        if selection:
            clean['roundList'] = [{'round': rid, 'comboItemList': [
                {'code': str(c['code']), 'quantity': c['quantity']} for c in children]}
                for rid, children in selected.items()]
        normalized.append(clean)
        if groups:
            for rid, children in selected.items():
                choices = {str(c['code']): c for c in groups[rid]['choices']}
                for child in children:
                    parts.append({'code': str(child['code']), 'name': choices[str(child['code'])]['name'],
                                  'quantity': qty * child['quantity']})
        else:
            parts.append({'code': code, 'name': detail['name'], 'quantity': qty})
    return normalized, parts, [detail_cache[str(i['productCode'])]['name'] for i in items]


def price_summary(result, expected_items):
    expected, actual = Counter(), Counter()
    for item in expected_items:
        expected[str(item['productCode'])] += item['quantity']
    for item in result.get('productList', []):
        actual[str(item['productCode'])] += item['quantity']
    if actual != expected:
        raise McdError('计价返回的商品与输入篮子不一致')
    fields = ('price', 'originalPrice', 'discount')
    if any(type(result.get(k)) is not int or result[k] < 0 for k in fields):
        raise ValueError('计价返回金额格式不符合分单位契约')
    applied = result.get('enjoyed') or {}
    return {'payableFen': result['price'], 'originalFen': result['originalPrice'],
            'discountFen': result['discount'], 'applied': applied.get('promotionName', '')}


def quote(client, store, items):
    items, parts, names = validate_basket(client, store, items)
    options, failed = [], []
    try:
        base = client.call('calculate-price', dict(context(store), items=items))
        options.append(dict(price_summary(base, items), method='普通商品报价（含接口自动优惠）'))
    except McdError:
        failed.append('普通商品方案未取得报价')
    # Only the identical product code and identical chosen rounds qualify as same-basket comparison.
    coupons = client.call('query-store-coupons', context(store))
    if len(items) == 1 and items[0]['quantity'] == 1:
        matches = [c for c in coupons if any(str(p['productCode']) == items[0]['productCode']
                                           for p in c.get('products', []))]
        for coupon in matches[:3]:
            candidate = dict(items[0], couponId=coupon['couponId'], couponCode=coupon['couponCode'])
            try:
                result = client.call('calculate-price', dict(context(store), items=[candidate]))
                options.append(dict(price_summary(result, items), method=coupon['title']))
            except McdError:
                failed.append('一张同商品门店券未取得报价')
    if not options:
        raise McdError('该篮子的普通商品与已测试门店券均未取得报价')
    best = min(options, key=lambda o: o['payableFen'])
    return {'storeCode': str(store), 'items': items, 'parts': parts, 'names': names,
            'best': best, 'options': options, 'failedOptions': failed, 'queriedAt': now(),
            'scope': '已测试的报价方案；单品券最多核对3张，多商品使用接口自动优惠'}


def choose(candidates, mode, budget_fen, excluded, eaten, rng=None):
    rng = rng or random.SystemRandom()
    pool = [c for c in candidates if c['best']['payableFen'] <= budget_fen
            and not any(term in p['name'] for term in excluded for p in c['parts'])]
    if not pool:
        raise ValueError('已核价候选中没有符合预算与排除条件的组合')
    if mode == 'save':
        price = min(c['best']['payableFen'] for c in pool)
        pool = [c for c in pool if c['best']['payableFen'] == price]
    elif mode == 'explore':
        scores = [sum(p['code'] not in eaten for p in c['parts']) for c in pool]
        top = max(scores)
        pool = [c for c, score in zip(pool, scores) if score == top]
    elif mode != 'random':
        raise ValueError('未知抽取模式')
    return rng.choice(pool)


def coupon_rows(client):
    result = []
    for page in range(1, 6):
        data = client.call('query-my-coupons', {'page': str(page), 'pageSize': '200'})
        for c in data['coupons']:
            result.append({k: c.get(k, '') for k in ('title', 'tradeStartDate', 'tradeEndDate', 'datetimeText', 'enable')})
        if page >= int(data['totalPages']):
            break
    return result


def calendar_data(campaign, coupons, month):
    year, mon = map(int, month.split('-'))
    days = {f'{month}-{n:02}': {'events': [], 'coupons': [], 'expiring': []}
            for n in range(1, calendar.monthrange(year, mon)[1] + 1)}
    for day in campaign['dailyList']:
        if day['date'] in days:
            days[day['date']]['events'] = [e.get('activityTitle') or (e.get('articleDto') or {}).get('title', '')
                                          for e in day.get('events', [])]
    for c in coupons:
        start, end = c['tradeStartDate'][:10], c['tradeEndDate'][:10]
        for day, values in days.items():
            if start <= day <= end:
                values['coupons'].append(c['title'])
                if day == end:
                    values['expiring'].append(c['title'])
    return days


NUTRIENTS = ('energyKcal', 'protein', 'fat', 'carbohydrate', 'sodium', 'calcium')


def parse_nutrition(text):
    header, body = text.split('\n', 1)
    match = re.fullmatch(r'\[(\d+)\]\{([^}]+)\}:', header.strip())
    if not match:
        raise ValueError('营养表格式不符合已验证的 TOON 表结构')
    fields = match[2].split(',')
    rows = list(csv.reader(io.StringIO(body), skipinitialspace=True))
    if len(rows) != int(match[1]) or any(len(r) != len(fields) for r in rows):
        raise ValueError('营养表条目数或字段数不匹配')
    result = {}
    for values in rows:
        item = dict(zip(fields, values))
        row = {k: float(item[k]) if item[k] != 'null' else None for k in NUTRIENTS}
        result.setdefault(item['productName'], []).append(row)
    return result


def nutrition(parts, table, aliases=None):
    aliases = aliases or {}
    total = dict.fromkeys(NUTRIENTS, 0.0)
    missing, matched = [], []
    for part in parts:
        name = aliases.get(part['name'], part['name'])
        rows = table.get(name, [])
        # Duplicate identical rows occur in the official table; conflicting rows stay unresolved.
        if not rows or any(r != rows[0] for r in rows) or any(v is None for v in rows[0].values()):
            missing.append(part['name'])
            continue
        for key in total:
            total[key] += rows[0][key] * part['quantity']
        matched.append(part['name'])
    names = ' '.join(p['name'] for p in parts)
    pairing = ['搭配一份蔬菜和完整水果，结合今天其他餐选择种类。',
               '当天其他餐可安排全谷物、豆制品或奶类。']
    if any('可乐' in p['name'] and '无糖' not in p['name'] or '雪碧' in p['name'] for p in parts):
        pairing.append('饮料换成水或同杯型无糖饮品，可减少含糖饮料摄入。')
    if '薯条' in names:
        pairing.append('想减少油炸小食，可查看当前套餐的玉米杯替换选项。')
    return {'knownTotal': total, 'matched': matched, 'missing': missing,
            'complete': not missing, 'coverage': f'{len(matched)}/{len(parts)}',
            'pairing': pairing,
            'source': '中国营养学会《中国居民膳食指南（2022）》；MCP 实时营养表'}


def order_preview(data):
    pending = []
    for order in data['list']:
        if order['orderStatus'] != '订单已完成':
            continue
        parts = []
        for product in order['orderProductList']:
            children = product.get('comboItemList')
            if children:
                parts.extend({'code': str(c['productCode']), 'name': c['name'],
                              'quantity': product['quantity'] * c['quantity']} for c in children)
            else:
                parts.append({'code': str(product['productCode']), 'name': product['productName'],
                              'quantity': product['quantity']})
        pending.append({'date': order['createTime'][:10], 'storeCode': order['storeCode'],
                        'storeName': order['storeName'], 'parts': parts})
    return pending


def record(state, kind, code, name, when):
    date.fromisoformat(when)
    group = state['foods' if kind == 'food' else 'stores']
    previous = group.get(code)
    group[code] = {'name': name, 'firstRecorded': min(when, previous['firstRecorded']) if previous else when,
                   'lastRecorded': max(when, previous['lastRecorded']) if previous else when}
    return state
