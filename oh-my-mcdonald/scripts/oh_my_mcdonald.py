#!/usr/bin/env python3
"""Run from the repository; no skill installation required."""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

from omm import core
from omm.mcp import Client, McdError
from omm.render import render, model_sheet, wrap, font
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]


def parser():
    p = argparse.ArgumentParser(description='Oh-My-McDonald：对话驱动的体素分享卡')
    p.add_argument('--codex-config', help='显式读取本机 mcd-mcp 配置；默认只读 MCD_MCP_TOKEN')
    p.add_argument('--state', default=str(Path.home()/'.local/share/oh-my-mcdonald/records.json'))
    p.add_argument('--out', default='output', help='图片和公开摘要输出目录')
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('models',help='渲染原创场景和餐品模型总览，不联网')
    stores = sub.add_parser('stores', help='搜索门店；无城市和关键词时查询收藏')
    stores.add_argument('--city')
    stores.add_argument('--keyword')
    menu = sub.add_parser('menu')
    menu.add_argument('--store', required=True)
    menu.add_argument('--contains', default='')
    detail = sub.add_parser('detail')
    detail.add_argument('--store', required=True)
    detail.add_argument('--code', required=True)
    q = sub.add_parser('quote')
    q.add_argument('--store', required=True)
    q.add_argument('--basket', required=True, help='JSON: {"items":[...]}')
    compare = sub.add_parser('compare')
    compare.add_argument('--stores', required=True, nargs='+', help='已搜索确认的2至3个门店编码')
    compare.add_argument('--basket', required=True)
    compare.add_argument('--locations', help='stores 命令输出的 JSON，提供真实门店名称')
    draw = sub.add_parser('draw')
    draw.add_argument('--store', required=True)
    draw.add_argument('--candidates', required=True, help='JSON: {"candidates":[{"items":[...]}]}，最多6组')
    draw.add_argument('--mode', choices=['random','save','explore'], required=True)
    draw.add_argument('--budget', required=True, type=str, help='元')
    draw.add_argument('--exclude', nargs='*', default=[], help='按实际子项名称排除；过敏原由客户端核对官方资料')
    coupons = sub.add_parser('coupons')
    coupons.add_argument('--store', help='同时核对某门店券列表')
    cal = sub.add_parser('calendar')
    cal.add_argument('--month', default=core.now()[:7])
    nut = sub.add_parser('nutrition')
    nut.add_argument('--store', required=True)
    nut.add_argument('--basket', required=True)
    sub.add_parser('import-preview', help='读取近期已完成订单，生成本机待确认列表')
    confirm = sub.add_parser('confirm', help='仅在用户确认后导入指定食用项或门店')
    confirm.add_argument('--pending', required=True)
    confirm.add_argument('--entry', required=True, type=int, help='从0开始的待确认条目')
    confirm.add_argument('--foods', nargs='*', default=[], help='用户确认本人吃过的商品编码')
    confirm.add_argument('--visit', action='store_true', help='用户确认去过这家店')
    rec = sub.add_parser('record')
    rec.add_argument('--kind', choices=['food','store'], required=True)
    rec.add_argument('--code', required=True)
    rec.add_argument('--name', required=True)
    rec.add_argument('--date', required=True)
    remove = sub.add_parser('remove')
    remove.add_argument('--kind', choices=['food','store'], required=True)
    remove.add_argument('--code', required=True)
    album = sub.add_parser('album')
    album.add_argument('--catalog', help='JSON: {"foods":[{"code":"...","name":"..."}]}，为空只展示已记录')
    return p


def section(heading, *lines):
    return {'heading':heading, 'lines':list(lines)}


def report(kind,title,subtitle,sections,**extra):
    return dict(kind=kind,title=title,subtitle=subtitle,sections=sections,generatedAt=core.now(),**extra)


