"""Inventory icons (32x32) of the small anomalies, drawn here (no source art).

    python3 tools/make_item_icons.py
"""

import os

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "Contents/mods/SCPFoundation/42/media/textures")
S = 8                     # drawn 8x bigger, then reduced
OUTLINE = (20, 20, 22, 255)


def new():
    return Image.new("RGBA", (32 * S, 32 * S), (0, 0, 0, 0))


def save(img, name):
    img.resize((32, 32), Image.LANCZOS).save(os.path.join(OUT, f"Item_{name}.png"))


def r(v):
    return [c * S for c in v]


def scp207():
    img = new(); d = ImageDraw.Draw(img)
    d.rounded_rectangle(r([10, 9, 22, 30]), 2 * S, fill=(70, 30, 20, 255), outline=OUTLINE, width=S)
    d.polygon(r([13, 9, 19, 9, 17, 3, 15, 3]), fill=(80, 36, 24, 255), outline=OUTLINE)
    d.rectangle(r([14, 1, 18, 3]), fill=(200, 30, 30, 255), outline=OUTLINE, width=S // 2)
    d.rectangle(r([10, 16, 22, 22]), fill=(200, 30, 30, 255))
    d.text((11 * S, 16 * S), "207", fill=(255, 255, 255, 255))
    d.line(r([12, 11, 12, 28]), fill=(140, 90, 70, 200), width=S)
    save(img, "SCP_207")


def scp268():
    img = new(); d = ImageDraw.Draw(img)
    d.pieslice(r([5, 8, 27, 28]), 180, 360, fill=(60, 64, 70, 255), outline=OUTLINE, width=S)
    d.rounded_rectangle(r([3, 17, 30, 21]), S, fill=(48, 50, 56, 255), outline=OUTLINE, width=S)
    d.ellipse(r([14, 9, 18, 13]), fill=(200, 200, 205, 255))
    save(img, "SCP_268")


def scp330():
    img = new(); d = ImageDraw.Draw(img)
    for i, c in enumerate([(230, 60, 90), (90, 170, 240), (250, 200, 60), (120, 210, 110), (220, 120, 220)]):
        x = 7 + i * 4
        d.ellipse(r([x, 9 + (i % 2) * 2, x + 6, 15 + (i % 2) * 2]), fill=c + (255,), outline=OUTLINE)
    d.pieslice(r([3, 2, 29, 30]), 0, 180, fill=(225, 230, 235, 255), outline=OUTLINE, width=S)
    d.line(r([5, 16, 27, 16]), fill=OUTLINE, width=S)
    save(img, "SCP_330")


def candy():
    img = new(); d = ImageDraw.Draw(img)
    d.polygon(r([4, 10, 10, 16, 4, 22]), fill=(240, 120, 160, 255), outline=OUTLINE)
    d.polygon(r([28, 10, 22, 16, 28, 22]), fill=(240, 120, 160, 255), outline=OUTLINE)
    d.ellipse(r([9, 10, 23, 22]), fill=(230, 60, 110, 255), outline=OUTLINE, width=S)
    d.arc(r([11, 12, 21, 20]), 200, 300, fill=(255, 200, 220, 255), width=S)
    save(img, "SCP_330_Candy")


def scp005():
    img = new(); d = ImageDraw.Draw(img)
    gold = (215, 175, 70, 255)
    d.ellipse(r([3, 3, 13, 13]), outline=OUTLINE, width=3 * S)
    d.ellipse(r([3, 3, 13, 13]), outline=gold, width=2 * S)
    d.line(r([11, 11, 27, 27]), fill=OUTLINE, width=4 * S)
    d.line(r([11, 11, 27, 27]), fill=gold, width=2 * S)
    for k in (0, 4):
        d.line(r([22 - k, 26 - k, 26 - k, 22 - k]), fill=gold, width=2 * S)
        d.line(r([22 - k, 26 - k, 20 - k, 28 - k]), fill=gold, width=2 * S)
    save(img, "SCP_005_Key")


def scp109():
    img = new(); d = ImageDraw.Draw(img)
    d.ellipse(r([5, 8, 27, 30]), fill=(86, 98, 60, 255), outline=OUTLINE, width=S)
    d.ellipse(r([9, 12, 23, 26]), outline=(110, 124, 80, 255), width=S)
    d.rectangle(r([13, 3, 19, 9]), fill=(60, 60, 64, 255), outline=OUTLINE, width=S)
    d.ellipse(r([22, 4, 29, 11]), fill=(90, 160, 230, 255))
    save(img, "SCP_109_Canteen")


def scp458():
    img = new(); d = ImageDraw.Draw(img)
    d.polygon(r([2, 14, 16, 8, 30, 14, 16, 20]), fill=(210, 180, 130, 255), outline=OUTLINE)
    d.polygon(r([2, 14, 16, 20, 16, 28, 2, 22]), fill=(180, 150, 105, 255), outline=OUTLINE)
    d.polygon(r([30, 14, 16, 20, 16, 28, 30, 22]), fill=(160, 130, 90, 255), outline=OUTLINE)
    d.ellipse(r([11, 11, 21, 17]), fill=(200, 40, 40, 255))
    save(img, "SCP_458_PizzaBox")


def scp427():
    img = new(); d = ImageDraw.Draw(img)
    d.line(r([16, 2, 9, 12]), fill=(200, 180, 120, 255), width=S)
    d.line(r([16, 2, 23, 12]), fill=(200, 180, 120, 255), width=S)
    d.ellipse(r([7, 11, 25, 29]), fill=(150, 120, 60, 255), outline=OUTLINE, width=S)
    d.ellipse(r([11, 15, 21, 25]), fill=(70, 150, 120, 255), outline=(40, 60, 50, 255), width=S)
    save(img, "SCP_427")


def scp018():
    img = new(); d = ImageDraw.Draw(img)
    d.ellipse(r([6, 6, 26, 26]), fill=(220, 40, 40, 255), outline=OUTLINE, width=S)
    d.arc(r([6, 6, 26, 26]), 20, 160, fill=(250, 210, 60, 255), width=2 * S)
    d.ellipse(r([10, 9, 15, 13]), fill=(255, 200, 200, 230))
    for k in range(3):
        d.line(r([2, 22 + k * 3, 6, 21 + k * 3]), fill=(240, 240, 240, 200), width=S)
    save(img, "SCP_018")


if __name__ == "__main__":
    for fn in (scp207, scp268, scp330, candy, scp005, scp109, scp458, scp427, scp018):
        fn()
    print("ok")
