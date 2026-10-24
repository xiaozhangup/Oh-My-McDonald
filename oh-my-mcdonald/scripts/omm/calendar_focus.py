"""Date-based calendar highlights; full records remain in the detail pages."""
from datetime import date, timedelta
from collections import Counter


def counted(values):
    return [name+(f' × {count}' if count>1 else '') for name,count in Counter(values).items()]


def focus(report):
    reference=date.fromisoformat(report['generatedAt'][:10])
    days=report['calendar']
    today=days.get(reference.isoformat(),{'coupons':[],'events':[],'expiring':[]})
    upcoming=[(key,value) for key,value in sorted(days.items()) if reference<=date.fromisoformat(key)<=reference+timedelta(days=7)]
    expiring=next(((key,value['expiring']) for key,value in upcoming if value['expiring']),None)
    events=[f"{key[5:]} {name}" for key,value in upcoming for name in counted(value['events'])]
    # A past month still has its monthly overview and complete details.
    return [dict(title=f"今天可用 {len(today['coupons'])} 张" if reference.isoformat() in days else "今天可用券",subtitle=reference.strftime('%m/%d')+' 按有效日期统计',lines=(counted(today['coupons']) or ['今天没有返回有效券']) if reference.isoformat() in days else ['所选月份不含今天']),
            dict(title='最近到期',subtitle=(expiring[0][5:]+' 到期 '+str(len(expiring[1]))+' 张') if expiring else '未来 7 天',lines=counted(expiring[1]) if expiring else ['没有返回到期券']),
            dict(title='最近活动',subtitle='今天起 7 天内已发布的活动',lines=events[:4]+([f'另有 {len(events)-4} 条，详见续页'] if len(events)>4 else []) or ['没有返回近期活动'])]