def publish(args, value):
    # Handlers construct these whitelisted display fields; raw MCP responses never reach the renderer.
    out = Path(args.out).expanduser()
    stamp = core.now().replace(':','').replace('+','-')
    stem = out / (args.command + '-' + stamp)
    # Keep share cards short; long coupon inventories and event lists continue on separate images.
    pages=[dict(value,sections=[])]
    if value['kind']=='calendar' and value.get('calendar'):
        pages.append({k:v for k,v in value.items() if k!='calendar'})
        pages[-1]['sections']=[]
    used=0
    measure=ImageDraw.Draw(Image.new('RGB',(1080,100)))
    for section_value in value.get('sections',[]):
        chunk=[]
        for line in section_value['lines']:
            count=len(wrap(measure,line,27,866))
            if used+count>20 and used:
                if chunk:
                    pages[-1]['sections'].append(dict(section_value,lines=chunk));chunk=[]
                pages.append({k:v for k,v in value.items() if k not in ['calendar','hero','collection']})
                pages[-1]['sections']=[]
                used=0
            chunk.append(line);used+=count
        if chunk:pages[-1]['sections'].append(dict(section_value,lines=chunk))
    paths=[]
    for n,page in enumerate(pages):
        if len(pages)>1:page['subtitle']=value['subtitle']+f'（{n+1}/{len(pages)}）'
        path=stem.with_suffix('.png') if n==0 else stem.with_name(stem.name+f'-{n+1}').with_suffix('.png')
        paths.append(render(page,path))
    core.private_write(stem.with_suffix('.json'), value)
    return {'image':paths[0],'pages':paths,'summary':str(stem.with_suffix('.json').resolve())}


def quote_sections(value):
    best = value['best']
    return [section('这一餐', *[f"{p['name']} × {p['quantity']}" for p in value['parts']]),
            section('优惠',f"原价 {core.money(best['originalFen'])}，已减 {core.money(best['discountFen'])}",
                    best['applied'] or best['method'])]


def food_model(name):
    if '热' in name and any(w in name for w in ['咖啡','奶铁','拿铁']):return 'drink_hot_coffee'
    exact = [('巨无霸','burger_big_mac'),('麦辣鸡腿','burger_mcspicy'),('板烧','burger_grilled_chicken'),
             ('麦香鱼','burger_filet_o_fish'),('双层吉士','burger_double_cheese'),('吉士汉堡','burger_cheeseburger'),
             ('猪柳蛋麦满分','muffin_sausage_egg'),('烟肉蛋麦满分','muffin_bacon_egg'),
             ('小薯条','fries_small'),('中薯条','fries_medium'),('大薯条','fries_large'),
             ('无糖可','drink_cola_zero'),('可乐','drink_cola'),('雪碧','drink_sprite'),
             ('冰美式','drink_iced_coffee'),('热美式','drink_hot_coffee'),('奶铁','drink_iced_latte'),
             ('牛奶','drink_milk'),('麦乐鸡4','nuggets_4'),('麦乐鸡5','nuggets_5'),('麦乐鸡10','nuggets_10'),
             ('麦辣鸡翅','chicken_wings_2'),('玉米杯','corn_cup'),('苹果片','apple_slices'),
             ('沙拉','salad_bowl'),('圆筒冰淇淋','icecream_cone'),('麦旋风','mcflurry'),('麦炫风','mcflurry'),
             ('朱古力新地','sundae_chocolate'),('草莓新地','sundae_strawberry'),
             ('菠萝派','apple_pie'),('香芋派','taro_pie'),('薯饼','hashbrown'),('热香饼','pancakes')]
    return next((model for label,model in exact if label in name),'burger')


