"""Continuous gallery walks and a calendar plaza at eight pixels per voxel."""
import calendar
from .scenes import bounds, cuboid, library, normalize, translated

RED = '#DA291C'
YELLOW = '#FFC72C'
CREAM = '#FFF2D4'
STONE = '#C4B598'
INK = '#5B4231'


def merged_geometry(cells):
    """Merge occupied cells without changing their material or position."""
    remaining = cells.copy()
    result = []
    for x, y, z in sorted(cells, key=lambda p: (p[2], p[1], p[0])):
        if (x, y, z) not in remaining:
            continue
        color = remaining[x, y, z]
        width = 1
        while remaining.get((x + width, y, z)) == color:
            width += 1
        depth = 1
        while all(remaining.get((xx, y + depth, z)) == color
                  for xx in range(x, x + width)):
            depth += 1
        height = 1
        while all(remaining.get((xx, yy, z + height)) == color
                  for yy in range(y, y + depth)
                  for xx in range(x, x + width)):
            height += 1
        result.append(cuboid((x, y, z), (width, depth, height), color))
        for zz in range(z, z + height):
            for yy in range(y, y + depth):
                for xx in range(x, x + width):
                    del remaining[xx, yy, zz]
    return result


def fill(cells, origin, size, color):
    x, y, z = origin
    width, depth, height = size
    for zz in range(z, z + height):
        for yy in range(y, y + depth):
            for xx in range(x, x + width):
                cells[xx, yy, zz] = color


def diagonal_floor(cells, minimum_s, maximum_s, half_width):
    """One connected public floor, clipped in sum/difference coordinates."""
    low = (minimum_s - half_width) // 2 - 2
    high = (maximum_s + half_width) // 2 + 2
    for y in range(low, high):
        for x in range(low, high):
            total, across = x + y, x - y
            if minimum_s <= total < maximum_s and -half_width < across < half_width:
                cells[x, y, 0] = '#C59539'
                edge = abs(across) >= half_width - 2 or total in (minimum_s, maximum_s - 1)
                cells[x, y, 1] = YELLOW if edge else '#E8DDC6'
                if not edge and (total - minimum_s) % 16 == 0:
                    cells[x, y, 1] = STONE


def diagonal_band(cells, minimum_s, maximum_s, half_width, bottom, height, color):
    low = (minimum_s - half_width) // 2 - 2
    high = (maximum_s + half_width) // 2 + 2
    for y in range(low, high):
        for x in range(low, high):
            if minimum_s <= x + y < maximum_s and -half_width < x - y < half_width:
                fill(cells, (x, y, bottom), (1, 1, height), color)


def center(total, across):
    return (total + across) // 2, (total - across) // 2


def planter(cells, total, across):
    x, y = center(total, across)
    fill(cells, (x - 3, y - 2, 2), (6, 4, 3), CREAM)
    fill(cells, (x - 3, y - 2, 3), (6, 4, 1), RED)
    fill(cells, (x - 2, y - 1, 5), (4, 2, 3), '#47664A')
    fill(cells, (x - 1, y - 1, 8), (2, 2, 1), '#79915D')


def lamp(cells, total, across):
    x, y = center(total, across)
    fill(cells, (x - 1, y - 1, 2), (3, 3, 1), STONE)
    fill(cells, (x, y, 3), (1, 1, 18), '#373D38')
    fill(cells, (x - 2, y, 21), (3, 1, 1), '#373D38')
    fill(cells, (x - 2, y - 1, 20), (2, 3, 1), YELLOW)


def bench(cells, total, across):
    x, y = center(total, across)
    for xx in (x - 4, x + 3):
        for yy in (y - 1, y + 1):
            fill(cells, (xx, yy, 2), (1, 1, 3), '#373D38')
    fill(cells, (x - 5, y - 2, 5), (10, 4, 1), '#A66F3F')
    for xx in (x - 5, x + 4):
        fill(cells, (xx, y - 2, 6), (1, 1, 3), '#373D38')
    fill(cells, (x - 4, y - 2, 7), (8, 1, 2), RED)


