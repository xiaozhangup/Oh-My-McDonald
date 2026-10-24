"""PNG share cards, rendered from original cuboid geometry on the local machine."""
import calendar
import json
import math
import os
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np

ASSETS = Path(__file__).resolve().parents[2] / 'assets'
INK, MUTED, PAPER = '#292622', '#746e62', '#fff8e8'
RED, YELLOW = '#da291c', '#ffc72c'
VOXEL_PIXELS = 4


class Canvas:
    """Draw at twice the final resolution for clean model edges and Chinese type."""
    def __init__(self,image):
        self.image=image
        self.draw=ImageDraw.Draw(image)

    def polygon(self,points,**kwargs):
        self.draw.polygon([(x*2,y*2) for x,y in points],**kwargs)

    def rectangle(self,box,**kwargs):
        self.draw.rectangle(tuple(n*2 for n in box),**kwargs)

    def rounded_rectangle(self,box,radius=0,**kwargs):
        if 'width' in kwargs:kwargs['width']*=2
        self.draw.rounded_rectangle(tuple(n*2 for n in box),radius=radius*2,**kwargs)

    def text(self,xy,value,font,**kwargs):
        self.draw.text((xy[0]*2,xy[1]*2),value,font=font.font_variant(size=font.size*2),**kwargs)

    def textlength(self,value,font):
        return self.draw.textlength(value,font=font)


@lru_cache(maxsize=32)
def font(size, bold=False):
    supplied = os.environ.get('OMM_FONT')
    weight = 'Bold' if bold else 'Regular'
    candidates = [supplied] if supplied else [
        f'/usr/share/fonts/google-noto-sans-cjk-fonts/NotoSansCJK-{weight}.ttc',
        f'/usr/share/fonts/opentype/noto/NotoSansCJK-{weight}.ttc',
        '/System/Library/Fonts/PingFang.ttc', 'C:/Windows/Fonts/msyh.ttc']
    for path in candidates:
        if path and Path(path).is_file():
            return ImageFont.truetype(path, size)
    raise ValueError('找不到中文字体，请将 OMM_FONT 指向 Noto Sans CJK 等中文字体文件')


@lru_cache(maxsize=1)
def models():
    result = json.loads((ASSETS/'models.json').read_text())
    foods = ASSETS/'food-models.json'
    if foods.exists():
        result.update(json.loads(foods.read_text()))
    return result


def shade(color, ratio):
    rgb = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))
    return tuple(min(255, round(c * ratio)) for c in rgb)


def project(x,y,z):
    return ((x-y)*.8660254, (x+y)*.5-z)


def geometry_faces(geometry):
    faces=[]
    for part in geometry:
        x,y,z=part['origin'];w,d,h=part['size']
        surfaces=[([(x+w,y,z),(x+w,y+d,z),(x+w,y+d,z+h),(x+w,y,z+h)],.77),
                  ([(x,y+d,z),(x+w,y+d,z),(x+w,y+d,z+h),(x,y+d,z+h)],.92),
                  ([(x,y,z+h),(x+w,y,z+h),(x+w,y+d,z+h),(x,y+d,z+h)],1.07)]
        for vertices,light in surfaces:
            faces.append(([project(*v) for v in vertices],[sum(v) for v in vertices],shade(part['color'],light)))
    return faces