def run(args, client_factory=Client):
    if args.command=='models':
        directory=Path(args.out);directory.mkdir(parents=True,exist_ok=True)
        paths=[]
        for family in ['world','food']:
            path=directory/(family+'-models.png');model_sheet(path,family);paths.append(str(path.resolve()))
        return {'images':paths}
    state_path = Path(args.state).expanduser()
    state = core.load_state(state_path)
    if args.command in ['record','remove','confirm','album']:
        if args.command == 'record':
            core.record(state,args.kind,args.code,args.name,args.date)
            core.private_write(state_path,state)
            return {'recorded':args.code,'kind':args.kind}
        if args.command == 'remove':
            state['foods' if args.kind=='food' else 'stores'].pop(args.code,None)
            core.private_write(state_path,state)
            return {'removed':args.code}
        if args.command == 'confirm':
            pending = core.read_json(args.pending)['pending']
            if not 0 <= args.entry < len(pending): raise ValueError('待确认条目超出范围')
            entry = pending[args.entry]
            available = {p['code']:p for p in entry['parts']}
            if set(args.foods) - available.keys(): raise ValueError('确认的餐品必须在该条待确认记录中')
            if not args.foods and not args.visit: raise ValueError('请选择用户已确认的食物或探店记录')
            for code in args.foods:
                core.record(state,'food',code,available[code]['name'],entry['date'])
            if args.visit:
                core.record(state,'store',entry['storeCode'],entry['storeName'],entry['date'])
            core.private_write(state_path,state)
            return {'confirmedFoods':len(args.foods),'confirmedVisit':args.visit}
        foods = core.read_json(args.catalog)['foods'] if args.catalog else [dict(code=k,name=v['name']) for k,v in state['foods'].items()]
        cards = [dict(name=f['name'],model=food_model(f['name']),lit=f['code'] in state['foods']) for f in foods]
        pages = []
        for offset in range(0,max(len(cards),1),12):
            value = report('album','我的麦麦探索岛',f"已点亮 {len(state['foods'])} 种餐品，记录 {len(state['stores'])} 家门店",
                           [section('探店足迹',*[v['name'] for v in state['stores'].values()] or ['还没有确认的探店记录'])],
                           collection=cards[offset:offset+12])
            page_args = argparse.Namespace(**vars(args)); page_args.command=f'album-{offset//12+1}'
            pages.append(publish(page_args,value))
        return {'pages':pages}
    client = client_factory(args.codex_config)
    if args.command == 'stores':
        if bool(args.city) != bool(args.keyword): raise ValueError('位置搜索同时需要城市和关键词')
        query = {'beType':1,'searchType':2 if args.city else 1}
        if args.city: query.update(city=args.city,keyword=args.keyword)
        values = client.call('query-nearby-stores',query)
        return {'stores':[{k:s.get(k) for k in ['storeCode','storeName','address','distance']} for s in values],
                'scope':'搜索结果；经纬度为0时仅使用门店列表'}
    if args.command == 'menu':
        menu = client.call('query-meals',core.context(args.store))
        return {'meals':[row for row in core.menu_rows(menu) if args.contains in row['name']]}
    if args.command == 'detail':
        d = client.call('query-meal-detail',dict(core.context(args.store),code=args.code))
        return {'code':d['code'],'name':d['name'],'rounds':[
            {'id':str(g['id']),'min':g['minQuantity'],'max':g['maxQuantity'],'choices':[
                {k:c.get(k) for k in ['code','name','quantity','isDefault','diffPrice']} for c in g['choices']]}
            for g in d.get('rounds',[])], 'defaultItem':core.default_item(d)}
    if args.command == 'quote':
        value = core.quote(client,args.store,core.read_json(args.basket)['items'])
        card = report('quote','这顿麦麦怎么省',f'到店价，门店 {args.store}',quote_sections(value),hero=core.money(value['best']['payableFen']),heroLabel='到店应付')
        return dict(publish(args,card),quote=value)
    if args.command == 'compare':
        stores = list(dict.fromkeys(args.stores))
        if not 2 <= len(stores) <= 3: raise ValueError('每次比较2至3家门店')
        basket = core.read_json(args.basket)['items']
        # Freeze default rounds at the first store so other stores receive the same selection.
        canonical, parts, _ = core.validate_basket(client,stores[0],basket)
        rows, failures = [], []
        locations = {str(s['storeCode']):s for s in core.read_json(args.locations)['stores']} if args.locations else {}
        for store in stores:
            try:
                value = core.quote(client,store,canonical)
                signature = sorted((p['code'],p['quantity']) for p in value['parts'])
                if signature != sorted((p['code'],p['quantity']) for p in parts):
                    raise ValueError('套餐子项不一致')
                rows.append({'storeCode':store,'storeName':locations.get(store,{}).get('storeName','门店 '+store),
                             'payableFen':value['best']['payableFen'],
                             'method':value['best']['applied'] or value['best']['method']})
            except (McdError,ValueError) as exc:
                failures.append({'storeCode':store,'reason':str(exc)})
        if not rows: raise ValueError('这些门店均未取得相同餐品的报价')
        rows.sort(key=lambda r:r['payableFen'])
        lowest = rows[0]['payableFen']
        lines = [f"{r['storeName']}：{core.money(r['payableFen'])}，{r['method']}" for r in rows]
        lines.extend(f"门店 {f['storeCode']}：本次未取得可比报价" for f in failures)
        card = report('compare','去哪家吃更省',f'相同商品、份量与套餐选择，{len(rows)} 家取得报价',
            [section('同一套餐',*[f"{p['name']} × {p['quantity']}" for p in parts]),section('门店报价',*lines)],
            stores=[{k:r[k] for k in ('storeName','payableFen','method')} for r in rows],
            failures=failures,meal=[dict(name=p['name'],quantity=p['quantity'],model=food_model(p['name'])) for p in parts],
            hero=core.money(lowest),heroLabel='本次门店最低价',scope='仅比较所选门店已测试方案，不含交通成本')
        return dict(publish(args,card),stores=rows,failures=failures)
    if args.command == 'draw':
        candidates = core.read_json(args.candidates)['candidates']
        if not 1 <= len(candidates) <= 6: raise ValueError('每次候选组合为1至6组')
        budget = core.yuan_to_fen(args.budget)
        if budget <= 0: raise ValueError('预算需要大于0')
        quotes = [core.quote(client,args.store,c['items']) for c in candidates]
        chosen = core.choose(quotes,args.mode,budget,args.exclude,state['foods'])
        label = {'random':'随便抽','save':'省钱抽','explore':'探索抽'}[args.mode]
        card = report('draw','今天就吃这一套',f'{label}，单人预算 {core.money(budget)}',quote_sections(chosen),
                      hero=core.money(chosen['best']['payableFen']),heroLabel='到店应付')
        return dict(publish(args,card),choice=chosen)
    if args.command == 'coupons':
        coupons = core.coupon_rows(client)
        sections = [section('我的券包',*[f"{c['title']}\n{c['datetimeText']}" for c in coupons] or ['券包暂无返回记录'])]
        offers = []
        if args.store:
            applicable = client.call('query-store-coupons',core.context(args.store))
            sections.append(section('所选门店返回的券',*[c['title']+'：'+c['tradeDateTime'] for c in applicable] or ['暂无可用券记录']))
            offers = [{'title':c['title'],'products':[
                {'productCode':p['productCode'],'productName':p['productName']} for p in c.get('products',[])]}
                for c in applicable]
        return dict(publish(args,report('coupons','我的麦麦券包','有效日期和使用时段',sections,coupons=coupons)),storeOffers=offers)
    if args.command == 'calendar':
        date.fromisoformat(args.month+'-01')
        campaign = client.call('campaign-calendar',{})
        coupons = core.coupon_rows(client)
        days = core.calendar_data(campaign,coupons,args.month)
        events = [f"{day[5:]}：{title}" for day,values in days.items() for title in values['events']]
        expiries = [f"{day[5:]} 到期：{title}" for day,values in days.items() for title in values['expiring']]
        sections = [section('近期到期',*expiries or ['本月暂无返回的到期券']),
                    section('已发布的官方活动',*events or ['本次查询没有返回这个月的活动']),
                    section('图例','黄色格子有券到期。券数按持有券的日期范围统计。')]
        return publish(args,report('calendar','麦麦优惠日历',args.month,sections,calendar=days,month=args.month))
    if args.command == 'nutrition':
        _,parts,_ = core.validate_basket(client,args.store,core.read_json(args.basket)['items'])
        table = core.parse_nutrition(client.call('list-nutrition-foods',{}))
        values = core.nutrition(parts,table,core.read_json(ROOT/'references/nutrition-aliases.json'))
        total = values['knownTotal']
        label = '本餐合计' if values['complete'] else '已匹配部分合计'
        sections = [section('餐品与份量',*[f"{p['name']} × {p['quantity']}" for p in parts]),
                    section(label,f"能量 {total['energyKcal']:g} kcal，蛋白质 {total['protein']:g} g",
                            f"脂肪 {total['fat']:g} g，碳水化合物 {total['carbohydrate']:g} g",
                            f"钠 {total['sodium']:g} mg，钙 {total['calcium']:g} mg",f"数据匹配 {values['coverage']}"),
                    section('这餐之外如何搭配',*values['pairing'])]
        if values['missing']: sections.insert(2,section('未匹配的餐品',*values['missing']))
        return dict(publish(args,report('nutrition','这顿麦麦怎么搭配','标准份量营养估算',sections,source=values['source'],
            nutrition=total,complete=values['complete'],coverage=values['coverage'],
            meal=[dict(name=p['name'],quantity=p['quantity'],model=food_model(p['name'])) for p in parts])),nutrition=values)
    if args.command == 'import-preview':
        pending = core.order_preview(client.call('order-list',{}))
        output = Path(args.out)/'pending-orders.json'
        core.private_write(output,{'pending':pending,'queriedAt':core.now()})
        return {'pendingFile':str(output.resolve()),'entries':pending,'scope':'近期返回的购买记录，确认后才点亮'}
    raise ValueError('未知命令')


def main():
    args = parser().parse_args()
    try:
        result = run(args)
    except (McdError,ValueError,KeyError,OSError,json.JSONDecodeError) as exc:
        # Transport errors are sanitized in mcp.py; never dump raw response bodies or local config.
        if isinstance(exc,(KeyError,OSError)):
            message = '输入文件、配置或返回字段不符合预期，请检查本机输入与接口版本'
        else:
            message = str(exc)
        print(json.dumps({'error':message},ensure_ascii=False),file=sys.stderr)
        return 1
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
