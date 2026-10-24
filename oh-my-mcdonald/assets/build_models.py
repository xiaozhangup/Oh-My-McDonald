"""Build the original scene assets on one shared, integer 1 x 1 x 1 voxel grid."""
import json
from pathlib import Path

RED = '#DA291C'
RED_DARK = '#A71D18'
RED_LIGHT = '#EE4938'
YELLOW = '#FFC72C'
GOLD = '#DFA21D'
CREAM = '#F4EBD8'
WHITE = '#FFF8E9'
SAND = '#D6C8AC'
STONE = '#B8AD98'
CHARCOAL = '#292C2F'
DARK = '#1A2228'
GLASS = '#334C58'
GLASS_LIGHT = '#63808A'
METAL = '#687174'
WOOD = '#B87943'
LEAF = '#49644A'
LEAF_LIGHT = '#6F8654'
LEAF_DARK = '#354C3A'
SOIL = '#66513D'
VOXELS = {}


class Grid:
    def __init__(self, name):
        self.cells = {}
        VOXELS[name] = self

    def fill(self, origin, size, color):
        """Paint occupied cells; later colors replace earlier cells exactly."""
        x, y, z = origin
        width, depth, height = size
        for zz in range(z, z + height):
            for yy in range(y, y + depth):
                for xx in range(x, x + width):
                    self.cells[xx, yy, zz] = color

    def motif(self, rows, origin, color, face='y'):
        x, y, z = origin
        for row_index, row in enumerate(rows):
            for column, pixel in enumerate(row):
                if pixel != ' ':
                    if face == 'y':
                        point = x + column, y, z + len(rows) - row_index - 1
                    elif face == 'x':
                        point = x, y + column, z + len(rows) - row_index - 1
                    else:
                        point = x + column, y + row_index, z
                    self.cells[point] = color

    def cuboids(self):
        """Merge same-color occupied cells along x, then y, then z."""
        remaining = self.cells.copy()
        result = []
        for x, y, z in sorted(self.cells, key=lambda p: (p[2], p[1], p[0])):
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
            result.append({'origin': [x, y, z], 'size': [width, depth, height], 'color': color})
            for zz in range(z, z + height):
                for yy in range(y, y + depth):
                    for xx in range(x, x + width):
                        del remaining[xx, yy, zz]
        return result


ARCHES = (
    '   ###     ###   ',
    '  #####   #####  ',
    '  ## ##   ## ##  ',
    ' ##   #   #   ## ',
    ' ##   ## ##   ## ',
    ' ##    # #    ## ',
    ' ##    # #    ## ',
    '##     ###     ##',
    '##     ###     ##',
    '##      #      ##',
    '##      #      ##',
    '##      #      ##',
)
SMALL_ARCHES = (' ## ## ', '## # ##', '#  #  #', '#  #  #', '#  #  #', '#  #  #')
TINY_ARCHES = (' # # ', '# # #', '# # #', '# # #')


