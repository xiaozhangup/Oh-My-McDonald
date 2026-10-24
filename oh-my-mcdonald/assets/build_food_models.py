"""Original integer-grid voxel food models for Oh-My-McDonald.

Run with Python 3.10+ to rebuild geometry, labels, and FOOD_MODELS.md.
Geometry is authored here from primitives; no downloaded artwork is used.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

STEP = 1
RED = "#DA291C"
YELLOW = "#FFC72C"
CREAM = "#FFF2D8"
WHITE = "#FFF9EE"
BUN = ("#D58B37", "#E8A547", "#F1B95E", "#EDB052")
CHICKEN = ("#B87225", "#D29331", "#E2A43D", "#F1BB55")
LETTUCE = ("#459C3A", "#69B94A", "#8CCB56")
BEEF = ("#62351F", "#75442B", "#885036")


def tone(x, y, z, palette, seed=0):
    return palette[((x * 37 + y * 19 + z * 11 + seed * 23) ^ (x * y + z * 5)) % len(palette)]


class Food:
    """Source coordinates use half steps; each occupied cell exports as one voxel."""

    def __init__(self):
        self.cells = {}

    def box(self, x, y, z, w, d, h, color):
        for i in range(round(x * 2), round((x + w) * 2)):
            for j in range(round(y * 2), round((y + d) * 2)):
                for k in range(round(z * 2), round((z + h) * 2)):
                    self.cells[i, j, k] = color

    def cut(self, x, y, z, w, d, h):
        for i in range(round(x * 2), round((x + w) * 2)):
            for j in range(round(y * 2), round((y + d) * 2)):
                for k in range(round(z * 2), round((z + h) * 2)):
                    self.cells.pop((i, j, k), None)

    def disk(self, cx, cy, z, rx, ry, h, color, palette=None, seed=0):
        for i in range(math.floor((cx - rx) * 2), math.ceil((cx + rx) * 2)):
            for j in range(math.floor((cy - ry) * 2), math.ceil((cy + ry) * 2)):
                if ((i / 2 + .25 - cx) / rx) ** 2 + ((j / 2 + .25 - cy) / ry) ** 2 <= 1:
                    for k in range(round(z * 2), round((z + h) * 2)):
                        self.cells[i, j, k] = tone(i, j, k, palette, seed) if palette else color

    def rounded(self, x, y, z, w, d, h, radius, color, palette=None, seed=0):
        for i in range(round(x * 2), round((x + w) * 2)):
            for j in range(round(y * 2), round((y + d) * 2)):
                px, py = i / 2 + .25, j / 2 + .25
                dx = max(x + radius - px, 0, px - (x + w - radius))
                dy = max(y + radius - py, 0, py - (y + d - radius))
                if dx * dx + dy * dy <= radius * radius:
                    for k in range(round(z * 2), round((z + h) * 2)):
                        self.cells[i, j, k] = tone(i, j, k, palette, seed) if palette else color

    def mound(self, cx, cy, z, rx, ry, height, palette, seed=0):
        for k in range(round(height * 2)):
            q = (k + .5) / (height * 2)
            factor = math.sqrt(max(0, 1 - q * q))
            self.disk(cx, cy, z + k / 2, rx * factor, ry * factor, .5,
                      palette[min(len(palette) - 1, int(q * len(palette)))])

    def front(self, x, z, color, thickness=1):
        """Paint the positive-y surface without adding intersecting decals."""
        i, k = round(x * 2), round(z * 2)
        row = [j for a, j, c in self.cells if a == i and c == k]
        if row:
            end = max(row)
            for j in range(end - thickness + 1, end + 1):
                if (i, j, k) in self.cells:
                    self.cells[i, j, k] = color

    def arch(self, cx, bottom, width=7, height=5, color=YELLOW):
        for a in range(round(width * 2)):
            x = a / 2 + .25
            half = width / 2
            arc_x = x % half
            peak = height * math.sqrt(max(0, 1 - ((arc_x - half / 2) / (half / 2)) ** 2))
            for k in range(round(height * 2)):
                z = k / 2 + .25
                if abs(z - peak) <= .65 or (min(arc_x, half - arc_x) < .5 and z < peak):
                    self.front(cx - width / 2 + a / 2, bottom + k / 2, color)

    def export(self):
        """Merge equal integer-grid cells into cuboids with edges up to four voxels."""
        remaining = dict(self.cells)
        out = []
        for x, y, z in sorted(self.cells, key=lambda v: (v[2], v[1], v[0])):
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
            out.append({"origin": [x * STEP, y * STEP, z * STEP],
                        "size": [w * STEP, d * STEP, h * STEP], "color": color})
        return out


def sesame(f, cx, cy, base, rx, ry, height, seed=0):
    points = [(-.60, -.22), (-.3, .25), (.02, -.52), (.45, -.21), (.57, .3),
              (-.44, .57), (.12, .57), (.04, .02), (-.68, -.50), (.35, .67), (.6, -.54)]
    for index, (a, b) in enumerate(points):
        q = math.sqrt(max(0, 1 - a * a - b * b))
        x, y = round((cx + a * rx) * 2) / 2, round((cy + b * ry) * 2) / 2
        z = round((base + height * q) * 2) / 2 - .5
        f.box(x, y, z, 1 if index % 2 else .5, .5 if index % 2 else 1, .5, "#FFF1BD")


def lettuce(f, z, r=8):
    f.disk(9, 9, z, r, r - .5, .5, LETTUCE[1])
    for index, (x, y, w, d) in enumerate([(2, 5, 4, 3), (5, 1, 4, 3), (12, 4, 4, 3),
                                         (10, 13, 4, 3), (3, 12, 4, 3), (13, 9, 4, 3)]):
        f.rounded(x, y, z, w, d, .5 + (index % 2) * .5, 1, LETTUCE[index % 3])
    for x, y in [(3, 6), (6, 2), (13, 10), (5, 13), (11, 14)]:
        f.box(x, y, z + .5, 2, .5, .5, LETTUCE[2])


def cheese(f, z, x=2.5, y=2.5, size=13):
    f.rounded(x, y, z, size, size, .5, .5, YELLOW)
    f.box(x + 2, y + size - .5, z - .5, 3.5, .5, .5, "#F1B521")
    f.box(x + size - .5, y + 3, z - .5, .5, 4, .5, "#F1B521")


def patty(f, z, kind="beef", thick=2):
    palette = BEEF if kind == "beef" else CHICKEN
    f.disk(9, 9, z, 7.6, 7.2, thick, palette[1])
    for i, j, k in list(f.cells):
        if round(z * 2) <= k < round((z + thick) * 2):
            edge = ((i / 2 + .25 - 9) / 7.6) ** 2 + ((j / 2 + .25 - 9) / 7.2) ** 2
            if edge > .65 or k == round((z + thick) * 2) - 1:
                if (i * 13 + j * 7 + k * 3) % 9 < (4 if kind != "beef" else 2):
                    f.cells[i, j, k] = tone(i, j, k, palette)
    if kind == "chicken":
        for x, y in [(2, 6), (3, 12), (13, 3), (14, 11), (8, 1)]:
            f.box(x, y, z + .5, 1.5, 1.5, 1, CHICKEN[2])


def burger(style):
    f = Food()
    f.disk(9, 9, 0, 6.5, 6, .5, "#B96E2D")
    f.disk(9, 9, .5, 7.5, 7, 1.5, BUN[1])
    f.disk(9, 9, 2, 8, 7.5, 1, "#F6CE7A")
    z = 3
    if style == "big_mac":
        lettuce(f, z); z += 1
        cheese(f, z); z += .5
        patty(f, z); z += 2
        f.disk(9, 9, z, 7.6, 7.1, .5, "#EDB967"); z += .5
        f.disk(9, 9, z, 7.7, 7.2, 1.5, "#F5CD83"); z += 1.5
        f.disk(9, 9, z, 7.5, 7, .5, "#BC762F"); z += .5
        lettuce(f, z); z += 1
        f.disk(9, 9, z, 7, 6.5, .5, "#ECA873"); z += .5
        patty(f, z); z += 2
        for x, y in [(6, 12), (11, 6), (5, 5)]:
            f.disk(x, y, z, 2, 1.6, .5, "#71863B")
            f.disk(x, y, z + .5, 1.4, 1, .5, "#A6B85B")
        z += 1
    elif style == "filet_o_fish":
        cheese(f, z); z += .5
        f.rounded(2, 2.5, z, 14, 13, 3, 2, CHICKEN[1]);
        for x, y in [(2.5, 5), (13, 9), (5, 13), (9, 3)]:
            f.box(x, y, z + 1, 1.5, 1, .5, CHICKEN[3])
        z += 3
        f.disk(9, 9, z, 6.5, 6, 1, CREAM); z += 1
    elif style in ("mcspicy", "mccrispy", "grilled_chicken"):
        f.disk(9, 9, z, 7, 6.5, .5, "#F8E0B8"); z += .5
        patty(f, z, "chicken", 3); z += 3
        if style == "mccrispy":
            cheese(f, z); z += .5
        if style == "grilled_chicken":
            for a in range(4, 14, 3):
                f.box(a, 5, z - .5, .5, 8, .5, "#8A4825")
            for x, y in [(6, 8), (11, 10)]:
                f.disk(x, y, z, 3.5, 3, .5, "#E14C31")
            z += .5
        lettuce(f, z); z += 1
        f.disk(9, 9, z, 6.5, 6, .5, CREAM); z += .5
    else:
        for _ in range(2 if style == "double_cheese" else 1):
            patty(f, z); z += 2
            cheese(f, z); z += .5
        f.disk(9, 9, z, 6, 5.5, .5, "#D74A2A")
        for x, y in [(5, 9), (10, 12), (12, 5)]:
            f.disk(x, y, z + .5, 1.5, 1.3, .5, "#769148")
        z += 1
    f.disk(9, 9, z, 8, 7.5, 1, "#D68D3B"); z += 1
    f.mound(9, 9, z, 8, 7.5, 4.5, BUN)
    if style != "filet_o_fish":
        sesame(f, 9, 9, z, 8, 7.5, 4.5)
    return f


def muffin(bacon=False):
    f = Food()
    f.disk(8, 8, 0, 6.5, 6, 1, "#C99F68")
    f.disk(8, 8, 1, 7.5, 7, 2, "#E8C793")
    f.disk(8, 8, 3, 7, 6.5, .5, "#B7894C")
    f.disk(8, 8, 3.5, 6.5, 6, 2, "#785033")
    f.rounded(1.5, 1.5, 5.5, 13, 13, .5, 1, YELLOW)
    f.disk(8, 8, 6, 6.5, 6, 2.5, "#FFF4DB")
    f.disk(8.5, 8, 8, 3, 2.5, 1, "#F6B528")
    if bacon:
        for x in [3, 7, 11]:
            f.box(x, .5, 8.5, 1.5, 15, .5, "#AA5038")
            f.box(x + .5, 1, 9, .5, 14.5, .5, "#E2A27E")
            f.box(x, 14.5, 8, 1.5, 1, .5, "#A94B35")
    f.disk(8, 8, 9.5, 7.5, 7, 2.5, "#E6C38F")
    f.mound(8, 8, 12, 7.5, 7, 1.5, ("#D6AD71", "#EBD0A1"))
    for i, j, k in list(f.cells):
        if k >= 24 and (i * 17 + j * 13) % 23 < 3:
            f.cells[i, j, k] = "#AF824C"
    return f


def fries(size):
    f = Food()
    width, depth, height = {"small": (12, 8, 17), "medium": (14, 9, 20), "large": (16, 10, 23)}[size]
    cx, cy = width / 2, depth / 2
    for k in range(22):
        z = k / 2
        half = width / 2 - 1.5 + z / 8
        halfd = depth / 2 - 1 + z / 12
        for i in range(round((cx - half) * 2), round((cx + half) * 2)):
            for j in range(round((cy - halfd) * 2), round((cy + halfd) * 2)):
                px, py = i / 2 + .25, j / 2 + .25
                side = abs(px - cx) > half - .6
                back = py < cy - halfd + .6
                front = py > cy + halfd - .6
                lip = 7.5 + 3 * (abs(px - cx) / half) ** 1.5
                if z < 1 or side or back or (front and z < lip):
                    color = RED if front else ("#B91F17" if side else "#E43B29")
                    f.cells[i, j, k] = color
    for row in range(3):
        for col in range(int((width - 3) / 2)):
            x = 2 + col * 2 + .5 * (row % 2)
            y = 1.5 + row * 2
            tip = height - ((col * 3 + row * 5) % 5)
            f.box(x, y, 5, 1.5, 1.5, tip - 5, "#EDAB28")
            f.box(x, y + 1, 5, 1.5, .5, tip - 5, "#FFD34A")
            f.box(x, y, tip - 1, 1.5, 1.5, 1, "#FFE16B")
            if (col + row) % 3 == 0:
                f.box(x + .5, y + 1, 10, .5, .5, 2, "#F4BC35")
    f.arch(cx, 2, min(width - 4, 8), 4)
    f.box(width - 1, depth - 1, 1.5, .5, .5, 5.5, "#F04B30")
    return f


def cup_body(f, height, radius, color, stripe=None):
    cx = cy = radius + 1
    for k in range(round(height * 2)):
        z = k / 2
        r = radius - 1.5 + z / height * 1.5
        c = color
        if stripe and stripe[0] <= z < stripe[1]:
            c = stripe[2]
        f.disk(cx, cy, z, r, r, .5, c)
    f.disk(cx, cy, 0, radius - 1.2, radius - 1.2, .5, "#E3D9C9")
    return cx, cy


def cold_drink(kind):
    f = Food()
    radius, height = 6, 16
    colors = {"cola": RED, "cola_zero": "#FFF6E9", "sprite": "#4BA866",
              "iced_coffee": "#9A6240", "iced_latte": "#D7AB7E", "orange_juice": "#F1A927"}
    color = colors[kind]
    center = radius + 1
    cup_body(f, height, radius, color)
    if kind in ("iced_coffee", "iced_latte", "orange_juice"):
        for k in range(2, 31):
            r = radius - 1.5 + k / 2 / height * 1.5
            for x in [3.5, 10.5]:
                for y in [4, 9.5]:
                    if ((x - center) / r) ** 2 + ((y - center) / r) ** 2 < 1:
                        f.box(x, y, k / 2, .5, .5, .5, "#E8D7BE")
        f.disk(center, center, 16, radius, radius, .5, "#E7E9D9")
        f.disk(center, center, 16.5, radius - .5, radius - .5, .5, "#B5794E" if kind != "orange_juice" else "#F6BD3E")
        for x, y, w, d in [(4, 4, 2, 2), (8, 5, 2.5, 2), (5.5, 9, 2, 2), (9, 9, 1.5, 2)]:
            f.rounded(x, y, 17, w, d, .5, .5, "#DDE5DB")
            f.box(x, y, 17.5, w - .5, .5, .5, "#FFF8E7")
        f.box(6, 7, 17, 1, 1, 7, "#C7A876" if kind != "orange_juice" else "#F9F1DC")
        f.box(6, 7, 23.5, 1, 1, .5, "#866442")
        if kind == "iced_latte":
            for i, j, k in list(f.cells):
                if k < 11 and f.cells[i, j, k] == color:
                    f.cells[i, j, k] = "#EEDBC0"
        for x in [3.5, 10]:
            for k in range(5, 29):
                f.front(x, k / 2, "#F4EAD4" if k % 7 else "#FFF9E8")
        f.arch(center, 5, 6, 4, "#FFF3D9")
    else:
        if kind == "cola_zero":
            for x in range(5, 23):
                for z in range(7, 19):
                    f.front(x / 2, z / 2, "#23262B")
            f.arch(center, 4, 6, 4, RED)
        else:
            f.arch(center, 5, 7, 5)
        f.disk(center, center, 16, radius + .5, radius + .5, 1, WHITE)
        f.disk(center, center, 17, radius, radius, .5, "#ECE5D9")
        f.disk(center, center, 17.5, radius - 1, radius - 1, .5, "#FFFDF5")
        f.box(6.5, 6, 18, 1, 1, 6, WHITE)
        for z in [19, 21, 23]:
            f.box(6.5, 6, z, 1, 1, .5, RED)
        f.box(6.5, 6, 24, 1, 1, .5, "#9C3023")
    return f


def hot_coffee():
    f = Food()
    cx, cy = cup_body(f, 14, 6, "#704631", (4, 9.5, "#BB8D5E"))
    f.arch(cx, 5, 6, 4, WHITE)
    f.disk(cx, cy, 14, 6.5, 6.5, 1, "#372D27")
    f.disk(cx, cy, 15, 6, 6, 1, "#4A3A30")
    f.disk(cx, cy, 16, 5.5, 5.5, .5, "#5B473A")
    f.rounded(5, 10, 16.5, 4, 1.5, .5, .5, "#281F1B")
    f.box(6, 4, 16.5, 2, .5, .5, "#776253")
    return f


def milk():
    f = Food()
    f.box(1, 1, 0, 10, 9, 14, "#FFF7E9")
    f.box(1, 1, 0, 10, 9, 2, "#478BB9")
    f.box(1, 9.5, 3, 10, .5, 4, "#6AAED4")
    f.box(10.5, 1, 3, .5, 9, 4, "#498EBA")
    for k in range(8):
        f.box(1 + k / 2, 1, 14 + k / 2, 10 - k, 9, .5, "#DFEAF0" if k % 2 else "#FAF8EC")
    f.box(4.5, 1, 18, 3, 9, .5, "#438AB5")
    f.box(5, 1, 18.5, 2, 9, 1, "#F9F7EA")
    f.arch(6, 8, 6, 4, RED)
    for x in [2, 3.5, 5, 6.5, 8, 9]:
        f.front(x, 2, "#2E6B95")
    return f


def nugget(f, cx, cy, z, rx=3, ry=2.5, seed=0):
    f.disk(cx, cy, z, rx * .8, ry * .8, .5, "#A96725")
    f.disk(cx, cy, z + .5, rx, ry, 1.5, CHICKEN[1])
    f.mound(cx, cy, z + 2, rx, ry, 1.5, CHICKEN)
    for i, j, k in list(f.cells):
        if z * 2 + 1 <= k < z * 2 + 7 and abs(i / 2 - cx) < rx and abs(j / 2 - cy) < ry:
            if (i * 7 + j * 13 + seed * 11) % 17 < 3:
                f.cells[i, j, k] = tone(i, j, k, CHICKEN, seed)


def tray(f, w, d, color=RED, lid=False):
    f.rounded(0, 0, 0, w, d, 1, 1, color)
    f.box(1, 1, 1, w - 2, d - 2, 1, "#F9E6BF")
    f.box(0, 0, 1, 1, d, 3, color)
    f.box(w - 1, 0, 1, 1, d, 3, "#BB261D")
    f.box(1, d - 1, 1, w - 2, 1, 3, color)
    f.box(1, 0, 1, w - 2, 1, 3, color)
    if lid:
        f.rounded(0, 0, 4, w, 1, 8, 0.5, "#EDC963")
        f.box(1, .5, 5, w - 2, .5, 6, WHITE)
        f.box(1, .5, 10.5, w - 2, .5, .5, "#E1B852")


def nuggets(count):
    f = Food()
    tray(f, 19, 14, "#F2C230" if count == 10 else RED, True)
    positions = {
        4: [(5.5, 4, 2), (13, 4, 2), (5.5, 9.5, 2), (13, 9.5, 2)],
        5: [(6, 4, 2), (13, 4, 2), (4.5, 9.5, 2), (10, 9.5, 2), (15, 9.5, 2)],
        6: [(4.5, 4, 2), (10, 4, 2), (15, 4, 2), (4.5, 9.5, 2), (10, 9.5, 2), (15, 9.5, 2)],
        10: [(4.5, 4, 2), (10, 4, 2), (15, 4, 2), (4.5, 9.5, 2), (10, 9.5, 2), (15, 9.5, 2)],
    }
    for index, (x, y, z) in enumerate(positions[count]):
        nugget(f, x, y, z, 2.7, 2.3, index)
    if count == 10:
        for index, (x, y) in enumerate([(6.5, 6.5), (12.5, 6.5), (7, 10), (13, 10)]):
            nugget(f, x, y, 5, 2.7, 2.2, index + 6)
    f.arch(9.5, 1.5, 5, 2)
    return f


def wings():
    f = Food()
    tray(f, 19, 14, "#F5D15B")
    for index, (cx, cy) in enumerate([(6, 5), (12.5, 9)]):
        f.disk(cx, cy, 2, 3.5, 2.5, 2, "#B66529")
        f.mound(cx, cy, 4, 3.5, 2.5, 3, CHICKEN)
        f.disk(cx + 3, cy - 1, 3, 2.8, 1.8, 2, "#C47B2F")
        f.mound(cx + 3, cy - 1, 5, 2.8, 1.8, 1.5, CHICKEN)
        f.box(cx + 4.5, cy - 1.5, 4, 2, 1.5, 1.5, "#E8CBA0")
        f.box(cx + 6, cy - 2, 4, 1, 2.5, 1.5, "#FFF0CF")
        for x, y in [(cx - 1.5, cy), (cx + 1, cy + 1), (cx + 2.5, cy - 1)]:
            f.box(x, y, 6, 1, 1, .5, "#F0AD48")
    return f


def corn():
    f = Food()
    cx, cy = cup_body(f, 10, 6, YELLOW, (2, 5, "#6BA63D"))
    f.arch(cx, 5, 6, 4, RED)
    f.disk(cx, cy, 10, 6.5, 6.5, .5, "#FFF0B7")
    f.disk(cx, cy, 10.5, 5.5, 5.5, .5, "#C6932C")
    for row in range(5):
        for col in range(5):
            x, y = 3 + col * 2, 3 + row * 2
            if (x - 7) ** 2 + (y - 7) ** 2 < 26:
                f.rounded(x - .5, y - .5, 11, 1.5, 1.5, 1 + ((row + col) % 2) * .5, .5,
                          "#FFDB54" if (row + col) % 3 else "#F5BC31")
                f.box(x, y, 12, .5, .5, .5, "#FFE77E")
    return f


def apples():
    f = Food()
    tray(f, 18, 13, "#F7E4BD")
    for row in range(3):
        cx, cy = 5 + row * 4, 4 + row * 2
        for i in range(-8, 9):
            for k in range(1, 10):
                d = (i / 2 / 4.5) ** 2 + (k / 2 / 5) ** 2
                if d <= 1:
                    color = "#D93832" if d > .82 else "#FFF0C3"
                    f.box(cx + i / 2, cy, 2 + k / 2, .5, 2, .5, color)
        f.box(cx - .5, cy + .5, 3, 1, 1, .5, "#DDB56A")
    f.box(0, 11, 3, 18, 2, 3.5, RED)
    f.arch(9, 3.5, 6, 2.5)
    return f


def salad():
    f = Food()
    for k in range(15):
        r = 6 + k / 5
        f.disk(10, 9, k / 2, r, r * .85, .5, "#EAD5B5")
    f.disk(10, 9, 7.5, 9.5, 8, .5, "#FFF1D8")
    f.disk(10, 9, 8, 8.5, 7, .5, "#477F35")
    for index, (x, y) in enumerate([(4, 7), (7, 3.5), (12, 3), (15, 6), (15, 11), (10, 14), (5, 12), (9, 8)]):
        f.mound(x, y, 8.5, 3, 2.5, 2, LETTUCE)
        f.box(x - 1, y, 10, 2, .5, .5, "#A7D977")
    for x, y in [(6, 7), (13, 6), (11, 12)]:
        f.disk(x, y, 10.5, 2, 1.8, 1, "#D9422D")
        f.disk(x, y, 11.5, 1.5, 1.3, .5, "#ED6942")
        f.box(x, y, 12, .5, .5, .5, "#FFC871")
    for x, y in [(4, 10), (9, 4), (14, 10)]:
        f.disk(x, y, 10.5, 1.5, 1.5, .5, "#4E8C39")
        f.disk(x, y, 11, 1, 1, .5, "#C6D991")
    for x, y in [(8, 11), (11, 7), (7, 5)]:
        f.box(x, y, 11, 1.5, 1.5, 1, "#D9AA52")
    return f


def cone():
    f = Food()
    for k in range(24):
        r = 1.5 + k / 7
        f.disk(7, 7, k / 2, r, r, .5, "#C98B43")
    for i, j, k in list(f.cells):
        if ((i + j + k) % 8 < 2 or (i - j + k) % 8 < 2):
            f.cells[i, j, k] = "#E8B366"
    f.disk(7, 7, 12, 5, 5, 1, "#EEC488")
    for z, r, dx, dy in [(13, 5.5, 0, 0), (15, 4.8, .5, 0), (17, 3.8, 0, .5),
                         (19, 2.8, -.5, 0), (21, 1.8, 0, 0), (23, .8, .5, 0)]:
        f.disk(7 + dx, 7 + dy, z, r, r, .5, "#E8DDC6")
        f.mound(7 + dx, 7 + dy, z + .5, r, r, 2, ("#FFF3D9", "#FFFBEA"))
    return f


def icecream(kind):
    f = Food()
    radius, height = (6.5, 10) if kind == "mcflurry" else (5.5, 9)
    cx, cy = cup_body(f, height, radius, WHITE if kind == "mcflurry" else "#E5D9C4",
                      (3, 6, RED if kind == "mcflurry" else "#EEE8D5"))
    f.arch(cx, 3.5, 6, 3, YELLOW if kind == "mcflurry" else RED)
    f.disk(cx, cy, height, radius + .5, radius + .5, .5, WHITE)
    f.mound(cx, cy, height + .5, radius - .5, radius - .5, 4, ("#F3E8D1", "#FFF7E4"))
    if kind == "mcflurry":
        for index, (dx, dy) in enumerate([(-3, -2), (0, -4), (3, -2), (-4, 1), (0, 0),
                                         (3, 2), (-1, 4), (-2, 2), (1, -2), (4, 0)]):
            radial = ((dx + .5) / (radius - .5)) ** 2 + ((dy + .5) / (radius - .5)) ** 2
            z = math.floor((height + .5 + 4 * math.sqrt(max(0, 1 - radial))) * 2) / 2
            f.box(cx + dx, cy + dy, z, 1, 1, .5, "#4A3029")
            f.box(cx + dx, cy + dy, z + .5, .5, .5, .5, "#6A493B")
        f.box(cx - 1, cy - 2, height + 2, 1, 1, 10, "#F6EFE1")
        f.box(cx - 1.5, cy - 2, height + 10, 2, 1, 3, "#E5DDCF")
    else:
        sauce = "#643C2A" if kind == "sundae_chocolate" else "#CD433E"
        for z, r, dx in [(height + 2, 4.5, 0), (height + 4, 3, .5), (height + 6, 1.5, 0)]:
            f.mound(cx + dx, cy, z, r, r, 2, ("#FFF5DF", "#FFFAEA"))
        top = {}
        for i, j, k in f.cells:
            if k >= round((height + 1) * 2):
                top[i, j] = max(k, top.get((i, j), k))
        for (i, j), k in top.items():
            x, y = i / 2 + .25 - cx, j / 2 + .25 - cy
            if abs(x + .45 * y) < .8 or abs(x - .6 * y - 2) < .65:
                f.cells[i, j, k] = sauce
                if (i, j, k - 1) in f.cells:
                    f.cells[i, j, k - 1] = sauce
        for dx, low, high in [(-2, 1.5, 5), (1.5, .5, 4.5), (3, 2, 3.5)]:
            for k in range(round((height + low) * 2), round((height + high) * 2)):
                f.front(cx + dx, k / 2, sauce)
                f.front(cx + dx + .5, k / 2, sauce)
    return f


def pie(taro=False):
    f = Food()
    f.rounded(2, 1, 0, 10, 18, 1, 1, "#AD6C2D")
    f.rounded(1, 0, 1, 12, 20, 3, 2, "#D3933F")
    f.rounded(1.5, .5, 4, 11, 19, 1.5, 2, "#E8AD54")
    f.rounded(2, 1, 5.5, 10, 18, .5, 1.5, "#F3BF6B")
    for y in [3, 6, 9, 12, 15, 18]:
        f.box(1.5, y, 4.5, 1, 1, 1, "#C98535")
        f.box(11.5, y, 4.5, 1, 1, 1, "#C98535")
    for y in [5, 9, 13, 17]:
        f.box(5, y, 5.5, 4, .5, .5, "#9A602B")
    f.box(0, 0, 0, 14, 10, 6.5, "#A265AA" if taro else RED)
    f.box(0, 0, 6.5, 1, 10, .5, "#D9ACDC" if taro else "#EF6550")
    f.box(13, 0, 6.5, 1, 10, .5, "#8A4D91" if taro else "#B8221A")
    f.arch(7, 1, 6, 4)
    return f


def hashbrown():
    f = Food()
    tray(f, 15, 19, WHITE)
    f.rounded(2, 2, 2, 11, 15, 2, 4, "#B97B2D")
    f.rounded(2, 2, 4, 11, 15, 1, 4, "#E3A43D")
    f.rounded(2.5, 2.5, 5, 10, 14, .5, 3.5, "#F0BB58")
    for i, j, k in list(f.cells):
        if k >= 8 and (i * 13 + j * 19) % 13 < 3:
            f.cells[i, j, k] = tone(i, j, k, CHICKEN)
    f.box(0, 15, 0, 15, 4, 4, RED)
    f.arch(7.5, 1, 5, 2)
    return f


def pancakes():
    f = Food()
    f.disk(10, 9, 0, 10, 9, .5, "#D5C8B3")
    f.disk(10, 9, .5, 9.5, 8.5, .5, WHITE)
    for z in [1, 3.5, 6]:
        f.disk(10, 9, z, 7.5, 7, .5, "#B47B38")
        f.disk(10, 9, z + .5, 8, 7.5, 1.5, "#DEAA59")
        f.disk(10, 9, z + 2, 7.5, 7, .5, "#EFC276")
    f.disk(10, 9, 8.5, 5.5, 4.5, .5, "#AC6730")
    f.box(8, 7, 9, 4, 3, 1, "#FFE596")
    f.box(8.5, 7, 10, 3, 2.5, .5, "#FFF0BA")
    for x, y, h in [(5, 12, 2), (14, 10, 3), (9, 15, 4)]:
        f.box(x, y, 8.5 - h, 1.5, 1, h, "#AC6730")
    return f


BUILDERS = [
    ("burger_big_mac", "巨无霸双层汉堡", lambda: burger("big_mac"), "三片芝麻面包、双层牛肉、芝士、酸黄瓜与生菜"),
    ("burger_mcspicy", "香辣鸡腿堡", lambda: burger("mcspicy"), "不规则炸鸡边缘、卷叶生菜和芝麻圆顶"),
    ("burger_filet_o_fish", "麦香鱼", lambda: burger("filet_o_fish"), "软面包圆顶、方形鱼排、塔塔酱和半融芝士"),
    ("burger_cheeseburger", "吉士汉堡", lambda: burger("cheeseburger"), "单层牛肉、番茄酱、酸黄瓜和垂边芝士"),
    ("burger_double_cheese", "双层吉士汉堡", lambda: burger("double_cheese"), "双层牛肉与双层芝士"),
    ("burger_mccrispy", "脆鸡芝士堡", lambda: burger("mccrispy"), "炸鸡、芝士和生菜"),
    ("burger_grilled_chicken", "板烧鸡腿堡", lambda: burger("grilled_chicken"), "烤纹鸡腿、番茄和生菜"),
    ("muffin_sausage_egg", "猪柳蛋麦满分", lambda: muffin(False), "英式松饼、猪柳、煎蛋和芝士"),
    ("muffin_bacon_egg", "培根蛋麦满分", lambda: muffin(True), "松饼表面烘烤斑点、培根和煎蛋"),
    ("fries_small", "小薯条", lambda: fries("small"), "小号折边纸盒、金色拱形和独立薯条"),
    ("fries_medium", "中薯条", lambda: fries("medium"), "中号开口纸盒与错落薯条"),
    ("fries_large", "大薯条", lambda: fries("large"), "加宽红盒、前沿凹口和长薯条"),
    ("drink_cola", "可口可乐", lambda: cold_drink("cola"), "红色锥形杯、金色拱形、压纹杯盖和条纹吸管"),
    ("drink_cola_zero", "无糖可乐", lambda: cold_drink("cola_zero"), "白杯、黑色标带、红色拱形和条纹吸管"),
    ("drink_sprite", "雪碧", lambda: cold_drink("sprite"), "绿色锥形杯与白色杯盖"),
    ("drink_iced_coffee", "冰美式", lambda: cold_drink("iced_coffee"), "浅色杯壁反光、褐色咖啡、冰块与细吸管"),
    ("drink_iced_latte", "冰拿铁", lambda: cold_drink("iced_latte"), "牛奶底层、咖啡层、冰块与杯壁反光"),
    ("drink_hot_coffee", "热咖啡", hot_coffee, "咖啡纸杯、隔热杯套、深色杯盖和饮口"),
    ("drink_milk", "牛奶盒", milk, "蓝白纸盒、屋脊封口和正面拱形"),
    ("drink_orange_juice", "橙汁", lambda: cold_drink("orange_juice"), "橙色果汁、冰块和浅色杯壁"),
    ("nuggets_4", "四块麦乐鸡", lambda: nuggets(4), "打开的红色纸盒与分开放置的四块鸡块"),
    ("nuggets_5", "五块麦乐鸡", lambda: nuggets(5), "两排错列摆放的五块鸡块"),
    ("nuggets_6", "六块麦乐鸡", lambda: nuggets(6), "打开的纸盒、六块圆角鸡块和外皮颗粒"),
    ("nuggets_10", "十块麦乐鸡", lambda: nuggets(10), "黄色纸盒与分层叠放的十块鸡块"),
    ("chicken_wings_2", "双份鸡翅", wings, "两只分节鸡翅、骨端和黄色纸托"),
    ("corn_cup", "玉米杯", corn, "黄绿纸杯与逐颗建模的玉米粒"),
    ("apple_slices", "苹果片", apples, "三片带红皮的苹果和红色纸套"),
    ("salad_bowl", "蔬菜沙拉", salad, "椭圆碗、生菜、番茄、黄瓜和面包丁"),
    ("icecream_cone", "原味甜筒", cone, "网格华夫筒、六层旋转奶油和尖顶"),
    ("mcflurry", "奥利奥麦旋风", lambda: icecream("mcflurry"), "红白纸杯、饼干碎和加宽柄勺"),
    ("sundae_chocolate", "巧克力新地", lambda: icecream("sundae_chocolate"), "奶油旋顶与巧克力淋酱"),
    ("sundae_strawberry", "草莓新地", lambda: icecream("sundae_strawberry"), "奶油旋顶与草莓淋酱"),
    ("apple_pie", "苹果派", lambda: pie(False), "红色纸套、酥皮压边和排气切口"),
    ("taro_pie", "香芋派", lambda: pie(True), "紫色纸套、酥皮压边和排气切口"),
    ("hashbrown", "脆薯饼", hashbrown, "椭圆薯饼、土豆颗粒和红白纸托"),
    ("pancakes", "热香饼", pancakes, "三层香饼、糖浆、黄油和椭圆餐盘"),
]


def main():
    models, rows, footprints = {}, [], []
    for key, label, builder, details in BUILDERS:
        food = builder()
        models[key] = food.export()
        mins = [min(v[axis] for v in food.cells) * STEP for axis in range(3)]
        maxs = [(max(v[axis] for v in food.cells) + 1) * STEP for axis in range(3)]
        size = [hi - lo for lo, hi in zip(mins, maxs)]
        cx, cy = (mins[0] + maxs[0]) / 2, (mins[1] + maxs[1]) / 2
        projection = []
        for part in models[key]:
            x, y, z = part["origin"]
            w, d, h = part["size"]
            for a in (x, x + w):
                for b in (y, y + d):
                    for c in (z, z + h):
                        projection.append(((a - cx - b + cy) * math.sqrt(3) / 2,
                                           (a - cx + b - cy) / 2 - c))
        left, top = (min(p[axis] for p in projection) for axis in range(2))
        right, bottom = (max(p[axis] for p in projection) for axis in range(2))
        footprints.append((key, size, left, top, right, bottom))
        dimensions = " × ".join(str(n) for n in size)
        projected = f"{right - left:.2f} × {bottom - top:.2f}"
        rows.append(f"| `{key}` | {label} | {dimensions} | {projected} | {len(models[key])} | {details} |")
    output = Path(__file__).with_name("food-models.json")
    output.write_text(json.dumps(models, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    Path(__file__).with_name("food-labels.json").write_text(
        json.dumps({key: label for key, label, _, _ in BUILDERS}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    world_max = [max(item[1][axis] for item in footprints) for axis in range(3)]
    max_width = max(item[4] - item[2] for item in footprints)
    max_height = max(item[5] - item[3] for item in footprints)
    common_left = min(item[2] for item in footprints)
    common_top = min(item[3] for item in footprints)
    common_right = max(item[4] for item in footprints)
    common_bottom = max(item[5] for item in footprints)
    doc = f"""# 餐品体素模型