def guide(cells, total, across):
    x, y = center(total, across)
    fill(cells, (x - 4, y - 3, 2), (8, 6, 1), STONE)
    fill(cells, (x - 3, y - 2, 3), (6, 4, 5), RED)
    fill(cells, (x - 4, y - 3, 8), (8, 6, 1), '#373D38')
    fill(cells, (x - 3, y - 2, 9), (6, 4, 1), CREAM)
    fill(cells, (x - 1, y - 1, 10), (2, 2, 1), YELLOW)
    fill(cells, (x - 2, y + 1, 4), (4, 1, 3), CREAM)
    fill(cells, (x - 1, y + 1, 5), (2, 1, 1), YELLOW)


def entrance_gate(cells, total):
    x, y = center(total, 0)
    for step in (-11, 10):
        px, py = x + step, y - step
        fill(cells, (px - 1, py - 1, 2), (4, 4, 1), STONE)
        fill(cells, (px, py, 3), (2, 2, 18), RED)
        fill(cells, (px, py, 8), (2, 2, 1), YELLOW)
    for step in range(-12, 13):
        px, py = x + step, y - step
        fill(cells, (px, py, 21), (1, 2, 9), RED)
        if -9 <= step <= 9:
            fill(cells, (px, py, 22), (1, 2, 7), CREAM)
        fill(cells, (px, py, 30), (1, 2, 1), YELLOW)
    return x, y + 1, 25


def local_label(cells, total, across):
    x, y = center(total, across)
    for step in range(-9, 10):
        px, py = x + step, y - step
        fill(cells, (px, py, 2), (1, 2, 14), RED)
        fill(cells, (px, py, 3), (1, 2, 12), CREAM)
        fill(cells, (px, py, 16), (1, 2, 1), YELLOW)
    return x, y + 1, 10


def gallery_sections(items):
    groups=[('汉堡与主食',[]),('薯条与小食',[]),('饮品与甜点',[])]
    for item in items:
        key=item['model']
        index=0 if key.startswith(('burger','muffin','pancakes')) else (1 if key.startswith(('fries','nuggets','chicken','corn','hashbrown')) else 2)
        groups[index][1].append(item)
    return [(name,values[start:start+4]) for name,values in groups for start in range(0,len(values),4)]


