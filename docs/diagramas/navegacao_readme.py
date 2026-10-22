# Gera as pranchas do README com o mesmo desenho dos slides: rode s169_personas.py com DARK=False e saída em navl/, depois este script.
# Pranchas de navegação do README: mesmo desenho dos slides (tema claro) com cabeçalho em Nunito
from PIL import Image, ImageDraw, ImageFont, ImageChops
NB='/root/.fonts/'
F=lambda w,s: ImageFont.truetype(NB+('Nunito-ExtraBold.ttf' if w else 'Nunito-SemiBold.ttf'),s)
INK=(20,23,31); SUB=(93,101,114); BG=(244,245,247); RED=(229,50,61)
GREEN=(15,122,81); BLUE=(29,78,168); ORANGE=(181,107,0)
def content(name):
    s=Image.open('navl/s_'+name+'.png').convert('RGB'); s=s.crop((0,20,s.width,s.height))
    bb=ImageChops.difference(s,Image.new('RGB',s.size,BG)).getbbox()
    return s.crop((bb[0],bb[1],bb[2],bb[3]))
def board(name,title,sub,accent,out):
    ct=content(name); pad=80
    W=ct.width+2*pad; H=ct.height+300+pad
    c=Image.new('RGB',(W,H),BG); d=ImageDraw.Draw(c)
    d.rectangle([0,0,W,12],fill=RED)
    d.text((pad,60),'ARQUITETURA DE NAVEGAÇÃO',font=F(1,30),fill=accent)
    d.text((pad,104),title,font=F(1,72),fill=INK)
    d.text((pad,206),sub,font=F(0,34),fill=SUB)
    c.paste(ct,(pad,300)); c.save(out,optimize=True); return c
imgs=[board('personas','ChargeGrid · três personas, um app','Uma entrada comum separa o motorista do gestor; no gestor, ter ou não a solução instalada define o painel completo ou o modo de avaliação.',RED,'navl/navegacao-capa.png'),
      board('motorista','Motorista','Encontra o eletroposto, libera a carga por QR Code, paga só os kWh entregues e acompanha o impacto.',GREEN,'navl/navegacao-motorista.png'),
      board('gestor','Gestor da galeria','Acompanha energia, vagas e faturamento, ajusta a tarifa base e conversa com o Síndico Virtual.',BLUE,'navl/navegacao-gestor.png'),
      board('prospect','Gestor prospect','Avalia a galeria antes de instalar: viabilidade, vagas que cabem no sol, parceiros e contratação.',ORANGE,'navl/navegacao-prospect.png')]
imgs[0].save('navl/navegacao-personas.pdf',save_all=True,append_images=imgs[1:],resolution=200)
for i in imgs: print(i.size)
