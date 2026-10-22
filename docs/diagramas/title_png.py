# Renderiza um título em Nunito como PNG transparente (300 dpi), para a fonte aparecer igual em qualquer aparelho
import sys, hashlib, os
from PIL import Image, ImageDraw, ImageFont
text, color, pt = sys.argv[1], sys.argv[2], float(sys.argv[3])
px = round(pt * 300 / 72)
f = ImageFont.truetype('/root/.fonts/Nunito-ExtraBold.ttf', px)
asc, desc = f.getmetrics()
w = int(ImageDraw.Draw(Image.new('L', (1, 1))).textlength(text, font=f)) + 4
h = asc + desc
im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
ImageDraw.Draw(im).text((2, 0), text, font=f, fill='#' + color)
os.makedirs('titulos', exist_ok=True)
out = 'titulos/' + hashlib.md5((text + color + str(pt)).encode()).hexdigest()[:12] + '.png'
im.save(out)
print(out, w / 300, h / 300)