由 `build_food_models.py` 生成，共 {len(models)} 种。几何与配色在本地原创，构建只使用 Python 标准库。

运行 `python oh-my-mcdonald/assets/build_food_models.py` 重建 `food-models.json`、`food-labels.json` 和本说明。

全部模型使用同一个 1 × 1 × 1 体素网格。`origin: [x,y,z]` 与 `size: [w,d,h]` 的数值均为整数；z 轴向上，地面为 z=0，`color` 为实色十六进制颜色。每个模型内部的 cuboid 体积互不相交，同色相邻体素合并为边长最多 4 格的 cuboid。

源码造型参数保留半单位的设计坐标：参数乘 2 后写入整数 cell 索引，导出时每个 cell 占据一个世界体素，`STEP=1`。所有餐品共用此转换，不按单个模型调整比例。

展示使用同一等距镜头与同一比例，每格 4 像素。正 x、正 y 面可见，投影为 `u=(x-y)*sqrt(3)/2`、`v=(x+y)*0.5-z`。各模型按 x、y 包围盒中心对齐；该中心在 z=0 的投影是统一地面基线。小薯、中薯、大薯保留各自体素尺寸。

最大世界包围尺寸分别为 x={world_max[0]}、y={world_max[1]}、z={world_max[2]} 格。单个模型最大投影宽度为 {max_width:.2f} 格，最大投影高度为 {max_height:.2f} 格。

