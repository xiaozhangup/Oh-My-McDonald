"""Function-specific scenes using the original coarse voxel library."""
import calendar
import math
from collections import Counter
import json
from pathlib import Path
from functools import lru_cache
from PIL import Image
from .render import Canvas, ASSETS, RED, YELLOW, PAPER, INK, MUTED, text, wrap, draw_geometry, projection_bounds

SCALE = 8


@lru_cache(maxsize=1)
def library():
    return json.loads((ASSETS/'coarse-models.json').read_text())


def model(draw, name, box, gray=False):
    geometry=library()[name]
    if gray: geometry=[dict(p,color='#b1aa98') for p in geometry]
    if name!='restaurant_kiosk':
        xmin=min(p['origin'][0] for p in geometry);ymin=min(p['origin'][1] for p in geometry)
        xmax=max(p['origin'][0]+p['size'][0] for p in geometry);ymax=max(p['origin'][1]+p['size'][1] for p in geometry)
        geometry=geometry+[{'origin':[xmin-1,ymin-1,-2],'size':[xmax-xmin+2,ymax-ymin+2,2],'color':'#c7bc9f' if gray else YELLOW}]
    left,top,right,bottom=projection_bounds(geometry)
    screen=((box[0]+box[2])/2-(left+right)*SCALE/2,
            (box[1]+box[3])/2-(top+bottom)*SCALE/2)
    draw_geometry(draw,geometry,screen,SCALE)


def label(draw,value,x,y,width,size=24,color=INK,bold=False):
    lines=wrap(draw,value,size,width,bold)
    for i,line in enumerate(lines):text(draw,(x,y+i*(size+8)),line,size,color,bold)
    return y+len(lines)*(size+8)


def panel(draw,box,color='#fffdf5'):
    x,y,r,b=box
    draw.rectangle((x+6,y+6,r+6,b+6),fill='#e3cf9f')
    draw.rectangle(box,fill=color)


def meal_scene(draw,items,y):
    text(draw,(54,y),'这一餐',30,RED,True)
    for i,item in enumerate(items):
        row,col=divmod(i,3);x=54+col*324;yy=y+55+row*290
        # A physical serving plinth connects each model to its actual order label.
        panel(draw,(x,yy+150,x+298,yy+250),'#ffe5a0')
        model(draw,item['model'],(x+15,yy-25,x+283,yy+185))
        label(draw,item['name']+' × '+str(item['quantity']),x+16,yy+195,265,20,bold=True)
    return y+55+((len(items)+2)//3)*700


def render_feature(report,output):
    kind=report['kind'];items=report.get('meal',[])
    height=2500+((len(items)+2)//3)*700+((len(report.get('collection',[]))+2)//3)*450
    height+=sum(100+70*len(wrap(Canvas(Image.new('RGB',(2160,100))),line,23,840)) for section in report.get('sections',[]) for line in section['lines'])
    if report.get('calendar'):
        from .calendar_focus import focus
        measure=Canvas(Image.new('RGB',(2160,100)))
        height+=300+max(sum(10+29*len(wrap(measure,line,21,280)) for line in group['lines']) for group in focus(report))
    image=Image.new('RGB',(2160,height*2),PAPER);d=Canvas(image)
    d.rectangle((0,0,1080,174),fill=RED)
    text(d,(48,20),'OH-MY-MCDONALD',20,YELLOW,True)
    title={'compare':'同一套餐，哪家便宜？','nutrition':'这一餐吃些什么？','album':'我的麦当劳图鉴','calendar':'看看哪天有优惠'}.get(kind,report['title'])
    if kind=='album' and '演示' in report['title']:title+='（演示记录）'
    text(d,(46,56),title,44,'#fff8e8',True)
    text(d,(48,120),report['subtitle'],21,'#ffe5b0')
    y=210
    if kind in ('compare','nutrition'):
        from . import scene_layouts
        y=scene_layouts.street(d,report,y) if kind=='compare' else scene_layouts.nutrition(d,report,y)
    elif kind in ('album','calendar'):
        from . import explore_layouts
        y=explore_layouts.gallery(d,report,y) if kind=='album' else explore_layouts.date_plaza(d,report,y)
    text(d,(54,y+20),'数据时间 '+report['generatedAt'][:19].replace('T',' ')+' 北京时间',18,MUTED)
    h=math.ceil(y+100)
    image=image.crop((0,0,2160,h*2)).resize((1080,h),Image.Resampling.LANCZOS)
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True);image.save(output)
    return str(output.resolve())