def draw_geometry(draw,geometry,screen,scale):
    """Orthographic z-buffer: thin signage and window trim remain in front of their walls."""
    faces=geometry_faces(geometry)
    points=[((screen[0]+x*scale)*2,(screen[1]+y*scale)*2) for vertices,_,_ in faces for x,y in vertices]
    image=draw.image
    left=max(0,math.floor(min(x for x,y in points)))
    top=max(0,math.floor(min(y for x,y in points)))
    right=min(image.width,math.ceil(max(x for x,y in points))+1)
    bottom=min(image.height,math.ceil(max(y for x,y in points))+1)
    pixels=np.array(image.crop((left,top,right,bottom)))
    depth_buffer=np.full((bottom-top,right-left),-np.inf,dtype=np.float64)
    for vertices,depths,color in faces:
        vertices=[((screen[0]+x*scale)*2-left,(screen[1]+y*scale)*2-top) for x,y in vertices]
        x0,y0=vertices[0];ux,uy=vertices[1][0]-x0,vertices[1][1]-y0
        vx,vy=vertices[3][0]-x0,vertices[3][1]-y0
        determinant=ux*vy-uy*vx
        xmin=max(0,math.floor(min(x for x,y in vertices)))
        xmax=min(right-left,math.ceil(max(x for x,y in vertices)))
        ymin=max(0,math.floor(min(y for x,y in vertices)))
        ymax=min(bottom-top,math.ceil(max(y for x,y in vertices)))
        if xmin>=xmax or ymin>=ymax:
            continue
        yy,xx=np.ogrid[ymin:ymax,xmin:xmax]
        dx,dy=xx+.5-x0,yy+.5-y0
        u=(dx*vy-dy*vx)/determinant
        v=(ux*dy-uy*dx)/determinant
        mask=(u>=0)&(u<=1)&(v>=0)&(v<=1)
        depth=depths[0]+u*(depths[1]-depths[0])+v*(depths[3]-depths[0])
        region=depth_buffer[ymin:ymax,xmin:xmax]
        visible=mask&(depth>region)
        region[visible]=depth[visible]
        pixels[ymin:ymax,xmin:xmax][visible]=color
    image.paste(Image.fromarray(pixels),(left,top))


def moved(name,position=(0,0,0),gray=False):
    return [{'origin':[position[k]+part['origin'][k] for k in range(3)],
             'size':part['size'],
             'color':'#ada99f' if gray else part['color']} for part in models()[name]]


def projection_bounds(geometry):
    points=[]
    for part in geometry:
        origin=part['origin'];size=part['size']
        for dx in (0,size[0]):
            for dy in (0,size[1]):
                for dz in (0,size[2]):
                    points.append(project(origin[0]+dx,origin[1]+dy,origin[2]+dz))
    left,top=min(p[0] for p in points),min(p[1] for p in points)
    right,bottom=max(p[0] for p in points),max(p[1] for p in points)
    return left,top,right,bottom


def placement(geometry,rect,grounded=False):
    if grounded:
        # Center the footprint, with z=0 on a common baseline. Small objects stay small.
        center=[(min(p['origin'][k] for p in geometry)+
                 max(p['origin'][k]+p['size'][k] for p in geometry))/2 for k in (0,1)]
        x,y=project(*center,0)
        return ((rect[0]+rect[2])/2-x*VOXEL_PIXELS,rect[1]+235-y*VOXEL_PIXELS)
    left,top,right,bottom=projection_bounds(geometry)
    return ((rect[0]+rect[2])/2-(left+right)*VOXEL_PIXELS/2,
            (rect[1]+rect[3])/2-(top+bottom)*VOXEL_PIXELS/2)


def place_geometry(draw,geometry,rect,grounded=False):
    draw_geometry(draw,geometry,placement(geometry,rect,grounded),VOXEL_PIXELS)


def scene(draw,kind,rect):
    # Compact vignettes share the same integer grid and projection scale.
    layouts={
        'album':[('chest',(0,18,0)),('burger_big_mac',(12,0,0))],
        'calendar':[('calendar',(0,0,0)),('coupon_kiosk',(26,8,0))],
        'compare':[('drive_thru_menu',(0,0,0)),('drive_thru_menu',(28,0,0)),
                   ('traffic_cone',(18,18,0))],
        'nutrition':[('salad_bowl',(0,0,0)),('apple_slices',(25,0,0))],
    }
    objects=layouts.get(kind,[('burger_big_mac',(0,0,0))])
    geometry=[]
    for name,origin in objects:
        geometry.extend(moved(name,origin))
    place_geometry(draw,geometry,rect)