将全部模型按共同地面基线展示时，投影边界为左右 {common_left:.2f} 至 {common_right:.2f} 格，上下 {common_top:.2f} 至 {common_bottom:.2f} 格。每格 4 像素对应 {4 * (common_right - common_left):.2f} × {4 * (common_bottom - common_top):.2f} 像素；顶部至基线为 {-4 * common_top:.2f} 像素，基线至底部为 {4 * common_bottom:.2f} 像素。

玻璃杯用浅色边缘与反光表现杯壁。红色包装使用 #DA291C，黄色包装使用 #FFC72C。

尺寸列依次为 x 宽度、y 深度和 z 高度。投影尺寸为模型实际几何在统一镜头下的宽度和高度，单位均为体素格。

| 模型键 | 餐品 | 世界尺寸 | 投影尺寸 | Cuboid 数量 | 结构细节 |
| --- | --- | --- | --- | ---: | --- |
"""
    Path(__file__).with_name("FOOD_MODELS.md").write_text(doc + "\n".join(rows) + "\n", encoding="utf-8")
    print(f"Wrote {len(models)} integer-grid models, {sum(map(len, models.values())):,} cuboids to {output}")
    print(f"World maxima: {world_max}; maximum projected size: {max_width:.2f} x {max_height:.2f}")
    print(f"Common baseline frame at 4 px/voxel: {4 * (common_right - common_left):.2f} x "
          f"{4 * (common_bottom - common_top):.2f}; above {-4 * common_top:.2f}, below {4 * common_bottom:.2f}")


if __name__ == "__main__":
    main()
