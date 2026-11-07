import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))
os.environ["TMP"] = os.path.join(HERE, "tmp")
os.environ["TEMP"] = os.environ["TMP"]
os.makedirs(os.environ["TMP"], exist_ok=True)

from playwright.sync_api import sync_playwright
from PIL import Image

FRAMES = 165
DUR = 33  # ms -> ~30fps
OUT_W, OUT_H = 480, 384
ROOT = os.path.dirname(HERE)
OUT_WEBP = os.path.join(ROOT, "frontend", "public", "robot-bienvenida.webp")
OUT_GIF = os.path.join(ROOT, "frontend", "public", "robot-bienvenida.gif")
BG = (10, 14, 28)  # --bg de la landing (#0a0e1c), para el .gif sin alfa

with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page(viewport={"width": 800, "height": 640}, device_scale_factor=1)
    page.goto("file:///" + os.path.join(HERE, "robot.html").replace("\\", "/"))
    page.wait_for_timeout(150)
    frames = []
    for i in range(FRAMES):
        page.evaluate(f"pose({i})")
        png = page.screenshot(omit_background=True)
        im = Image.open(io.BytesIO(png)).convert("RGBA")
        frames.append(im.resize((OUT_W, OUT_H), Image.LANCZOS))
    b.close()

frames[0].save(OUT_WEBP, save_all=True, append_images=frames[1:], duration=DUR,
               loop=0, quality=82, method=4)
print(OUT_WEBP, os.path.getsize(OUT_WEBP), "bytes", flush=True)

flat = []
for f in frames[::2]:  # 15fps para el gif
    base = Image.new("RGB", f.size, BG)
    base.paste(f, mask=f.getchannel("A"))
    flat.append(base)
pal = flat[len(flat) // 2].quantize(colors=256, method=Image.MEDIANCUT)
gif_frames = [f.quantize(palette=pal, dither=Image.FLOYDSTEINBERG) for f in flat]
gif_frames[0].save(OUT_GIF, save_all=True, append_images=gif_frames[1:], duration=DUR * 2,
                   loop=0, disposal=2, optimize=True)
print(OUT_GIF, os.path.getsize(OUT_GIF), "bytes")
