"""
Resizes a single source image into a small JPEG thumbnail. Used by curation_server.py to
lazily generate notes/<sweep>/thumbs/<tag>.jpg on first request instead of pre-generating
every thumbnail in a batch step; once made, a thumbnail never goes stale (its source image
doesn't change after generation), so there's nothing to invalidate.
"""
from PIL import Image

THUMB_SIZE = 220
QUALITY = 78


def generate_thumbnail(src_path, dst_path):
    img = Image.open(src_path).convert("RGB")
    img.thumbnail((THUMB_SIZE, THUMB_SIZE), Image.BICUBIC)
    img.save(dst_path, format="JPEG", quality=QUALITY)
