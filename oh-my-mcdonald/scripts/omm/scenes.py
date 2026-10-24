"""Continuous street and shared meal-table geometry on the integer voxel grid.

Both composers return (geometry, anchors). Anchor points are integer world
coordinates and use the same projection as the geometry. Rendering uses 8 px
per voxel; the composers never resize a model.
"""
import json
from functools import lru_cache
from pathlib import Path

ASSETS = Path(__file__).resolve().parents[2] / 'assets'
RED = '#DA291C'
YELLOW = '#FFC72C'
CREAM = '#F4EBD8'
CHARCOAL = '#292C2F'


@lru_cache(maxsize=1)
def library():
    return json.loads((ASSETS / 'coarse-models.json').read_text(encoding='utf-8'))


def cuboid(origin, size, color):
    return {'origin': list(origin), 'size': list(size), 'color': color}


def translated(geometry, position):
    return [cuboid(tuple(p['origin'][i] + position[i] for i in range(3)),
                   p['size'], p['color']) for p in geometry]


def bounds(geometry):
    return (tuple(min(p['origin'][i] for p in geometry) for i in range(3)),
            tuple(max(p['origin'][i] + p['size'][i] for p in geometry) for i in range(3)))


def row_geometry(cells):
    """Combine adjacent equal-color cells along each horizontal row."""
    remaining = cells.copy()
    result = []
    for x, y, z in sorted(cells, key=lambda p: (p[2], p[1], p[0])):
        if (x, y, z) not in remaining:
            continue
        color = remaining[x, y, z]
        width = 1
        while remaining.get((x + width, y, z)) == color:
            width += 1
        result.append(cuboid((x, y, z), (width, 1, 1), color))
        for xx in range(x, x + width):
            del remaining[xx, y, z]
    return result


def normalize(geometry, anchors):
    low, _ = bounds(geometry)
    delta = tuple(-v for v in low)
    return translated(geometry, delta), {
        key: [tuple(point[i] + delta[i] for i in range(3)) for point in points]
        for key, points in anchors.items()
    }


def compose_street(count):
    """Place one to three stores along one horizontal projected street.

    Three stores project to 942.24 px at 8 px/voxel. Prices attach above each
    entrance; names sit at the near edge of the road, below the price signs.
    """
    back = 24 * (count - 1)
    minimum_t, maximum_t = -back - 16, back + 24
    cells = {}
    for y in range(-16, back + 58):
        for x in range(-16, back + 58):
            total, across = x + y, x - y
            if back - 3 <= total < back + 51 and minimum_t < across < maximum_t:
                cells[x, y, 0] = '#DFA21D'
                if back + 40 <= total < back + 49:
                    color = '#414440'
                    if total == back + 44 and (across - minimum_t) % 16 < 8:
                        color = CREAM
                elif total in (back + 39, back + 49):
                    color = YELLOW
                else:
                    color = CREAM if (x // 4 + y // 4) % 2 else '#E5D7BB'
                cells[x, y, 1] = color
    geometry = row_geometry(cells)
    anchors = {'prices': [], 'names': []}
    for index in range(count):
        x, y = 24 * index, back - 24 * index
        geometry.extend(translated(library()['restaurant_kiosk'], (x, y, 2)))
        # The diagonal hanging frame projects horizontally while retaining the grid.
        for step in range(15):
            px, py = x + 14 + step, y + 23 - step
            color = CHARCOAL if step in (0, 14) else RED
            geometry.append(cuboid((px, py, 15), (1, 2, 9), color))
            geometry.append(cuboid((px, py, 24), (1, 2, 1), YELLOW))
        for step in (3, 11):
            px, py = x + 14 + step, y + 23 - step
            geometry.append(cuboid((px, py, 2), (1, 1, 13), CHARCOAL))
            geometry.append(cuboid((px - 1, py - 1, 2), (3, 3, 1), '#B8AD98'))
        anchors['prices'].append((x + 21, y + 17, 19))
        anchors['names'].append((x + 27, y + 23, 2))
    return normalize(geometry, anchors)


def compose_table(meal_models):
    """Serve up to three actual food models together on one tray and table.

    Even three 14 x 14 burgers fit inside a 52 x 24 tray. Including the table,
    the widest three-item composition projects to 609.68 px at 8 px/voxel.
    """
    foods = []
    for name in meal_models:
        parts = library()[name]
        low, high = bounds(parts)
        foods.append((parts, low, tuple(high[i] - low[i] for i in range(3))))
    occupied_width = sum(size[0] for _, _, size in foods) + 2 * max(0, len(foods) - 1)
    tray_width = max(38, occupied_width + 6)
    tray_depth = max(24, max((size[1] for _, _, size in foods), default=0) + 6)
    width, depth = tray_width + 6, tray_depth + 6
    geometry = []
    for x in (2, width - 4):
        for y in (2, depth - 4):
            geometry.append(cuboid((x, y, 0), (2, 2, 7), CHARCOAL))
    geometry.append(cuboid((0, 0, 7), (width, depth, 1), '#8F552E'))
    for x in range(width):
        geometry.append(cuboid((x, 0, 8), (1, depth, 1),
                               '#976338' if x % 8 == 0 else '#C58C50'))
    # A recessed paper liner sits inside the four raised edges of one serving tray.
    geometry.append(cuboid((3, 3, 9), (tray_width, tray_depth, 1), '#A71D18'))
    geometry.append(cuboid((3, 3, 10), (2, tray_depth, 2), RED))
    geometry.append(cuboid((tray_width + 1, 3, 10), (2, tray_depth, 2), RED))
    geometry.append(cuboid((5, 3, 10), (tray_width - 4, 2, 2), RED))
    geometry.append(cuboid((5, tray_depth + 1, 10), (tray_width - 4, 2, 2), RED))
    geometry.append(cuboid((5, 5, 10), (tray_width - 4, tray_depth - 4, 1), '#FFF1D4'))
    cursor = 3 + (tray_width - occupied_width) // 2
    anchors = {'foods': []}
    for parts, low, size in foods:
        y = 3 + (tray_depth - size[1]) // 2
        position = (cursor - low[0], y - low[1], 11 - low[2])
        geometry.extend(translated(parts, position))
        anchors['foods'].append((cursor + size[0] // 2, y + size[1] // 2, 12 + size[2]))
        cursor += size[0] + 2
    return geometry, anchors
