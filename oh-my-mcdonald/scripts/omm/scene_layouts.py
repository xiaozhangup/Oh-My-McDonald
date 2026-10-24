"""Street prices and meal nutrition attached to continuous voxel scenes."""
from .render import text, wrap, project, projection_bounds, draw_geometry, RED, YELLOW, INK, MUTED
from .scenes import compose_street, compose_table

SCALE=8


def draw_scene(d, geometry, anchors, box):
    left,top,right,bottom=projection_bounds(geometry)
    screen=((box[0]+box[2])/2-(left+right)*SCALE/2,
            (box[1]+box[3])/2-(top+bottom)*SCALE/2)
    draw_geometry(d,geometry,screen,SCALE)
    return {key:[(screen[0]+project(*p)[0]*SCALE,screen[1]+project(*p)[1]*SCALE) for p in points] for key,points in anchors.items()}


def lines(d,value,x,y,width,size=23,color=INK,bold=False):
    for i,line in enumerate(wrap(d,value,size,width,bold)):text(d,(x,y+i*(size+8)),line,size,color,bold)


def table(d,items,y,right=1020):
    geometry,anchors=compose_table([item['model'] for item in items])
    bounds=projection_bounds(geometry)
    height=(bounds[3]-bounds[1])*SCALE
    draw_scene(d,geometry,anchors,(40,y,right,y+height))
    y+=height+16
    width=(right-64)/max(len(items),1)
    for i,item in enumerate(items):
        lines(d,item['name']+((' × '+str(item['quantity'])) if item.get('quantity') else ''),54+i*width,y,width-4,20,bold=True)
    return y+85


def street(d,report,y):
    stores=report['stores'];low=min(s['payableFen'] for s in stores)
    geometry,anchors=compose_street(len(stores))
    bounds=projection_bounds(geometry);h=(bounds[3]-bounds[1])*SCALE
    points=draw_scene(d,geometry,anchors,(30,y+40,1050,y+40+h))
    for i,store in enumerate(stores):
        x,py=points['prices'][i]
        # Camera-facing hanging signs keep the price legible at the store entrance.
        d.rectangle((x-109,py-40,x+109,py+41),fill='#93271c')
        d.rectangle((x-103,py-34,x+103,py+35),fill=YELLOW if store['payableFen']==low else '#fff3d6')
        text(d,(x-91,py-31),f"¥{store['payableFen']/100:.2f}",39,RED,True)
        name=store['storeName'].removeprefix('麦当劳').removesuffix('餐厅')
        nx,ny=points['names'][i]
        d.rectangle((nx-140,ny-4,nx+140,ny+92),fill='#fff4d8')
        lines(d,name,nx-126,ny,252,21,bold=True)
        cheaper='最低价' if i==0 else '同样最低'
        detail=cheaper if store['payableFen']==low else f"贵 {(store['payableFen']-low)/100:.2f} 元"
        text(d,(nx-126,ny+58),detail,20,RED,True)
    y+=h+180
    for i,store in enumerate(stores):
        text(d,(54+i*324,y),store['method'],18,MUTED)
    y+=65
    text(d,(54,y),'比的是这一餐',30,RED,True);y+=50
    items=report['meal']
    for offset in range(0,len(items),3):y=table(d,items[offset:offset+3],y)
    for failure in report.get('failures',[]):
        lines(d,failure['storeCode']+'：本次未取得可比报价',54,y,970);y+=45
    return y


def nutrition(d,report,y):
    items=report['meal'];totals=report['nutrition']
    text(d,(54,y),'这一餐',30,RED,True);y+=55
    top=y
    for offset in range(0,len(items),3):y=table(d,items[offset:offset+3],y,right=716)
    # One receipt sits beside the meal; values refer only to the ordered food.
    x=744
    d.rectangle((x+6,top+6,1032,top+556),fill='#d9c9a6')
    d.rectangle((x,top,1026,top+550),fill='#fffdf8')
    title='这份套餐的营养' if report['complete'] else '已匹配餐品的营养'
    text(d,(x+18,top+18),title,23,RED,True)
    text(d,(x+18,top+66),f"{totals['energyKcal']:g}",48,RED,True)
    text(d,(x+168,top+91),'kcal',23,MUTED)
    metrics=[('蛋白质','protein','g'),('脂肪','fat','g'),('碳水化合物','carbohydrate','g'),('钠','sodium','mg'),('钙','calcium','mg')]
    for i,(name,key,unit) in enumerate(metrics):
        yy=top+147+i*65
        d.rectangle((x+18,yy-10,1005,yy-8),fill='#e9dfc8')
        text(d,(x+18,yy),name,21)
        text(d,(x+155,yy),f"{totals[key]:g} {unit}",21,RED,True)
    text(d,(x+18,top+495),'数据匹配 '+report['coverage'],18,MUTED)
    y=max(y,top+590)
    text(d,(54,y),'还可以搭配这些',30,RED,True);y+=48
    text(d,(54,y),'放在其他餐里搭配着吃',22,MUTED);y+=40
    extras=[dict(model='salad_bowl',name='蔬菜'),dict(model='apple_slices',name='水果'),dict(model='drink_milk',name='奶类或豆制品')]
    y=table(d,extras,y)
    text(d,(54,y),'本餐之外的搭配，未计入上面的营养合计',20,MUTED);y+=50
    for sec in report.get('sections',[]):
        if sec['heading']=='未匹配的餐品':
            lines(d,'未匹配：'+'、'.join(sec['lines']),54,y,970);y+=60
    return y