def front_window(model, x, width):
    model.fill((x, 29, 5), (width, 1, 14), CHARCOAL)
    model.fill((x + 1, 29, 6), (width - 2, 1, 12), GLASS)
    model.fill((x + 2, 29, 7), (width - 4, 1, 1), WOOD)
    model.fill((x + 2, 29, 14), (1, 1, 3), GLASS_LIGHT)
    model.fill((x + width // 2, 29, 5), (1, 1, 14), CHARCOAL)
    model.fill((x, 29, 12), (width, 1, 1), CHARCOAL)
    model.fill((x + width // 2 - 1, 29, 17), (3, 1, 1), YELLOW)
    model.fill((x, 30, 4), (width, 1, 1), SAND)


def side_window(model, y, width):
    model.fill((45, y, 5), (1, width, 14), CHARCOAL)
    model.fill((45, y + 1, 6), (1, width - 2, 12), GLASS)
    model.fill((45, y + 2, 7), (1, width - 4, 1), WOOD)
    model.fill((45, y + 1, 14), (1, 1, 3), GLASS_LIGHT)
    model.fill((45, y + width // 2, 5), (1, 1, 14), CHARCOAL)
    model.fill((45, y, 12), (1, width, 1), CHARCOAL)
    model.fill((45, y + width // 2 - 1, 17), (1, 3, 1), YELLOW)
    model.fill((46, y, 4), (1, width, 1), SAND)


m = Grid('restaurant')
m.fill((0, 0, 0), (48, 34, 1), STONE)
m.fill((0, 0, 1), (48, 34, 1), CREAM)
for x in range(0, 48, 6):
    m.fill((x, 31, 1), (1, 3, 1), SAND)
m.fill((2, 2, 2), (44, 28, 2), STONE)
m.fill((2, 2, 4), (44, 28, 20), CREAM)
# Red corner tower and its whole-voxel brick accents.
m.fill((2, 25, 2), (11, 5, 27), RED)
for z in range(5, 24, 4):
    for x in range(3 + (z // 4 % 2), 12, 4):
        m.fill((x, 29, z), (2, 1, 1), RED_DARK)
m.fill((2, 25, 29), (11, 5, 1), YELLOW)
m.motif(SMALL_ARCHES, (4, 30, 16), YELLOW)
m.fill((4, 30, 11), (7, 1, 3), CREAM)
m.fill((5, 30, 12), (5, 1, 1), RED_DARK)
front_window(m, 14, 10)
front_window(m, 35, 10)
# Two glazed door leaves share a one-cell central frame.
m.fill((25, 29, 2), (9, 1, 17), CHARCOAL)
for x in (26, 30):
    m.fill((x, 29, 3), (3, 1, 15), GLASS)
    m.fill((x, 29, 5), (3, 1, 1), METAL)
    m.fill((x, 29, 13), (2, 1, 1), WHITE)
m.fill((28, 30, 8), (1, 1, 3), YELLOW)
m.fill((30, 30, 8), (1, 1, 3), YELLOW)
m.fill((25, 30, 1), (9, 3, 1), CHARCOAL)
for y in (4, 13, 22):
    side_window(m, y, 7)
# Roof fascia and projecting striped canopy.
m.fill((1, 1, 23), (46, 30, 1), YELLOW)
m.fill((1, 1, 24), (46, 30, 3), RED)
m.fill((1, 1, 27), (46, 30, 1), RED_DARK)
m.fill((3, 3, 27), (42, 26, 1), CHARCOAL)
for origin, size in (((1, 1, 28), (46, 1, 1)), ((1, 30, 28), (46, 1, 1)),
                     ((1, 2, 28), (1, 28, 1)), ((46, 2, 28), (1, 28, 1))):
    m.fill(origin, size, RED)
m.fill((14, 30, 20), (32, 3, 1), RED_DARK)
for x in range(14, 46, 2):
    stripe = RED if ((x - 14) // 2) % 2 else CREAM
    m.fill((x, 30, 21), (2, 4, 1), stripe)
    m.fill((x, 33, 20), (2, 1, 1), stripe)
m.fill((14, 33, 19), (32, 1, 1), YELLOW)
m.fill((46, 3, 20), (1, 27, 2), RED)
m.fill((46, 3, 19), (1, 27, 1), YELLOW)
# A complete 17-cell arch silhouette is extruded one full cell from the panel.
for x in (19, 32):
    m.fill((x, 6, 28), (2, 2, 3), CHARCOAL)
m.fill((15, 6, 30), (23, 3, 14), RED_DARK)
m.fill((15, 8, 30), (23, 1, 14), CREAM)
m.fill((16, 8, 31), (21, 1, 12), RED)
m.motif(ARCHES, (18, 9, 31), YELLOW)
# Roof ventilation uses full-cell slats and duct steps.
m.fill((36, 5, 28), (8, 10, 1), DARK)
m.fill((37, 6, 29), (6, 8, 3), METAL)
m.fill((37, 6, 32), (6, 8, 1), STONE)
for y in range(7, 14, 2):
    m.fill((38, y, 32), (4, 1, 1), CHARCOAL)
for z in (29, 31):
    m.fill((42, 7, z), (1, 6, 1), CHARCOAL)
m.fill((38, 15, 28), (3, 5, 2), METAL)
m.fill((39, 18, 30), (2, 2, 3), METAL)
m.fill((38, 17, 33), (4, 4, 1), STONE)

m = Grid('golden_arches')
m.fill((7, 1, 0), (9, 6, 1), STONE)
m.fill((8, 2, 1), (7, 4, 1), CHARCOAL)
m.fill((10, 3, 2), (3, 2, 23), METAL)
m.fill((11, 5, 2), (1, 1, 21), RED)
m.fill((0, 1, 24), (23, 5, 14), RED_DARK)
m.fill((0, 5, 24), (23, 1, 14), CREAM)
m.fill((1, 5, 25), (21, 1, 12), RED)
m.motif(ARCHES, (3, 6, 25), YELLOW)
m.fill((5, 2, 18), (13, 4, 5), RED)
m.motif(('  #  ', '   # ', '#####', '   # ', '  #  '), (9, 6, 18), YELLOW)

m = Grid('terrace_umbrella')
m.fill((8, 8, 0), (6, 6, 1), STONE)
m.fill((9, 9, 1), (4, 4, 1), CHARCOAL)
m.fill((10, 10, 2), (2, 2, 16), METAL)
for inset, z in ((0, 17), (2, 18), (4, 19), (6, 20), (8, 21), (9, 22)):
    half = 11 - inset
    for side_x, side_y, color in ((0, 0, RED), (1, 0, CREAM), (0, 1, CREAM), (1, 1, RED)):
        m.fill((inset + side_x * half, inset + side_y * half, z), (half, half, 1), color)
m.fill((0, 21, 16), (11, 1, 1), CREAM)
m.fill((11, 21, 16), (11, 1, 1), RED)
m.fill((21, 0, 16), (1, 11, 1), CREAM)
m.fill((21, 11, 16), (1, 11, 1), RED)
for x, y in ((0, 21), (21, 0), (21, 21)):
    m.fill((x, y, 16), (1, 1, 1), YELLOW)
m.fill((10, 10, 23), (2, 2, 2), YELLOW)

m = Grid('terrace_table')
m.fill((3, 3, 0), (8, 8, 1), CHARCOAL)
m.fill((6, 6, 1), (2, 2, 7), CHARCOAL)
m.fill((0, 0, 8), (14, 14, 2), RED_DARK)
for x, width in ((0, 3), (4, 3), (8, 3), (12, 2)):
    m.fill((x, 0, 9), (width, 14, 1), WOOD)

m = Grid('chair')
for x in (1, 5):
    for y in (1, 5):
        m.fill((x, y, 0), (1, 1, 5), CHARCOAL)
m.fill((0, 0, 5), (7, 7, 1), RED_DARK)
for y in (0, 3, 6):
    m.fill((0, y, 6), (7, 1, 1), YELLOW)
for x in (0, 6):
    m.fill((x, 0, 6), (1, 1, 6), CHARCOAL)
for z in (8, 10):
    m.fill((1, 0, z), (5, 1, 2), RED)

m = Grid('bench')
for x in (2, 14):
    for y in (1, 5):
        m.fill((x, y, 0), (2, 1, 6), CHARCOAL)
m.fill((0, 0, 5), (18, 7, 1), CHARCOAL)
for y, depth in ((0, 2), (3, 2), (6, 1)):
    m.fill((0, y, 6), (18, depth, 1), WOOD)
for x in (1, 16):
    m.fill((x, 0, 6), (1, 1, 5), CHARCOAL)
    m.fill((x, 0, 8), (1, 7, 1), CHARCOAL)
for z in (8, 10):
    m.fill((0, 0, z), (18, 1, 1), RED)
m.fill((0, 0, 10), (18, 1, 1), YELLOW)

m = Grid('coupon_kiosk')
m.fill((0, 0, 0), (8, 7, 1), STONE)
m.fill((1, 1, 1), (6, 5, 18), RED_DARK)
m.fill((1, 5, 1), (6, 1, 18), RED)
m.fill((0, 0, 19), (8, 7, 1), YELLOW)
m.fill((2, 5, 10), (4, 1, 8), CHARCOAL)
m.fill((2, 6, 11), (4, 1, 6), CREAM)
m.fill((3, 6, 15), (2, 1, 1), GOLD)
m.fill((2, 6, 14), (4, 1, 1), YELLOW)
m.fill((2, 6, 13), (4, 1, 1), RED_DARK)
m.fill((2, 6, 12), (4, 1, 1), GOLD)
m.fill((2, 6, 9), (2, 1, 1), WHITE)
m.fill((5, 6, 9), (1, 1, 1), YELLOW)
m.fill((2, 6, 6), (4, 1, 1), CHARCOAL)
m.fill((3, 6, 5), (2, 1, 1), WHITE)
m.motif(TINY_ARCHES, (2, 6, 1), YELLOW)
for z in (3, 5, 7):
    m.fill((6, 2, z), (1, 2, 1), CHARCOAL)

m = Grid('calendar')
for x in (3, 14):
    m.fill((x - 1, 0, 0), (3, 5, 1), STONE)
    m.fill((x, 2, 1), (1, 1, 7), CHARCOAL)
m.fill((0, 1, 8), (18, 3, 14), RED_DARK)
m.fill((1, 4, 9), (16, 1, 12), CREAM)
m.fill((1, 4, 18), (16, 1, 3), RED)
m.fill((3, 4, 19), (5, 1, 1), YELLOW)
m.fill((10, 4, 19), (5, 1, 1), WHITE)
for row in range(3):
    for column in range(5):
        color = YELLOW if (row, column) in ((1, 1), (2, 3)) else SAND
        m.fill((2 + column * 3, 4, 9 + row * 3), (2, 1, 2), color)
        m.fill((2 + column * 3, 4, 10 + row * 3), (1, 1, 1), RED_DARK)
m.fill((0, 0, 22), (18, 5, 1), YELLOW)
for x in (3, 13):
    m.fill((x, 2, 21), (2, 2, 2), CHARCOAL)

m = Grid('street_lamp')
m.fill((3, 2, 0), (4, 5, 1), STONE)
m.fill((4, 3, 1), (2, 2, 2), CHARCOAL)
m.fill((4, 3, 3), (1, 1, 26), CHARCOAL)
m.fill((0, 3, 27), (5, 1, 1), CHARCOAL)
m.fill((0, 3, 25), (1, 1, 2), CHARCOAL)
m.fill((0, 2, 24), (3, 3, 1), CHARCOAL)
m.fill((1, 3, 23), (1, 1, 1), WHITE)
m.fill((5, 3, 14), (3, 1, 7), RED)
m.fill((6, 3, 16), (1, 1, 3), YELLOW)
m.fill((5, 3, 19), (3, 1, 1), YELLOW)
m.fill((4, 3, 8), (1, 1, 1), YELLOW)


def shrub(model, origin, size):
    x, y, z = origin
    width, depth, height = size
    model.fill((x + 1, y + 1, z), (width - 2, depth - 2, height), LEAF_DARK)
    model.fill((x, y + 1, z + 1), (width, depth - 2, height - 2), LEAF)
    model.fill((x + 1, y, z + 1), (width - 2, depth, height - 2), LEAF)
    model.fill((x + 1, y + 1, z + height - 1), (width - 2, depth - 2, 1), LEAF_LIGHT)

m = Grid('planter')
m.fill((0, 0, 0), (16, 8, 1), CHARCOAL)
m.fill((0, 0, 1), (16, 8, 4), CREAM)
m.fill((0, 0, 3), (16, 8, 1), RED)
m.fill((1, 1, 4), (14, 6, 1), SOIL)
for x in (1, 6, 11):
    shrub(m, (x, 1, 5), (4, 6, 4))
    m.fill((x + 1, 6, 7), (2, 1, 1), YELLOW)

m = Grid('garden')
m.fill((0, 0, 0), (18, 12, 1), STONE)
m.fill((0, 0, 1), (18, 12, 2), CREAM)
m.fill((0, 11, 1), (18, 1, 1), RED)
m.fill((1, 1, 2), (16, 10, 1), SOIL)
for x in (1, 6, 11):
    shrub(m, (x, 1, 3), (5, 5, 6))
for index, x in enumerate((2, 5, 8, 11, 14)):
    m.fill((x, 8, 3), (1, 1, 4), LEAF_DARK)
    m.fill((x + 1, 8, 5), (1, 1, 1), LEAF)
    m.fill((x, 8, 7), (2, 2, 2), RED if index % 2 else YELLOW)

m = Grid('tree')
m.fill((0, 0, 0), (15, 15, 1), STONE)
m.fill((1, 1, 1), (13, 13, 1), CREAM)
m.fill((2, 2, 2), (11, 11, 1), SOIL)
m.fill((6, 6, 3), (3, 3, 12), '#896042')
m.fill((4, 6, 12), (3, 2, 2), WOOD)
m.fill((8, 6, 15), (3, 2, 2), WOOD)
shrub(m, (1, 3, 13), (8, 8, 8))
shrub(m, (7, 2, 15), (7, 8, 8))
shrub(m, (3, 7, 16), (8, 7, 7))
shrub(m, (4, 3, 20), (7, 8, 7))
m.fill((3, 11, 3), (2, 1, 1), YELLOW)
m.fill((11, 4, 3), (1, 2, 1), RED)

m = Grid('road_tile')
m.fill((0, 0, 0), (16, 16, 1), '#73736B')
for y in (0, 15):
    m.fill((0, y, 0), (16, 1, 1), CREAM)
for x in (1, 9):
    m.fill((x, 7, 0), (5, 1, 1), YELLOW)

m = Grid('crosswalk')
m.fill((0, 0, 0), (16, 16, 1), '#73736B')
for x in (1, 4, 7, 10, 13):
    m.fill((x, 2, 0), (2, 12, 1), WHITE)

m = Grid('sidewalk_tile')
m.fill((0, 0, 0), (16, 16, 1), SAND)
for x in range(0, 16, 4):
    for y in range(0, 16, 4):
        m.fill((x, y, 0), (3, 3, 1), CREAM)

m = Grid('parking_tile')
m.fill((0, 0, 0), (16, 16, 1), '#73736B')
for x in (0, 15):
    m.fill((x, 1, 0), (1, 14, 1), WHITE)
m.fill((0, 14, 0), (16, 1, 1), WHITE)
m.motif(('#### ', '#   #', '#   #', '#### ', '#    ', '#    ', '#    '), (5, 3, 0), CREAM, 'z')
m.fill((3, 12, 1), (10, 1, 1), CHARCOAL)
for x in (3, 10):
    m.fill((x, 12, 1), (3, 1, 1), YELLOW)

m = Grid('mailbox')
m.fill((2, 1, 0), (5, 5, 1), STONE)
m.fill((3, 2, 1), (2, 2, 7), CHARCOAL)
m.fill((0, 0, 8), (8, 6, 5), RED_DARK)
m.fill((0, 0, 13), (8, 6, 1), RED)
m.fill((1, 0, 14), (6, 6, 1), RED)
m.fill((2, 0, 15), (4, 6, 1), RED_LIGHT)
m.fill((1, 6, 9), (6, 1, 4), RED)
m.fill((2, 6, 12), (4, 1, 1), DARK)
m.fill((2, 6, 13), (4, 1, 1), YELLOW)
m.fill((3, 6, 10), (2, 1, 1), CREAM)

m = Grid('chest')
for x in (1, 11):
    for y in (1, 7):
        m.fill((x, y, 0), (2, 2, 1), CHARCOAL)
m.fill((0, 0, 1), (14, 10, 7), RED)
for x in (2, 11):
    m.fill((x, 9, 1), (1, 1, 7), GOLD)
m.fill((0, 0, 8), (14, 10, 1), GOLD)
m.fill((1, 1, 9), (12, 8, 1), YELLOW)
m.fill((2, 2, 10), (10, 6, 1), YELLOW)
m.fill((5, 4, 11), (4, 2, 1), RED)
m.motif(TINY_ARCHES, (5, 9, 2), YELLOW)
m.fill((6, 9, 6), (2, 1, 2), GOLD)
m.fill((6, 9, 7), (1, 1, 1), CHARCOAL)

m = Grid('trash_bin')
m.fill((0, 0, 0), (6, 6, 1), CHARCOAL)
m.fill((0, 0, 1), (6, 6, 8), CREAM)
m.fill((0, 0, 1), (6, 6, 1), RED)
m.fill((0, 0, 9), (6, 6, 1), CHARCOAL)
m.fill((0, 0, 10), (6, 6, 1), RED)
m.fill((1, 1, 11), (4, 4, 1), RED_DARK)
m.fill((1, 5, 10), (4, 1, 1), DARK)
m.motif(TINY_ARCHES, (0, 5, 3), YELLOW)

m = Grid('drive_thru_menu')
m.fill((1, 0, 0), (12, 5, 1), STONE)
for x in (3, 10):
    m.fill((x, 2, 1), (1, 1, 6), CHARCOAL)
m.fill((0, 1, 7), (14, 3, 14), CHARCOAL)
m.fill((1, 4, 8), (12, 1, 12), CREAM)
m.fill((1, 4, 17), (12, 1, 3), RED)
for x in (2, 8):
    m.fill((x + 1, 4, 15), (2, 1, 1), GOLD)
    m.fill((x, 4, 14), (4, 1, 1), YELLOW)
    m.fill((x, 4, 13), (4, 1, 1), RED_DARK)
    m.fill((x, 4, 12), (4, 1, 1), GOLD)
    m.fill((x, 4, 10), (3, 1, 1), CHARCOAL)
    m.fill((x, 4, 8), (4, 1, 1), YELLOW)
m.fill((3, 4, 18), (8, 1, 1), YELLOW)
m.fill((0, 0, 21), (14, 5, 1), RED_DARK)

m = Grid('bollard')
m.fill((0, 0, 0), (3, 3, 1), CHARCOAL)
m.fill((1, 1, 1), (1, 1, 6), YELLOW)
m.fill((1, 1, 4), (1, 1, 1), CHARCOAL)

m = Grid('traffic_cone')
m.fill((0, 0, 0), (6, 6, 1), CHARCOAL)
m.fill((1, 1, 1), (4, 4, 2), RED)
m.fill((1, 1, 3), (4, 4, 1), WHITE)
m.fill((2, 2, 4), (2, 2, 2), RED)
m.fill((2, 2, 6), (2, 2, 1), WHITE)

m = Grid('bike_rack')
for x in (0, 7, 14):
    for y in (0, 4):
        m.fill((x, y, 0), (1, 1, 7), METAL)
    m.fill((x, 0, 7), (1, 5, 1), METAL)
m.fill((0, 4, 2), (15, 1, 1), RED)

m = Grid('fence')
for x in (0, 16):
    m.fill((x, 0, 0), (2, 3, 9), CREAM)
    m.fill((x, 0, 9), (2, 3, 1), YELLOW)
for x in (4, 7, 10, 13):
    m.fill((x, 1, 1), (1, 1, 7), CHARCOAL)
for z in (2, 7):
    m.fill((2, 1, z), (14, 1, 1), RED)

# Compatibility food assets also use the same integer grid.
m = Grid('burger')
for z, inset, height, color in ((0, 2, 1, '#BC7736'), (1, 1, 1, '#E9AF4F'),
    (2, 0, 1, LEAF), (3, 1, 1, '#783F2A'), (4, 0, 1, YELLOW),
    (5, 1, 1, RED), (6, 0, 1, '#E8AB42'), (7, 1, 1, '#F1BC5C'),
    (8, 2, 1, '#F4CA74')):
    m.fill((inset, inset, z), (12 - inset * 2, 12 - inset * 2, height), color)
for x, y in ((3, 4), (7, 7), (7, 3), (4, 6)):
    m.fill((x, y, 9), (1, 1, 1), WHITE)

m = Grid('fries')
m.fill((1, 1, 0), (8, 5, 1), RED_DARK)
m.fill((0, 0, 1), (10, 7, 7), RED)
for x, y, height in ((1, 1, 5), (3, 1, 7), (5, 1, 4), (7, 1, 6), (2, 3, 6), (4, 3, 4), (6, 3, 7)):
    m.fill((x, y, 7), (1, 1, height), YELLOW)
m.motif(TINY_ARCHES, (2, 6, 2), YELLOW)

m = Grid('drink')
m.fill((2, 2, 0), (5, 5, 1), SAND)
m.fill((1, 1, 1), (7, 7, 11), CREAM)
m.fill((1, 1, 5), (7, 7, 4), RED)
m.fill((0, 0, 12), (9, 9, 1), WHITE)
m.fill((4, 4, 13), (1, 1, 6), RED)

MODELS = {name: model.cuboids() for name, model in VOXELS.items()}

if __name__ == '__main__':
    output = Path(__file__).with_name('models.json')
    output.write_text(json.dumps(MODELS, indent=2) + '\n', encoding='utf-8')
    print(f'Wrote {len(MODELS)} models, {sum(map(len, MODELS.values()))} merged cuboids')
