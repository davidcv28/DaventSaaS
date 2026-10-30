"""Compone los PDF de imprenta a partir de los PNG 300 dpi del folleto."""
from PIL import Image, ImageDraw

W_PX, H_PX = 1240, 1748          # A6 a 300 dpi
A4_PX = (2480, 3508)             # A4 a 300 dpi
BLEED_PX = 35                    # 3 mm a 300 dpi

frente = Image.open('frente.png').convert('RGB')
dorso = Image.open('dorso.png').convert('RGB')
print('frente', frente.size, 'dorso', dorso.size)


def edge_bleed(img, b=BLEED_PX):
    """Extiende el arte 3 mm replicando el borde (sangrado barato y sin costuras visibles)."""
    w, h = img.size
    out = Image.new('RGB', (w + 2 * b, h + 2 * b))
    out.paste(img, (b, b))
    px = img.load()
    op = out.load()
    for y in range(h):
        left = px[0, y]
        right = px[w - 1, y]
        for x in range(b):
            op[x, b + y] = left
            op[w + b + x, b + y] = right
    for x in range(out.width):
        top = op[x, b]
        bot = op[x, b + h - 1]
        for y in range(b):
            op[x, y] = top
            op[x, out.height - 1 - y] = bot
    return out


# 1) A6 sin sangrado, 2 páginas (frente / dorso) listo para imprimir al tamaño exacto.
frente.save('DAVENT-folleto-A6.pdf', 'PDF', resolution=300.0, save_all=True, append_images=[dorso])
print('ok DAVENT-folleto-A6.pdf')

# 2) A6 con 3 mm de sangrado (para gráfica que corta a sangre).
bf = edge_bleed(frente)
bd = edge_bleed(dorso)
bf.save('DAVENT-folleto-A6-con-sangrado.pdf', 'PDF', resolution=300.0, save_all=True, append_images=[bd])
print('ok DAVENT-folleto-A6-con-sangrado.pdf', bf.size)

# 3) A4 con 4 copias por hoja (2x2) + marcas de corte: pág. 1 frentes, pág. 2 dorsos.
def sheet(img):
    canvas = Image.new('RGB', A4_PX, 'white')
    oy = (A4_PX[1] - 2 * H_PX) // 2
    canvas.paste(img, (0, oy))
    canvas.paste(img, (W_PX, oy))
    canvas.paste(img, (0, oy + H_PX))
    canvas.paste(img, (W_PX, oy + H_PX))
    d = ImageDraw.Draw(canvas)
    mark = (175, 175, 185)
    for x in (W_PX,):
        for y in range(0, A4_PX[1], 24):
            d.line([(x - 9, y), (x + 9, y)], fill=mark, width=2)
    for y in (oy, oy + H_PX):
        for x in range(0, A4_PX[0], 24):
            d.line([(x, y - 9), (x, y + 9)], fill=mark, width=2)
    return canvas


sheet(frente).save('DAVENT-hoja-A4-4x-frentes.pdf', 'PDF', resolution=300.0, save_all=True,
                   append_images=[sheet(dorso)])
print('ok DAVENT-hoja-A4-4x.pdf')

# 4) Vista previa de la imposición A4 (para revisar sin abrir el PDF).
sheet(frente).resize((1240, 1754), Image.LANCZOS).save('preview-hoja-A4.png')
print('ok preview-hoja-A4.png')
