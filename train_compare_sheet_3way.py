import os
import textwrap
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(ROOT, "lora-dataset")

VERSIONS = [
    ("v1 (original)", os.path.join(ROOT, "gen_train", "final")),
    ("v2 (fixed captions)", os.path.join(ROOT, "gen_train_v2", "final")),
    ("v3 (fixed captions + tuned LR)", os.path.join(ROOT, "gen_train_v3", "final")),
]

ITEMS = [
    ("F0Sehn1XgBMIx5j", 1),
    ("Fg7u1FyXEAE5d_x", 2),
    ("FmViiloXEAAbIZ4", 3),
    ("FpLHBSOaMAQHaD-1", 4),
]
COL_LABELS = ["input"] + [v[0] for v in VERSIONS]

TILE = 1024
PAD = 16
HEADER_H = 70
CAPTION_H = 140
LABEL_H = 40

cols = 1 + len(VERSIONS)
rows = len(ITEMS)

sheet_w = PAD + cols * (TILE + PAD)
row_h = LABEL_H + TILE + CAPTION_H + PAD
sheet_h = PAD + HEADER_H + rows * (row_h + PAD)

sheet = Image.new("RGB", (sheet_w, sheet_h), "white")
draw = ImageDraw.Draw(sheet)

FONT_DIR = "/usr/share/fonts/truetype/dejavu"
try:
    font_header = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans-Bold.ttf", 28)
    font_label = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans-Bold.ttf", 24)
    font_caption = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans.ttf", 20)
except Exception:
    font_header = font_label = font_caption = ImageFont.load_default()

for c, label in enumerate(COL_LABELS):
    x = PAD + c * (TILE + PAD)
    draw.text((x + TILE / 2, PAD + HEADER_H / 2), label, fill="black", font=font_header, anchor="mm")

def fit_square(im, size):
    im = im.convert("RGB")
    im.thumbnail((size, size), Image.LANCZOS)
    canvas = Image.new("RGB", (size, size), "white")
    x = (size - im.width) // 2
    y = (size - im.height) // 2
    canvas.paste(im, (x, y))
    return canvas

for r, (stem, idx) in enumerate(ITEMS):
    y0 = PAD + HEADER_H + r * (row_h + PAD)

    x0 = PAD
    draw.text((x0 + TILE / 2, y0), "input", fill="black", font=font_label, anchor="ma")
    in_path = os.path.join(DATASET, f"{stem}.jpg")
    im = fit_square(Image.open(in_path), TILE)
    sheet.paste(im, (x0, y0 + LABEL_H))

    with open(os.path.join(DATASET, f"{stem}.txt")) as f:
        caption = f.read().strip()
    wrapped = textwrap.fill(caption, width=60)
    draw.multiline_text(
        (x0, y0 + LABEL_H + TILE + 8), wrapped, fill="black", font=font_caption, spacing=4
    )

    for c, (label, gen_dir) in enumerate(VERSIONS, start=1):
        x = PAD + c * (TILE + PAD)
        draw.text((x + TILE / 2, y0), label, fill="black", font=font_label, anchor="ma")
        fname = f"im_{idx:06d}.png"
        gen_path = os.path.join(gen_dir, fname)
        gim = Image.open(gen_path).convert("RGB")
        if gim.size != (TILE, TILE):
            gim = gim.resize((TILE, TILE), Image.LANCZOS)
        sheet.paste(gim, (x, y0 + LABEL_H))

out_path = os.path.join(ROOT, "train_compare_sheet_3way.png")
sheet.save(out_path)
print("wrote", out_path, sheet.size)
