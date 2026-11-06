# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
"""Draws the GUI icons (24 px PNG, plus app icon 64 px / .ico) into atlasa0/assets/icons. Needs Pillow only.
    python tools/make_icons.py
"""
import os
from PIL import Image, ImageDraw

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "atlasa0", "assets", "icons")
INK, TEAL, SKY, RED, GREEN, AMBER, GREY = "#17324d", "#1f7a8c", "#bfdbf7", "#d1495b", "#3a9d5d", "#edae49", "#8d99ae"
S = 96  # drawn at 96 px and reduced for smooth edges


def canvas():
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


def where(d):      # map pin
    d.ellipse((26, 10, 70, 54), fill=RED); d.polygon([(30, 46), (66, 46), (48, 84)], fill=RED)
    d.ellipse((38, 22, 58, 42), fill="white")

def map_(d):       # folded map
    d.polygon([(8, 22), (32, 14), (32, 76), (8, 84)], fill=SKY, outline=INK)
    d.polygon([(32, 14), (64, 24), (64, 86), (32, 76)], fill="white", outline=INK)
    d.polygon([(64, 24), (88, 14), (88, 76), (64, 86)], fill=SKY, outline=INK)
    d.line((12, 60, 28, 40), fill=TEAL, width=5); d.line((70, 40, 84, 30), fill=TEAL, width=5)

def layers(d):     # stack
    for i, c in enumerate((SKY, "#7fb7d9", TEAL)):
        y = 56 - i * 20
        d.polygon([(48, y - 22), (86, y), (48, y + 22), (10, y)], fill=c, outline=INK)

def receptors(d):  # hospital cross in a circle
    d.ellipse((8, 8, 88, 88), fill=RED); d.rectangle((40, 22, 56, 74), fill="white"); d.rectangle((22, 40, 74, 56), fill="white")

def elements(d):   # compass star
    d.polygon([(48, 6), (58, 38), (90, 48), (58, 58), (48, 90), (38, 58), (6, 48), (38, 38)], fill=TEAL, outline=INK)
    d.polygon([(48, 6), (58, 38), (38, 38)], fill=RED)

def styles(d):     # paint palette
    d.ellipse((6, 12, 90, 84), fill=AMBER, outline=INK)
    for (x, y, c) in ((28, 34, RED), (50, 24, GREEN), (70, 38, TEAL)):
        d.ellipse((x - 9, y - 9, x + 9, y + 9), fill=c)
    d.ellipse((50, 54, 78, 78), fill="white", outline=INK)

def output(d):     # folder
    d.polygon([(6, 28), (36, 28), (42, 38), (90, 38), (90, 84), (6, 84)], fill=AMBER, outline=INK)
    d.rectangle((6, 44, 90, 84), fill="#f4c76d", outline=INK)

def settings(d):   # gear
    import math
    for k in range(8):
        a = k * math.pi / 4
        cx, cy = 48 + 36 * math.cos(a), 48 + 36 * math.sin(a)
        d.ellipse((cx - 10, cy - 10, cx + 10, cy + 10), fill=GREY, outline=INK)
    d.ellipse((14, 14, 82, 82), fill=GREY, outline=INK); d.ellipse((32, 32, 64, 64), fill="white", outline=INK)

def run(d):        # play
    d.ellipse((6, 6, 90, 90), fill=GREEN); d.polygon([(36, 26), (36, 70), (72, 48)], fill="white")

def cancel(d):     # stop
    d.ellipse((6, 6, 90, 90), fill=RED); d.rectangle((30, 30, 66, 66), fill="white")

def save(d):       # floppy
    d.rectangle((10, 10, 86, 86), fill=TEAL, outline=INK); d.rectangle((24, 10, 70, 34), fill="white")
    d.rectangle((52, 14, 62, 30), fill=INK); d.rectangle((22, 50, 74, 86), fill=SKY)

def load(d):       # open folder with arrow
    output(d); d.polygon([(48, 20), (66, 38), (56, 38), (56, 60), (40, 60), (40, 38), (30, 38)], fill=TEAL, outline=INK)

def export(d):     # box + arrow out
    d.rectangle((10, 36, 70, 86), fill=SKY, outline=INK)
    d.polygon([(54, 8), (90, 30), (54, 52), (54, 38), (36, 38), (36, 22), (54, 22)], fill=GREEN, outline=INK)

def add(d):
    d.ellipse((6, 6, 90, 90), fill=GREEN); d.rectangle((42, 22, 54, 74), fill="white"); d.rectangle((22, 42, 74, 54), fill="white")

def remove(d):
    d.ellipse((6, 6, 90, 90), fill=RED); d.rectangle((22, 42, 74, 54), fill="white")

def edit(d):       # pencil
    d.polygon([(14, 82), (20, 58), (62, 16), (80, 34), (38, 76)], fill=AMBER, outline=INK)
    d.polygon([(14, 82), (20, 58), (38, 76)], fill="#f5d7a1", outline=INK); d.polygon([(62, 16), (72, 6), (90, 24), (80, 34)], fill=RED, outline=INK)

def up(d):
    d.polygon([(48, 12), (86, 56), (62, 56), (62, 84), (34, 84), (34, 56), (10, 56)], fill=TEAL, outline=INK)

def down(d):
    d.polygon([(48, 84), (86, 40), (62, 40), (62, 12), (34, 12), (34, 40), (10, 40)], fill=TEAL, outline=INK)

def browse(d):
    output(d)

def refresh(d):    # download tray
    d.polygon([(48, 62), (84, 22), (62, 22), (62, 6), (34, 6), (34, 22), (12, 22)], fill=TEAL, outline=INK)
    d.rectangle((10, 70, 86, 86), fill=INK)

def label(d):      # text tag "A"
    d.rounded_rectangle((8, 14, 88, 82), radius=12, fill=SKY, outline=INK)
    d.polygon([(30, 68), (48, 24), (66, 68), (58, 68), (54, 58), (42, 58), (38, 68)], fill=INK)

def app(d):        # map pin over a grid
    d.rounded_rectangle((4, 4, 92, 92), radius=16, fill="#e9f1e4", outline=INK, width=3)
    for v in (30, 50, 70):
        d.line((v, 8, v, 88), fill="#c6d7bf", width=3); d.line((8, v, 88, v), fill="#c6d7bf", width=3)
    d.ellipse((30, 14, 66, 50), fill=RED); d.polygon([(34, 42), (62, 42), (48, 76)], fill=RED); d.ellipse((40, 24, 56, 40), fill="white")

ICONS = dict(where=where, map=map_, layers=layers, receptors=receptors, elements=elements, styles=styles,
             output=output, settings=settings, run=run, cancel=cancel, save=save, load=load, export=export, add=add, remove=remove,
             edit=edit, up=up, down=down, browse=browse, refresh=refresh, label=label, app=app)


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, fn in ICONS.items():
        im, d = canvas()
        fn(d)
        size = 64 if name == "app" else 24
        im.resize((size, size), Image.LANCZOS).save(os.path.join(OUT, f"{name}.png"))
        if name == "app":
            im.resize((256, 256), Image.LANCZOS).save(os.path.join(OUT, "app.ico"), sizes=[(16, 16), (32, 32), (48, 48), (256, 256)])
    print(f"{len(ICONS)} icons written to {OUT}")


if __name__ == "__main__":
    main()
