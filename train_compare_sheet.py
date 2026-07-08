import os
import textwrap
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(ROOT, "lora-dataset")
GEN = os.path.join(ROOT, "gen_train")

ITEMS = [
    ("F0Sehn1XgBMIx5j", 1),
    ("Fg7u1FyXEAE5d_x", 2),
    ("FmViiloXEAAbIZ4", 3),
    ("FpLHBSOaMAQHaD-1", 4),
]
EPOCHS = ["000002", "000004", "000006", "000008", "final"]
COL_LABELS = ["input"] + [f"ep{e}" for e in EPOCHS]

TILE = 1024
PAD = 16
HEADER_H = 60
CAPTION_H = 140
LABEL_H = 40

cols = 1 + len(EPOCHS)
rows = len(ITEMS)

sheet_w = PAD + cols * (TILE + PAD)
row_h = LABEL_H + TILE + CAPTION_H + PAD
sheet_h = PAD + HEADER_H + rows * (row_h + PAD)

sheet = Image.new("RGB", (sheet_w, sheet_h), "white")
draw = ImageDraw.Draw(sheet)

FONT_DIR = "/usr/share/fonts/truetype/dejavu"
try:
    font_header = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans-Bold.ttf", 30)
    font_label = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans-Bold.ttf", 24)
    font_caption = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans.ttf", 20)
except Exception:
    font_header = font_label = font_caption = ImageFont.load_default()

# column headers
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

    # input image column
    x0 = PAD
    draw.text((x0 + TILE / 2, y0), "input", fill="black", font=font_label, anchor="ma")
    in_path = os.path.join(DATASET, f"{stem}.jpg")
    im = fit_square(Image.open(in_path), TILE)
    sheet.paste(im, (x0, y0 + LABEL_H))

    # caption under input image
    with open(os.path.join(DATASET, f"{stem}.txt")) as f:
        caption = f.read().strip()
    wrapped = textwrap.fill(caption, width=60)
    draw.multiline_text(
        (x0, y0 + LABEL_H + TILE + 8), wrapped, fill="black", font=font_caption, spacing=4
    )

    # generated epoch columns
    for c, ep in enumerate(EPOCHS, start=1):
        x = PAD + c * (TILE + PAD)
        draw.text((x + TILE / 2, y0), f"ep{ep}", fill="black", font=font_label, anchor="ma")
        fname = f"im_{idx:06d}.png"
        gen_path = os.path.join(GEN, ep, fname)
        gim = Image.open(gen_path).convert("RGB")
        if gim.size != (TILE, TILE):
            gim = gim.resize((TILE, TILE), Image.LANCZOS)
        sheet.paste(gim, (x, y0 + LABEL_H))

out_path = os.path.join(ROOT, "train_compare_sheet.png")
sheet.save(out_path)
print("wrote", out_path, sheet.size)
