import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
EPOCHS = ["000002", "000004", "000006", "000008", "final"]
COLS = 10
ROWS = len(EPOCHS)
THUMB = 1024
LABEL_H = 50
PAD = 12

sheet_w = COLS * (THUMB + PAD) + PAD
sheet_h = ROWS * (THUMB + LABEL_H + PAD) + PAD

sheet = Image.new("RGB", (sheet_w, sheet_h), "white")
draw = ImageDraw.Draw(sheet)
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 34)
except Exception:
    font = ImageFont.load_default()

for row, ep in enumerate(EPOCHS):
    for col in range(COLS):
        idx = col + 1
        fname = f"im_0000{idx:02d}.png"
        path = os.path.join(ROOT, "gen", ep, fname)
        im = Image.open(path).convert("RGB")
        if im.size != (THUMB, THUMB):
            im = im.resize((THUMB, THUMB))
        x = PAD + col * (THUMB + PAD)
        y = PAD + row * (THUMB + LABEL_H + PAD)
        sheet.paste(im, (x, y))
        label = f"ep{ep} p{idx}"
        draw.text((x + 6, y + THUMB + 8), label, fill="black", font=font)

out_path = os.path.join(ROOT, "epoch_sheet_full_res.png")
sheet.save(out_path)
print("wrote", out_path, sheet.size)
