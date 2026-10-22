# Avatares circulares da equipe. Se existir s169/fotos/<RM>.jpg|png, usa a foto; senão, iniciais.
from PIL import Image, ImageDraw, ImageFont
import os
team=[('572899','Patrick Fernandes Martins Pais'),('571836','Bruna Yukimy Hada'),('571562','Denize Ferrante'),
      ('570436','Gabriel Del Pizzo Pintor'),('572395','Gabriel Dias Menezes'),('570540','Ian Rodrigues Martins')]
# recorte circular por pessoa; onde o círculo passa da borda, a foto é estendida por espelhamento com desfoque
CROP={'572899':(250,205,205),'571836':(225,175,175),'571562':(200,150,137),'570436':(215,180,180),'572395':(210,190,190),'570540':(195,170,170)}  # centro (x,y) e raio do círculo na foto, com o rosto inteiro dentro
S=800; RING=26; LIME=(156,254,51); DARK=(26,33,48)
f=ImageFont.truetype('/root/.fonts/Nunito-Black.ttf',260)
for rm,n in team:
    out=Image.new('RGBA',(S,S),(0,0,0,0)); d=ImageDraw.Draw(out)
    d.ellipse([0,0,S-1,S-1],fill=LIME)
    inner=S-2*RING
    src=next((f'fotos/{rm}.{e}' for e in ('jpg','jpeg','png') if os.path.exists(f's169/fotos/{rm}.{e}')),None)
    if src:
        im=Image.open('s169/'+src).convert('RGB'); w,h=im.size; m=min(w,h)
        cx,cy,r=CROP.get(rm,(w//2,h//2,m//2))
        P=max(0,r-cx,r-cy,cx+r-w,cy+r-h)
        if P:
            from PIL import ImageFilter, ImageOps
            big=Image.new('RGB',(w+2*P,h+2*P)); 
            import numpy as np
            a=np.asarray(im).astype(float); bg=np.median(np.concatenate([a[:15].reshape(-1,3),a[-15:].reshape(-1,3),a[:,:15].reshape(-1,3),a[:,-15:].reshape(-1,3)]),axis=0)
            big=Image.new('RGB',(w+2*P,h+2*P),tuple(int(v) for v in bg)); big.paste(im,(P,P)); big=big.filter(ImageFilter.GaussianBlur(10)); big.paste(im,(P,P)); im=big; cx+=P; cy+=P
        im=im.crop((cx-r,cy-r,cx+r,cy+r))
        im=im.resize((inner,inner),Image.LANCZOS)
    else:
        im=Image.new('RGB',(inner,inner),DARK); di=ImageDraw.Draw(im)
        p=n.split(); ini=p[0][0]+p[-1][0]
        di.text((inner/2,inner/2),ini,font=f,fill=(255,255,255),anchor='mm')
    mask=Image.new('L',(inner,inner),0); ImageDraw.Draw(mask).ellipse([0,0,inner-1,inner-1],fill=255)
    out.paste(im,(RING,RING),mask); out.save(f's169/av_{rm}.png'); print(rm,'foto' if src else 'iniciais')