def compose_gallery(items):
    """Compact themed bays linked by a continuous turning path."""
    sections=gallery_sections(items)
    rows=len(sections)
    last=80+100*max(0,rows-1)
    entry=last+94
    cells={}
    diagonal_floor(cells,16,entry+24,70)
    # Horizontal lanes join alternately on opposite sides of each exhibition bay.
    for point in list(cells):
        x,y,z=point
        if z!=1:continue
        total,across=x+y,x-y
        lane=False
        for row in range(rows):
            front=80+100*row+58
            lane|=abs(total-front)<=6
            if row<rows-1:
                side=65 if row%2==0 else -65
                lane|=(front<=total<=front+100 and abs(across-side)<=4)
        lane|=(last+58<=total and abs(across)<=8)
        if lane:cells[point]='#A66F44' if total%12==0 else '#C28B59'
        elif any(abs(total-(80+100*row))<31 for row in range(rows)):
            row=min(rows-1,max(0,(total-49)//100))
            cells[point]=['#F6E3B6','#ECE4CA','#E1E8D5'][row%3]
    anchors={'labels':[],'entrance':[],'zones':[],'path':[]}
    objects=[]
    for row,(name,values) in enumerate(sections):
        total=80+100*row
        anchors['zones'].append((*center(total-52,0),2))
        for column,item in enumerate(values):
            across=-48+32*column
            x,y=center(total,across)
            fill(cells,(x-7,y-7,2),(15,15,2),'#AD3928')
            fill(cells,(x-7,y-7,4),(15,15,1),YELLOW)
            fill(cells,(x-6,y-6,4),(13,13,1),'#FFF1D5')
            model=library()[item['model']]
            low,high=bounds(model)
            if not item['lit']:model=[dict(part,color='#AAA493') for part in model]
            objects.extend(translated(model,(x-(high[0]-low[0])//2-low[0],y-(high[1]-low[1])//2-low[1],5-low[2])))
            lx,ly=center(total+36,across)
            for step in range(-7,8):
                fill(cells,(lx+step,ly-step,2),(1,2,12),RED)
                fill(cells,(lx+step,ly-step,3),(1,2,10),CREAM)
                fill(cells,(lx+step,ly-step,14),(1,2,1),YELLOW)
            anchors['labels'].append((lx,ly+1,9))
        anchors['path'].append((*center(total+58,0),2))
        if row<rows-1:
            side=65 if row%2==0 else -65
            anchors['path'].append((*center(total+108,side),2))
        planter(cells,total+75,-40 if row%2==0 else 40)
    guide(cells,entry-10,-46)
    bench(cells,entry-10,48)
    lamp(cells,entry,-64);lamp(cells,entry,64)
    anchors['entrance'].append(entrance_gate(cells,entry))
    return normalize(merged_geometry(cells)+objects,anchors)


def compose_calendar(year, month, days):
    """Seven aligned date streets with weekly roads and a foreground plaza.

    Columns retain the (10, -10) step. Weeks advance by (22, 22), or 176 px.
    Date/weekday anchors are ordered lists; entrance contains one gate point.
    """
    start, count = calendar.monthrange(year, month)
    rows = (start + count + 6) // 7
    last = 80 + 44 * (rows - 1)
    entry = last + 62
    cells = {}
    diagonal_floor(cells, 8, entry + 28, 70)
    for point in list(cells):
        x, y, z = point
        total, across = x + y, x - y
        if z != 1:
            continue
        for row in range(rows):
            offset = total - (80 + row * 44)
            if 18 <= offset <= 26:
                cells[point] = '#AD774E' if offset in (18, 26) else '#5D5141'
        if total >= last + 30 and abs(across) < 18:
            cells[point] = '#87553A' if total % 10 == 0 else '#B87D52'
    anchors = {'days': [], 'weekdays': [], 'entrance': []}
    for column in range(7):
        x, y = center(30, -60 + 20 * column)
        for step in range(-3, 4):
            fill(cells, (x + step, y - step, 6), (1, 2, 6), RED)
            fill(cells, (x + step, y - step, 7), (1, 2, 4), CREAM)
        fill(cells, (x, y, 2), (1, 1, 4), '#5B4231')
        anchors['weekdays'].append((x, y + 1, 9))
    for day in range(1, count + 1):
        row, column = divmod(start + day - 1, 7)
        total, across = 80 + 44 * row, -60 + 20 * column
        x, y = center(total, across)
        value = days[f'{year:04d}-{month:02d}-{day:02d}']
        paper = '#FFE28A' if value['expiring'] else CREAM
        trim = YELLOW if value['expiring'] else RED
        # A broad low shop extends toward the road underneath its roof sign.
        fill(cells, (x - 3, y - 1, 2), (12, 8, 1), STONE)
        fill(cells, (x - 2, y, 3), (10, 6, 5), '#EBD5AC')
        fill(cells, (x - 3, y - 1, 8), (12, 8, 1), trim)
        fill(cells, (x + 3, y + 5, 3), (2, 1, 4), '#65503B')
        fill(cells, (x, y + 5, 4), (2, 1, 2), '#527073')
        for step in range(9):
            px, py = x - 4 + step, y + 4 - step
            fill(cells, (px, py, 4), (1, 2, 1), trim)
            fill(cells, (px, py, 5), (1, 2, 13), paper)
            fill(cells, (px, py, 18), (1, 2, 1), trim)
        anchors['days'].append((x - 1, y, 10))
    for slot in range(start):
        across = -60 + 20 * slot
        if slot % 3 == 0:
            lamp(cells, 80, across)
        elif slot % 3 == 1:
            planter(cells, 80, across)
        else:
            bench(cells, 80, across)
    for row in range(rows - 1):
        planter(cells, 80 + row * 44 + 32, -64 if row % 2 else 64)
    guide(cells, entry - 10, -46)
    bench(cells, entry - 10, 48)
    planter(cells, entry + 10, -58)
    planter(cells, entry + 10, 58)
    lamp(cells, entry - 4, -64)
    lamp(cells, entry - 4, 64)
    anchors['entrance'].append(entrance_gate(cells, entry))
    return normalize(merged_geometry(cells), anchors)
