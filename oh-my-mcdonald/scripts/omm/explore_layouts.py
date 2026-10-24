"""Food gallery and date plaza with labels fixed to scene anchors."""
import calendar
import math
from collections import Counter
from .render import text, wrap, projection_bounds, RED, YELLOW, INK, MUTED
from .scene_layouts import draw_scene, lines
from .scenes import cuboid
from .calendar_focus import focus
from .explore_scenes import compose_gallery, compose_calendar, gallery_sections


def noticeboard(d,sections,y):
    prepared=[]
    height=45
    for section in sections:
        heading={'近期到期':'这些券快到期了','已发布的官方活动':'最近有哪些活动'}.get(section['heading'],section['heading'])
        entries=[value+(f' × {count}' if count>1 else '') for value,count in Counter(section['lines']).items()]
        pairs=[]
        for offset in range(0,len(entries),2):
            pair=[wrap(d,line,22,405) for line in entries[offset:offset+2]]
            rh=max(map(len,pair))*31+26
            pairs.append((pair,rh));height+=rh
        prepared.append((heading,pairs));height+=80
    height=math.ceil(height/8)*8
    # A single freestanding wooden noticeboard holds all notices on one surface.
    geometry=[]
    for i in range(68):
        geometry.append(cuboid((i,-i,10),(1,2,height//8),'#fff1d4' if 2<=i<66 else '#9b632e'))
        geometry.append(cuboid((i,-i,10+height//8),(1,2,2),'#bf813c'))
        geometry.append(cuboid((i,-i,8),(1,2,2),'#9b632e'))
    for i in (5,61):geometry.append(cuboid((i,-i,0),(2,2,8),'#724727'))
    bounds=projection_bounds(geometry);h=(bounds[3]-bounds[1])*8
    draw_scene(d,geometry,{},(40,y,1040,y+h))
    d.rectangle((86,y+23,994,y+height+17),fill='#fff1d4')
    yy=y+42
    for heading,pairs in prepared:
        text(d,(95,yy),heading,28,RED,True);yy+=55
        for pair,rh in pairs:
            for col,values in enumerate(pair):
                x=95+col*460
                for n,line in enumerate(values):text(d,(x,yy+31*n),line,22,INK)
            yy+=rh
        yy+=25
    return y+h+35


def gallery(d,report,y):
    items=report.get('collection',[])
    if items:
        geometry,anchors=compose_gallery(items)
        bounds=projection_bounds(geometry);h=(bounds[3]-bounds[1])*8
        points=draw_scene(d,geometry,anchors,(35,y+10,1045,y+10+h))
        sections=gallery_sections(items)
        ordered=[item for _,values in sections for item in values]
        for (name,_),(x,yy) in zip(sections,points['zones']):
            text(d,(x-100,yy-18),name,28,RED,True)
        for item,(x,yy) in zip(ordered,points['labels']):
            d.rectangle((x-97,yy-32,x+97,yy+48),fill='#fff2d4')
            lines(d,item['name'],x-91,yy-26,182,19,INK,True)
            text(d,(x-91,yy+26),'已点亮' if item['lit'] else '待点亮',16,RED if item['lit'] else MUTED)
        for x,yy in points.get('entrance',[]):
            d.rectangle((x-120,yy-27,x+120,yy+27),fill=RED)
            text(d,(x-84,yy-23),'餐品展馆',32,YELLOW,True)
        y+=h+55
    else:
        text(d,(54,y),'吃过并记下来，图鉴就会亮起来。',26,INK);y+=65
    sections=[section for section in report.get('sections',[])
              if not (section['heading']=='探店足迹' and section['lines']==['还没有确认的探店记录'])]
    return noticeboard(d,sections,y) if sections else y


def focus_board(d,report,y):
    groups=focus(report)
    prepared=[[(line,wrap(d,line,21,280)) for line in group['lines']] for group in groups]
    height=115+max(sum(len(lines)*29+10 for _,lines in entries) for entries in prepared)
    d.rectangle((50,y+10,1030,y+height+10),fill='#8f5d2d')
    d.rectangle((60,y+18,1020,y+height),fill='#fff1d4')
    d.rectangle((50,y,1030,y+12),fill=RED)
    for col,(group,entries) in enumerate(zip(groups,prepared)):
        x=78+col*318
        text(d,(x,y+25),group['title'],27,RED,True)
        text(d,(x,y+65),group['subtitle'],17,MUTED)
        yy=y+104
        for _,lines in entries:
            for line in lines:
                text(d,(x,yy),line,21);yy+=29
            yy+=10
    return y+height+35


def date_plaza(d,report,y):
    if report.get('calendar'):
        y=focus_board(d,report,y)
        year,month=map(int,report['month'].split('-'))
        text(d,(54,y),f'{month} 月优惠街区',30,RED,True)
        text(d,(54,y+45),'整月概览：红框是今天，黄色有券到期。完整优惠见续页。',22,MUTED)
        y+=95
        geometry,anchors=compose_calendar(year,month,report['calendar'])
        bounds=projection_bounds(geometry);h=(bounds[3]-bounds[1])*8
        points=draw_scene(d,geometry,anchors,(30,y+45,1050,y+45+h))
        start,count=calendar.monthrange(year,month)
        # Weekdays align with the projected columns of the continuous plaza.
        for label,(x,yy) in zip('一二三四五六日',points['weekdays']):
            d.rectangle((x-32,yy-16,x+32,yy+20),fill='#fff2d4')
            text(d,(x-10,yy-15),label,23,RED,True)
        for day,(x,yy) in enumerate(points['days'],1):
            value=report['calendar'][f'{year}-{month:02}-{day:02}']
            # Paint a flat readable face inside the voxel sign's frame.
            d.rectangle((x-54,yy-52,x+56,yy+47),fill='#ffe28a' if value['expiring'] else '#fff2d4')
            is_today=f'{year}-{month:02}-{day:02}'==report['generatedAt'][:10]
            if is_today:d.rounded_rectangle((x-55,yy-53,x+57,yy+48),radius=0,outline=RED,width=3)
            text(d,(x-49,yy-47),day,27,RED if value['expiring'] or is_today else INK,True)
            if value['coupons']:text(d,(x-49,yy-7),f"{len(value['coupons'])} 张券",17,INK)
            if value['events']:text(d,(x-49,yy+20),f"{len(value['events'])} 项活动",16,MUTED)
        for x,yy in points.get('entrance',[]):
            d.rectangle((x-120,yy-27,x+120,yy+27),fill=RED)
            text(d,(x-84,yy-23),'优惠街区',32,YELLOW,True)
        y+=h+105
    return noticeboard(d,report.get('sections',[]),y) if report.get('sections') else y
