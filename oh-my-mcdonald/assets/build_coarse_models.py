"""Build original coarse food and scene models on a one-unit voxel grid.

Run: python oh-my-mcdonald/assets/build_coarse_models.py
All geometry is authored at this resolution and displayed at 8 pixels per voxel.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

RED = '#DA291C'
YELLOW = '#FFC72C'
WHITE = '#FFF3D8'
BROWN = '#77432B'
BUN = '#E8A74E'
GREEN = '#74B94A'


class Grid:
    def __init__(self):
        self.cells = {}

    def box(self, x, y, z, w, d, h, color):
        for a in range(x, x + w):
            for b in range(y, y + d):
                for c in range(z, z + h):
                    self.cells[a, b, c] = color

    def erase(self, x, y, z, w, d, h):
        for a in range(x, x + w):
            for b in range(y, y + d):
                for c in range(z, z + h):
                    self.cells.pop((a, b, c), None)

    def disk(self, cx, cy, z, rx, ry, h, color):
        for x in range(math.floor(cx - rx), math.ceil(cx + rx)):
            for y in range(math.floor(cy - ry), math.ceil(cy + ry)):
                if ((x + .5 - cx) / rx) ** 2 + ((y + .5 - cy) / ry) ** 2 <= 1:
                    self.box(x, y, z, 1, 1, h, color)

    def front_pixel(self, x, z, color):
        row = [y for a, y, c in self.cells if a == x and c == z]
        if row:
            self.cells[x, max(row), z] = color

    def logo(self, x, z, small=False, color=YELLOW):
        rows = ('01010', '10101', '10101', '10101') if small else (
            '0110110', '1101011', '1001001', '1001001', '1001001')
        for row, bits in enumerate(reversed(rows)):
            for col, bit in enumerate(bits):
                if bit == '1':
                    self.front_pixel(x + col, z + row, color)

    def top_pixel(self, x, y, color):
        column = [z for a, b, z in self.cells if a == x and b == y]
        if column:
            self.cells[x, y, max(column)] = color

    def export(self):
        remaining = dict(self.cells)
        result = []
        for x, y, z in sorted(self.cells, key=lambda p: (p[2], p[1], p[0])):
            if (x, y, z) not in remaining:
                continue
            color = remaining[x, y, z]
            w = 1
            while w < 4 and remaining.get((x + w, y, z)) == color:
                w += 1
            d = 1
            while d < 4 and all(remaining.get((a, y + d, z)) == color for a in range(x, x + w)):
                d += 1
            h = 1
            while h < 4 and all(remaining.get((a, b, z + h)) == color
                                for a in range(x, x + w) for b in range(y, y + d)):
                h += 1
            for a in range(x, x + w):
                for b in range(y, y + d):
                    for c in range(z, z + h):
                        del remaining[a, b, c]
            result.append({'origin': [x, y, z], 'size': [w, d, h], 'color': color})
        return result


def bun_top(f, z, seeded=True):
    for dz, radius, color in [(0, 7, '#D38C37'), (1, 6.5, BUN),
                              (2, 5.5, '#F1B55B'), (3, 3.5, '#F8C573')]:
        f.disk(7, 7, z + dz, radius, radius, 1, color)
    if seeded:
        for x, y in [(4, 6), (7, 4), (9, 6), (6, 9), (9, 9)]:
            f.top_pixel(x, y, '#FFF1BA')


def leaf(f, z):
    f.disk(7, 7, z, 7, 6.5, 1, GREEN)
    for x, y in [(1, 5), (3, 11), (10, 11), (11, 3)]:
        f.box(x, y, z, 2, 2, 1, '#9BD56C')


def cheese(f, z):
    f.box(2, 2, z, 10, 10, 1, YELLOW)
    f.box(3, 11, z - 1, 3, 1, 1, '#F4B422')
    f.box(11, 7, z - 1, 1, 3, 1, '#F4B422')


def meat(f, z, chicken=False, grilled=False, height=2):
    color = '#C58430' if chicken else BROWN
    if grilled:
        color = '#B96E35'
    f.disk(7, 7, z, 6.5, 6, height, color)
    if chicken:
        for x, y in [(1, 6), (3, 11), (10, 10), (11, 4)]:
            f.box(x, y, z, 1, 1, height, '#E5AB44')
    if grilled:
        for x in [3, 6, 9]:
            for y in range(3, 11):
                f.top_pixel(x, y, '#7A3E25')
        for x in [3, 6, 9]:
            f.front_pixel(x, z + 1, '#7A3E25')
    elif not chicken:
        for x in [3, 8, 11]:
            f.front_pixel(x, z, '#532D20')


def burger(kind):
    f = Grid()
    f.disk(7, 7, 0, 5.5, 5, 1, '#C27C32')
    f.disk(7, 7, 1, 6.5, 6, 1, BUN)
    f.disk(7, 7, 2, 7, 6.5, 1, '#F7CE80')
    z = 3
    if kind == 'big_mac':
        leaf(f, z); z += 1
        cheese(f, z); z += 1
        meat(f, z, height=1); z += 1
        f.disk(7, 7, z, 6.5, 6, 1, '#D99D4C'); z += 1
        f.disk(7, 7, z, 6.5, 6, 1, '#F6CD83'); z += 1
        leaf(f, z); z += 1
        meat(f, z, height=2); z += 2
        for x, y in [(4, 9), (9, 4)]:
            f.disk(x, y, z, 2, 1.5, 1, '#8FAD52')
        z += 1
    elif kind == 'filet_o_fish':
        cheese(f, z); z += 1
        f.box(2, 2, z, 10, 10, 3, '#D49A3D')
        f.box(2, 3, z + 1, 1, 2, 1, '#EEBB5D')
        f.box(10, 11, z + 1, 2, 1, 1, '#E8AD4C')
        z += 3
        f.disk(7, 7, z, 6, 5.5, 1, WHITE); z += 1
    elif kind in ('mcspicy', 'mccrispy', 'grilled_chicken'):
        meat(f, z, chicken=True, grilled=kind == 'grilled_chicken', height=3); z += 3
        if kind == 'mccrispy':
            cheese(f, z); z += 1
        if kind == 'grilled_chicken':
            f.disk(6, 7, z, 3, 3, 1, '#DF4D32'); z += 1
        leaf(f, z); z += 1
        f.disk(7, 7, z, 5.5, 5, 1, WHITE); z += 1
    else:
        for _ in range(2 if kind == 'double_cheese' else 1):
            meat(f, z, height=2); z += 2
            cheese(f, z); z += 1
        f.disk(7, 7, z, 4, 4, 1, '#D54D30')
        f.box(4, 9, z, 2, 2, 1, '#86A64B'); z += 1
    bun_top(f, z, kind != 'filet_o_fish')
    return f


def muffin(bacon=False):
    f = Grid()
    f.disk(6, 6, 0, 5, 4.5, 1, '#B88D51')
    f.disk(6, 6, 1, 6, 5.5, 2, '#E9C68C')
    f.disk(6, 6, 3, 5.5, 5, 1, BROWN)
    f.box(1, 1, 4, 10, 10, 1, YELLOW)
    f.disk(6, 6, 5, 5, 4.5, 2, WHITE)
    f.disk(6, 6, 6, 2.5, 2.5, 1, '#F6B62D')
    if bacon:
        for x in [2, 5, 8]:
            f.box(x, 1, 7, 1, 11, 1, '#A94F36')
            f.box(x, 10, 7, 1, 1, 1, '#DBA181')
    f.disk(6, 6, 8, 6, 5.5, 1, '#C99E66')
    f.disk(6, 6, 9, 5.5, 5, 1, '#E5C797')
    for x, y in [(3, 4), (6, 3), (8, 6), (5, 8)]:
        f.top_pixel(x, y, '#AB814E')
    return f


def fries(size='medium'):
    f = Grid()
    w, d, height = {'small': (8, 5, 12), 'medium': (10, 6, 15), 'large': (12, 7, 18)}[size]
    for z in range(8):
        left = 1 if z < 3 else 0
        right = w - left
        f.box(left, 0, z, right - left, 1, 1, '#E13D2A')
        f.box(left, 1, z, 1, d - 1, 1, RED)
        f.box(right - 1, 1, z, 1, d - 1, 1, '#B9251B')
        for x in range(left, right):
            lip = 6 if 2 <= x < w - 2 else 8
            if z < lip:
                f.box(x, d - 1, z, 1, 1, 1, RED)
        if z == 0:
            f.box(left, 0, 0, right - left, d, 1, RED)
    for row, y in enumerate(range(1, d - 1, 2)):
        for col, x in enumerate(range(1, w - 1, 2)):
            top = height - ((col + row * 2) % 3)
            f.box(x, y, 3, 1, 1, top - 3, '#F3BC36')
            f.box(x, y, top - 1, 1, 1, 1, '#FFE26A')
    f.logo((w - 5) // 2, 1, small=True)
    return f


def cup(f, height, color, radius=4):
    for z in range(height):
        r = radius - 1 if z < 3 else (radius - .5 if z < 7 else radius)
        f.disk(radius, radius, z, r, r, 1, color)
    f.disk(radius, radius, 0, radius - 1, radius - 1, 1, '#E6D8C2')


def drink(kind):
    f = Grid()
    colors = {'cola': RED, 'cola_zero': '#FFF6E5', 'sprite': '#4BA365',
              'iced_coffee': '#9C6949', 'iced_latte': '#C6996C', 'orange_juice': '#EFAF2D'}
    cup(f, 12, colors[kind])
    if kind in ('iced_coffee', 'iced_latte', 'orange_juice'):
        if kind == 'iced_latte':
            for x, y, z in list(f.cells):
                if z < 4:
                    f.cells[x, y, z] = '#E9D7B9'
        for z in range(2, 11):
            f.front_pixel(1, z, '#E8DDC7')
        f.disk(4, 4, 12, 4, 4, 1, '#EDE9D9')
        f.disk(4, 4, 12, 3, 3, 1, colors[kind])
        for x, y in [(2, 2), (5, 2), (3, 5)]:
            f.box(x, y, 13, 1, 1, 1, '#FFF7E6')
        f.box(4, 3, 13, 1, 1, 5, '#B89A70')
        f.logo(1, 5, small=True, color=WHITE)
    else:
        if kind == 'cola_zero':
            for x in range(1, 7):
                for z in range(3, 9):
                    f.front_pixel(x, z, '#26262A')
        f.logo(1, 4, small=True, color=RED if kind == 'cola_zero' else YELLOW)
        f.disk(4, 4, 12, 4, 4, 1, '#FFF8E9')
        f.disk(4, 4, 13, 3.5, 3.5, 1, '#E3DED2')
        for z in range(14, 18):
            f.box(4, 3, z, 1, 1, 1, RED if z % 2 else WHITE)
    return f


def hot_coffee():
    f = Grid()
    cup(f, 10, '#795039')
    for x in range(1, 7):
        for z in range(3, 7):
            f.front_pixel(x, z, '#C59864')
    f.logo(1, 3, small=True, color=WHITE)
    f.disk(4, 4, 10, 4, 4, 1, '#342B25')
    f.disk(4, 4, 11, 3.5, 3.5, 1, '#4B3A2D')
    f.box(3, 6, 11, 2, 1, 1, '#211D19')
    return f


def milk():
    f = Grid()
    f.box(0, 0, 0, 8, 6, 10, '#FFF6E5')
    f.box(0, 0, 0, 8, 6, 2, '#5799BD')
    f.box(0, 5, 3, 8, 1, 2, '#79B6D5')
    f.box(7, 0, 3, 1, 6, 2, '#589AC0')
    f.box(0, 0, 10, 8, 6, 1, '#DDE7E5')
    f.box(1, 0, 11, 6, 6, 1, '#F9F5E6')
    f.box(2, 0, 12, 4, 6, 1, '#DBE4E3')
    f.box(3, 0, 13, 2, 6, 1, '#5799BD')
    f.logo(1, 6, small=True, color=RED)
    return f


def food_box(f, w=14, d=10, color=RED, lid=False):
    f.box(0, 0, 0, w, d, 1, color)
    f.box(1, 1, 1, w - 2, d - 2, 1, '#F4DCA9')
    for x in [0, w - 1]:
        f.box(x, 0, 1, 1, d, 2, color)
    for y in [0, d - 1]:
        f.box(1, y, 1, w - 2, 1, 2, color)
    f.box(w // 2 - 2, d - 1, 1, 4, 1, 1, YELLOW)
    if lid:
        f.box(0, 0, 3, w, 1, 5, '#F1CD69')
        f.box(1, 0, 4, w - 2, 1, 3, WHITE)


def nugget(f, x, y, z):
    f.disk(x, y, z, 2, 1.7, 1, '#B67A2C')
    f.disk(x, y, z + 1, 1.7, 1.4, 1, '#E9B655')
    f.top_pixel(x - 1, y - 1, '#F4CC77')


def nuggets(count):
    f = Grid()
    food_box(f, color=YELLOW if count == 10 else RED, lid=True)
    positions = {
        4: [(4, 3), (10, 3), (4, 7), (10, 7)],
        5: [(4, 3), (10, 3), (3, 7), (7, 7), (11, 7)],
        6: [(3, 3), (7, 3), (11, 3), (3, 7), (7, 7), (11, 7)],
        10: [(3, 3), (7, 3), (11, 3), (3, 7), (7, 7), (11, 7)],
    }
    for x, y in positions[count]:
        nugget(f, x, y, 2)
    if count == 10:
        for x, y in [(5, 3), (9, 3), (5, 7), (9, 7)]:
            nugget(f, x, y, 4)
    return f


def wings():
    f = Grid()
    food_box(f, color=YELLOW)
    for x, y in [(4, 3), (8, 7)]:
        f.disk(x, y, 2, 2.5, 2, 2, '#C08435')
        f.disk(x, y, 4, 2, 1.5, 1, '#E7AE4D')
        f.box(x + 1, y - 1, 3, 3, 2, 1, '#D99A3E')
        f.box(x + 4, y - 1, 3, 1, 2, 1, '#F9E4BC')
    return f


def corn():
    f = Grid()
    cup(f, 6, YELLOW)
    for x in range(1, 7):
        f.front_pixel(x, 2, '#70A547')
    f.disk(4, 4, 6, 4, 4, 1, '#FFF0BC')
    for x, y in [(2, 2), (4, 2), (6, 3), (2, 4), (4, 4), (5, 6), (2, 6)]:
        f.box(x, y, 7, 1, 1, 1, '#FFD448')
    f.logo(1, 3, small=True, color=RED)
    return f


def apples():
    f = Grid()
    food_box(f, 10, 8, '#F5DDB4')
    f.box(0, 7, 1, 10, 1, 2, RED)
    for x, y in [(2, 2), (5, 3), (8, 4)]:
        f.box(x - 1, y, 2, 3, 1, 1, '#D84034')
        f.box(x - 1, y, 3, 3, 1, 1, '#FFEFBE')
        f.box(x, y, 4, 1, 1, 1, '#D84034')
        f.box(x - 1, y, 3, 1, 1, 1, '#D84034')
    return f


def salad():
    f = Grid()
    for z, rx, ry in [(0, 4, 3.5), (1, 4.5, 4), (2, 5, 4.5), (3, 6, 5)]:
        f.disk(6, 5, z, rx, ry, 1, '#DCC8A3' if z < 3 else WHITE)
    f.disk(6, 5, 4, 5.5, 4.5, 1, '#4E8E36')
    for x, y in [(2, 3), (5, 1), (8, 2), (9, 5), (6, 7), (2, 6), (5, 4)]:
        f.box(x, y, 5, 2, 2, 1, GREEN)
        f.box(x, y, 6, 1, 1, 1, '#A3D274')
    for x, y in [(4, 3), (8, 5), (3, 6)]:
        f.box(x, y, 6, 2, 2, 1, '#DA4732')
        f.box(x, y, 7, 1, 1, 1, '#F28C56')
    return f


def cone():
    f = Grid()
    for z in range(9):
        radius = 1 + z // 3
        f.disk(4, 4, z, radius, radius, 1, '#CF9550' if z % 2 else '#E6B46C')
    for z, r, cx in [(9, 4, 4), (11, 3, 5), (13, 2.5, 4), (15, 1.5, 4), (17, .7, 4.5)]:
        f.disk(cx, 4, z, r, r, 1, '#EADDC3')
        f.disk(cx, 4, z + 1, max(.6, r - .5), max(.6, r - .5), 1, '#FFF6DF')
    return f


def icecream(kind):
    f = Grid()
    cup(f, 7, WHITE)
    for x in range(1, 7):
        for z in [2, 3]:
            f.front_pixel(x, z, RED)
    for z, r in [(7, 4), (8, 3.5), (9, 3), (10, 2), (11, 1)]:
        f.disk(4, 4, z, r, r, 1, '#FFF6E1' if z % 2 else '#EADFC8')
    if kind == 'mcflurry':
        for x, y in [(2, 3), (4, 2), (5, 4), (3, 5), (4, 4)]:
            f.top_pixel(x, y, '#593A2C')
        f.box(3, 2, 10, 1, 1, 6, '#F8F0DF')
        f.box(3, 2, 15, 2, 1, 2, '#D8D0BF')
    else:
        color = '#71442D' if kind == 'sundae_chocolate' else '#D24943'
        for x in [2, 5]:
            for z in range(8, 11):
                f.front_pixel(x, z, color)
        for x, y in [(3, 3), (4, 4), (2, 4), (5, 3)]:
            f.top_pixel(x, y, color)
    return f


def pie(taro=False):
    f = Grid()
    f.box(1, 0, 0, 6, 12, 1, '#BB7B33')
    f.box(0, 1, 1, 8, 10, 2, '#E4A74C')
    f.box(1, 1, 3, 6, 10, 1, '#F3BF68')
    for y in [7, 9]:
        f.box(3, y, 3, 2, 1, 1, '#A2662A')
    f.box(0, 0, 0, 8, 5, 4, '#A86BB2' if taro else RED)
    f.box(0, 0, 4, 8, 1, 1, '#D2ABDA' if taro else '#EE6651')
    return f


def hashbrown():
    f = Grid()
    food_box(f, 10, 12, WHITE)
    f.disk(5, 6, 2, 4, 5, 1, '#BD802D')
    f.disk(5, 6, 3, 3.5, 4.5, 1, '#EAB351')
    for x, y in [(3, 4), (6, 3), (4, 7), (6, 8)]:
        f.top_pixel(x, y, '#D19736')
    f.box(0, 10, 1, 10, 2, 2, RED)
    return f


def pancakes():
    f = Grid()
    f.disk(7, 6, 0, 7, 6, 1, WHITE)
    for z in [1, 3, 5]:
        f.disk(7, 6, z, 5.5, 5, 1, '#BA7E35')
        f.disk(7, 6, z + 1, 6, 5.5, 1, '#E8B361')
    f.disk(7, 6, 7, 4, 3, 1, '#A4642E')
    f.box(6, 5, 8, 3, 2, 1, '#FFE6A1')
    return f


def restaurant_kiosk():
    f = Grid()
    f.box(0, 0, 0, 22, 14, 1, '#CBBE9F')
    f.box(1, 1, 1, 20, 11, 11, '#F6E5BC')
    f.box(1, 1, 1, 20, 11, 2, '#B35432')
    f.box(3, 11, 4, 10, 1, 6, '#365A5C')
    f.box(4, 11, 5, 3, 1, 4, '#8CB8B2')
    f.box(9, 11, 5, 3, 1, 4, '#67999A')
    f.box(7, 11, 4, 1, 1, 6, '#FFF0CB')
    f.box(3, 11, 7, 10, 1, 1, '#FFF0CB')
    f.box(3, 12, 3, 10, 1, 1, '#C99C55')
    f.box(15, 11, 1, 4, 1, 9, '#594636')
    f.box(16, 11, 2, 2, 1, 7, '#426C6B')
    f.box(17, 12, 4, 1, 1, 1, YELLOW)
    f.box(20, 3, 4, 1, 6, 6, '#426B69')
    f.box(20, 5, 4, 1, 1, 6, '#FFF0CB')
    f.box(20, 3, 7, 1, 6, 1, '#FFF0CB')
    f.box(0, 0, 12, 22, 13, 2, RED)
    f.box(0, 12, 13, 22, 1, 1, YELLOW)
    for x in range(1, 21, 2):
        f.box(x, 12, 11, 2, 2, 1, RED if x % 4 == 1 else YELLOW)
    f.box(7, 8, 14, 8, 4, 4, RED)
    for row, bits in enumerate(reversed(('01010', '10101', '10101', '10101'))):
        for col, bit in enumerate(bits):
            if bit == '1':
                f.box(8 + col, 11, 14 + row, 1, 1, 1, YELLOW)
    f.box(2, 2, 14, 4, 3, 1, '#B92B1C')
    return f


def tray():
    f = Grid()
    f.box(0, 0, 0, 38, 24, 1, '#B82A20')
    f.box(0, 0, 1, 38, 24, 1, RED)
    f.box(2, 2, 1, 34, 20, 1, '#F8E7BE')
    for x in range(4, 34, 4):
        f.box(x, 20, 1, 2, 1, 1, '#EDD39C')
    return f


def calendar_board():
    f = Grid()
    f.box(0, 0, 0, 22, 4, 2, '#AF3425')
    f.box(0, 0, 2, 22, 3, 18, RED)
    f.box(1, 2, 3, 20, 1, 13, '#FFF3D9')
    f.box(1, 2, 16, 20, 1, 3, YELLOW)
    for x in [4, 16]:
        f.box(x, 1, 18, 2, 2, 2, '#5B5144')
    for row in range(3):
        for col in range(5):
            f.box(2 + col * 4, 3, 5 + row * 3, 2, 1, 1,
                  RED if (row == 1 and col == 3) else '#BCA77D')
    return f


def coupon_ticket():
    f = Grid()
    f.box(0, 0, 0, 10, 2, 6, YELLOW)
    f.box(0, 0, 0, 2, 2, 6, RED)
    f.erase(0, 0, 2, 1, 2, 2)
    f.erase(9, 0, 2, 1, 2, 2)
    for z in [0, 2, 4]:
        f.box(2, 1, z, 1, 1, 1, '#F9E9B9')
    f.logo(4, 1, small=True, color=RED)
    return f


BUILDERS = {
    'burger_big_mac': lambda: burger('big_mac'),
    'burger_mcspicy': lambda: burger('mcspicy'),
    'burger_filet_o_fish': lambda: burger('filet_o_fish'),
    'burger_cheeseburger': lambda: burger('cheeseburger'),
    'burger_double_cheese': lambda: burger('double_cheese'),
    'burger_mccrispy': lambda: burger('mccrispy'),
    'burger_grilled_chicken': lambda: burger('grilled_chicken'),
    'muffin_sausage_egg': lambda: muffin(False),
    'muffin_bacon_egg': lambda: muffin(True),
    'fries_small': lambda: fries('small'),
    'fries_medium': lambda: fries('medium'),
    'fries_large': lambda: fries('large'),
    'drink_cola': lambda: drink('cola'),
    'drink_cola_zero': lambda: drink('cola_zero'),
    'drink_sprite': lambda: drink('sprite'),
    'drink_iced_coffee': lambda: drink('iced_coffee'),
    'drink_iced_latte': lambda: drink('iced_latte'),
    'drink_hot_coffee': hot_coffee,
    'drink_milk': milk,
    'drink_orange_juice': lambda: drink('orange_juice'),
    'nuggets_4': lambda: nuggets(4),
    'nuggets_5': lambda: nuggets(5),
    'nuggets_6': lambda: nuggets(6),
    'nuggets_10': lambda: nuggets(10),
    'chicken_wings_2': wings,
    'corn_cup': corn,
    'apple_slices': apples,
    'salad_bowl': salad,
    'icecream_cone': cone,
    'mcflurry': lambda: icecream('mcflurry'),
    'sundae_chocolate': lambda: icecream('sundae_chocolate'),
    'sundae_strawberry': lambda: icecream('sundae_strawberry'),
    'apple_pie': lambda: pie(False),
    'taro_pie': lambda: pie(True),
    'hashbrown': hashbrown,
    'pancakes': pancakes,
    'restaurant_kiosk': restaurant_kiosk,
    'tray': tray,
    'calendar_board': calendar_board,
    'coupon_ticket': coupon_ticket,
    'burger': lambda: burger('cheeseburger'),
    'fries': lambda: fries('medium'),
    'drink': lambda: drink('cola'),
}


def main():
    models = {}
    for name, builder in BUILDERS.items():
        model = builder()
        models[name] = model.export()
        lo = [min(p[axis] for p in model.cells) for axis in range(3)]
        hi = [max(p[axis] for p in model.cells) + 1 for axis in range(3)]
        size = [b - a for a, b in zip(lo, hi)]
        print(f'{name}: {size[0]} x {size[1]} x {size[2]}, {len(models[name])} cuboids')
    target = Path(__file__).with_name('coarse-models.json')
    target.write_text(json.dumps(models, separators=(',', ':')) + '\n', encoding='utf-8')
    print(f'Wrote {len(models)} original coarse models to {target}')


if __name__ == '__main__':
    main()
