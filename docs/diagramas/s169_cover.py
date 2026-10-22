from PIL import Image, ImageDraw, ImageFilter
W,H=3200,1800; BG=(255,255,255); RED=(229,50,61)
def phone(name,w):
    h=int(w*1800/860); im=Image.open('shots/'+name+'.png').convert('RGB').resize((w,h),Image.LANCZOS)
    r=int(w*0.08); m=Image.new('L',(w,h),0); ImageDraw.Draw(m).rounded_rectangle([0,0,w-1,h-1],r,fill=255); return im,m,h
def put(c,name,x,y,w,alpha=1.0):
    im,m,h=phone(name,w)
    sh=Image.new('L',(w+120,h+120),0); ImageDraw.Draw(sh).rounded_rectangle([60,70,60+w,70+h],int(w*0.08),fill=int(90*alpha)); sh=sh.filter(ImageFilter.GaussianBlur(28))
    c.paste((20,23,31),(x-60,y-60),sh)
    if alpha<1: m=m.point(lambda v:int(v*alpha))
    c.paste(im,(x,y),m)
    if alpha>=1: ImageDraw.Draw(c).rounded_rectangle([x,y,x+w-1,y+h-1],int(w*0.08),outline=(213,216,222),width=3)
def base():
    c=Image.new('RGB',(W,H),BG); return c
c=base()
from PIL import ImageOps
g=Image.open('s169/galeria.png').convert('RGB')
g=ImageOps.fit(g,(W,H),Image.LANCZOS,centering=(1.0,0.5))
wh=Image.new('RGB',(W,H),(255,255,255))
# véu branco: mais forte à esquerda (onde fica o texto), mais leve à direita
mask=Image.new('L',(W,H))
md=ImageDraw.Draw(mask)
for x in range(W):
    a=int(255*(0.90-0.10*min(1,x/(W*0.6))))
    md.line([(x,0),(x,H)],fill=a)
g=Image.composite(wh,g,mask)
c.paste(g,(0,0))
put(c,'m_inicio',1760,412,480,0.45)
put(c,'g_dash',2560,412,480,0.45)
put(c,'x_role',2110,282,580)
c.save('s169/s_capa.png',optimize=True)
c=base()
put(c,'m_encerrar',2380,250,620)
c.save('s169/s_fim.png',optimize=True)
c=base(); c.save('s169/s_base.png',optimize=True)
# fundo do agradecimento: a mesma galeria com véu, sem os celulares
c=base(); c.paste(g,(0,0)); c.save('s169/s_obrigado.png',optimize=True)