def wrap(draw,value,size,width,bold=False):
    value=display_text(value)
    f=font(size,bold)
    lines=[]
    for paragraph in str(value).split('\n'):
        line=''
        for char in paragraph:
            if draw.textlength(line+char,font=f)>width and line:
                lines.append(line);line=char
            else:
                line+=char
        lines.append(line)
    return lines


def text(draw,xy,value,size=28,color=INK,bold=False):
    draw.text(xy,display_text(value),font=font(size,bold),fill=color)


def display_text(value):
    return re.sub(r'[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\u200D]', '', str(value))


def render(report,output):
    if report['kind'] in ('album','calendar') or (report['kind']=='compare' and 'stores' in report) or (report['kind']=='nutrition' and 'nutrition' in report):
        from .feature_render import render_feature
        return render_feature(report,output)
    scratch=ImageDraw.Draw(Image.new('RGB',(1080,100)))
    prepared=[]
    sections=report.get('sections',[])
    if report['kind']=='nutrition':
        sections=sorted(sections,key=lambda section: section['heading']!='本餐合计')
    for section in sections:
        lines=[]
        entries=section['lines']
        if section['heading'] in ['我的券包','所选门店返回的券','近期到期','已发布的官方活动']:
            entries=[item+(f' × {count}' if count>1 else '') for item,count in Counter(entries).items()]
        for item in entries:
            lines.extend(wrap(scratch,item,27,866))
        prepared.append((section['heading'],lines))
    content_height=sum(110+43*len(lines) for _,lines in prepared)
    calendar_height=594 if report.get('calendar') else 0
    collection_height=430*((len(report.get('collection',[]))+2)//3)
    height=454+(150 if report.get('hero') else 0)+content_height+calendar_height+collection_height
    image=Image.new('RGB',(2160,height*2),PAPER)
    draw=Canvas(image)
    draw.rectangle((0,0,1080,320),fill=RED)
    # Keep the function title beside its compact scene.
    text(draw,(59,30),'OH-MY-MCDONALD',25,YELLOW,True)
    for n,line in enumerate(wrap(draw,report['title'],46,640,True)):
        text(draw,(58,81+70*n),line,46,'#fff9e7',True)
    for n,line in enumerate(wrap(draw,report['subtitle'],24,600)):
        text(draw,(61,166+n*34),line,24,'#ffe5b0')
    scene(draw,report['kind'],(710,28,1050,286))
    draw.rectangle((0,308,1080,320),fill=YELLOW)
    for x in range(0,1080,54):
        draw.polygon([(x,308),(x+16,308),(x+28,320),(x+12,320)],fill='#f3ae16')
    y=350
    if report.get('hero'):
        draw.rounded_rectangle((54,y,1026,y+122),radius=13,fill=YELLOW)
        text(draw,(82,y+11),report.get('heroLabel','到店应付'),19,'#7d4b10',True)
        text(draw,(80,y+38),report['hero'],45,RED,True)
        y+=150
    if report.get('calendar'):
        data=report['calendar'];month=report['month'];year,mon=map(int,month.split('-'))
        start,count=calendar.monthrange(year,mon)
        for col,label in enumerate('一二三四五六日'):
            text(draw,(83+col*136,y),label,23,RED,True)
        y+=45
        for day in range(1,count+1):
            row,col=divmod(start+day-1,7);x,yy=64+col*136,y+row*84
            values=data[f'{month}-{day:02}']
            color=YELLOW if values['expiring'] else '#f2e7d1'
            draw.rounded_rectangle((x,yy,x+124,yy+74),radius=7,fill=color)
            text(draw,(x+10,yy+1),day,25,RED if values['expiring'] else INK,True)
            labels=[]
            if values['coupons']:labels.append(f"{len(values['coupons'])}张券")
            if values['events']:labels.append(f"{len(values['events'])}活动")
            text(draw,(x+6,yy+42),' '.join(labels),14,MUTED)
        y+=549
    for index,(heading,lines) in enumerate(prepared):
        bh=88+43*len(lines)
        draw.rounded_rectangle((54,y,1026,y+bh),radius=12,fill='#fffdf7',outline='#efdfc3',width=2)
        text(draw,(80,y+17),heading,30,RED,True)
        for n,line in enumerate(lines):
            text(draw,(80,y+73+43*n),line,27)
        y+=bh+22
    for idx,item in enumerate(report.get('collection',[])):
        row,col=divmod(idx,3);x,yy=54+col*324,y+row*430
        draw.rounded_rectangle((x,yy,x+306,yy+416),radius=10,fill='#fffdf7',outline='#ebd9b7',width=2)
        name=item['model']
        if name not in models(): name='burger'
        place_geometry(draw,moved(name,gray=not item['lit']),(x+13,yy+12,x+293,yy+322),grounded=True)
        for n,line in enumerate(wrap(draw,item['name'],22,278,True)[:2]):
            text(draw,(x+14,yy+321+n*28),line,22,INK,True)
        draw.rounded_rectangle((x+12,yy+384,x+294,yy+407),radius=4,fill=YELLOW if item['lit'] else '#e7e4db')
        text(draw,(x+24,yy+383),'已点亮' if item['lit'] else '等待探索',15,RED if item['lit'] else MUTED)
    if report.get('collection'):y+=collection_height
    text(draw,(59,y+14),'数据时间 '+report['generatedAt'][:19].replace('T',' ')+' 北京时间',18,MUTED)
    image=image.crop((0,0,2160,(y+100)*2)).resize((1080,y+100),Image.Resampling.LANCZOS)
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    image.save(output,format='PNG')
    return str(output.resolve())


def model_sheet(output,family='all'):
    """Contact sheet of the original model library for visual review."""
    library=models()
    food_labels=json.loads((ASSETS/'food-labels.json').read_text())
    labels={'restaurant':'麦麦餐厅','golden_arches':'金拱门招牌','terrace_umbrella':'露台遮阳伞',
            'terrace_table':'露台餐桌','chair':'露台椅','bench':'长椅','coupon_kiosk':'优惠站',
            'calendar':'优惠日历牌','street_lamp':'路灯','planter':'花盆','garden':'花坛','tree':'树木',
            'road_tile':'道路','crosswalk':'斑马线','sidewalk_tile':'人行道','parking_tile':'停车位',
            'mailbox':'邮箱','chest':'奖励箱','trash_bin':'垃圾桶','drive_thru_menu':'得来速菜单',
            'bollard':'防撞柱','traffic_cone':'路锥','bike_rack':'自行车架','fence':'围栏'}
    if family=='food':labels=food_labels
    elif family=='all':labels.update(food_labels)
    entries=[(name,library[name]) for name in labels]
    cols,cellw,cellh=(6,306,410) if family=='food' else (3,420,460)
    rows=math.ceil(len(entries)/cols)
    image=Image.new('RGB',(cols*cellw*2,(rows*cellh+140)*2),PAPER);draw=Canvas(image)
    draw.rectangle((0,0,cols*cellw,105),fill=RED)
    text(draw,(35,21),'OH-MY-MCDONALD / 原创体素模型',34,YELLOW,True)
    for i,(name,geometry) in enumerate(entries):
        row,col=divmod(i,cols);x,y=col*cellw,row*cellh+120
        draw.rounded_rectangle((x+8,y+4,x+cellw-8,y+cellh-8),radius=8,fill='#fffdf7')
        if family=='food':
            place_geometry(draw,geometry,(x+13,y+12,x+293,y+322),grounded=True)
        else:
            place_geometry(draw,geometry,(x+15,y+15,x+cellw-15,y+cellh-65))
        for n,line in enumerate(wrap(draw,labels[name],21,cellw-35,True)[:2]):
            text(draw,(x+17,y+cellh-55+n*25),line,21,RED,True)
    image=image.resize((cols*cellw,rows*cellh+140),Image.Resampling.LANCZOS)
    Path(output).parent.mkdir(parents=True,exist_ok=True);image.save(output)
