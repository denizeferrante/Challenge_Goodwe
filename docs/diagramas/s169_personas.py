from PIL import ImageChops
from PIL import Image, ImageDraw, ImageFont
import math
B='/usr/share/fonts/opentype/inter/'
NB='/root/.fonts/'
from fontTools.ttLib import TTFont as _TT
_CMAP=set(_TT(NB+'Nunito-ExtraBold.ttf').getBestCmap())
_FB={}
def F(w,s):
    f=ImageFont.truetype(NB+('Nunito-ExtraBold.ttf' if w else 'Nunito-SemiBold.ttf'),s)
    f._fb=ImageFont.truetype(B+('Inter-Bold.otf' if w else 'Inter-Regular.otf'),s); return f
def _runs(t,font):
    out=[];cur='';cf=None
    for ch in t:
        f=font if (ord(ch) in _CMAP or not hasattr(font,'_fb')) else font._fb
        if f is not cf and cur: out.append((cur,cf)); cur=''
        cf=f; cur+=ch
    if cur: out.append((cur,cf))
    return out
_otext=ImageDraw.ImageDraw.text; _olen=ImageDraw.ImageDraw.textlength
def _text(self,xy,t,fill=None,font=None,**k):
    if font is None or not hasattr(font,'_fb'): return _otext(self,xy,t,fill=fill,font=font,**k)
    x,y=xy
    for r,f in _runs(t,font):
        _otext(self,(x,y),r,fill=fill,font=f,**k); x+=_olen(self,r,font=f)
def _len(self,t,font=None,**k):
    if font is None or not hasattr(font,'_fb'): return _olen(self,t,font=font,**k)
    return sum(_olen(self,r,font=f) for r,f in _runs(t,font))
ImageDraw.ImageDraw.text=_text; ImageDraw.ImageDraw.textlength=_len
INK=(20,23,31); SUB=(93,101,114); BG=(244,245,247); RED=(229,50,61); LINE=(185,190,200)
# tema escuro (azul-marinho do app) para destacar as telas claras
NAVY=(23,36,58); DARK=True  # #17243A, tom dos cards escuros do app (gradiente #131c2e → #1d2942)
TXT=(255,255,255) if DARK else INK; TXT2=(174,180,192) if DARK else SUB; LINE=(110,122,145) if DARK else LINE
W,H=3200,1800
def canvas():
    c=Image.new('RGB',(W,H),NAVY if DARK else BG); d=ImageDraw.Draw(c)
    if not DARK: d.rectangle([0,0,W,16],fill=RED)
    return c,d
def save_w(c,fname):
    # versão para o slide: recorta o conteúdo com margem
    bgc=c.getpixel((W-2,H-2)); bb=ImageChops.difference(c,Image.new('RGB',c.size,bgc)).getbbox()
    c.crop((max(0,bb[0]-30),max(0,bb[1]-30),min(W,bb[2]+30),min(H,bb[3]+30))).save('s169/'+fname.replace('s_','w_',1)+'.png',optimize=True)
def shot(name,w):
    h=int(w*1800/860)
    im=Image.open('shots/'+name+'.png').convert('RGB').resize((w,h),Image.LANCZOS)
    m=Image.new('L',(w,h),0); ImageDraw.Draw(m).rounded_rectangle([0,0,w-1,h-1],int(w*0.06),fill=255); return im,m,h
def paste(c,d,name,x,y,w,compact=False):
    if not compact:
        im,m,h=shot(name,w); c.paste(im,(x,y),m); d.rounded_rectangle([x,y,x+w-1,y+h-1],int(w*0.06),outline=(213,216,222),width=3); return h
    hf=int(w*1800/860); full=Image.open('shots/'+name+'.png').convert('RGB').resize((w,hf),Image.LANCZOS)
    H=int(w*1.62); tab=int(hf*0.085)
    im=Image.new('RGB',(w,H),'white'); im.paste(full.crop((0,0,w,H-tab)),(0,0)); im.paste(full.crop((0,hf-tab,w,hf)),(0,H-tab))
    dd=ImageDraw.Draw(im); dd.line([0,H-tab,w,H-tab],fill=(225,227,232),width=2)
    m=Image.new('L',(w,H),0); ImageDraw.Draw(m).rounded_rectangle([0,0,w-1,H-1],int(w*0.06),fill=255)
    c.paste(im,(x,y),m); d.rounded_rectangle([x,y,x+w-1,y+H-1],int(w*0.06),outline=(213,216,222),width=3); return H
def pill(d,x,y,w,txt,fill):
    d.rounded_rectangle([x,y,x+w,y+52],26,fill=fill); f=F(1,26); tw=d.textlength(txt,font=f); d.text((x+(w-tw)/2,y+11),txt,font=f,fill=(255,255,255))
def chips(d,x,y,entry):
    f=F(1,24); last=0
    for i,e in enumerate(entry):
        tw=d.textlength(e,font=f); d.rounded_rectangle([x,y,x+tw+40,y+50],25,fill=(255,255,255),outline=LINE,width=2); d.text((x+20,y+12),e,font=f,fill=INK)
        last=x+(tw+40)/2; x+=tw+40
        if i<len(entry)-1: d.text((x+14,y+7),'→',font=F(1,30),fill=TXT2); x+=60
    return last
WS=430; GAP=110; Y_SH=455
def board(fname,accent,tabs,entry,x0=None,extra=None):
    c,d=canvas(); n=len(tabs)
    tot=n*WS+(n-1)*GAP; x0=x0 if x0 is not None else (W-tot)//2
    lastc=chips(d,x0,276,entry)
    bus=352
    cxs=[x0+k*(WS+GAP)+WS/2 for k in range(n)]
    d.line([min(cxs[0],lastc),bus,max(cxs[-1],lastc),bus],fill=LINE,width=4); d.line([lastc,326,lastc,bus],fill=LINE,width=4)
    for k,(tab,sh,cap,items) in enumerate(tabs):
        x=x0+k*(WS+GAP); cx=cxs[k]
        d.line([cx,bus,cx,380],fill=LINE,width=4); pill(d,x+30,380,WS-60,tab,accent)
        h=paste(c,d,sh,x,Y_SH,WS)
        d.text((x+4,Y_SH+h+14),cap,font=F(0,22),fill=TXT2)
        yl=Y_SH+h+60
        if items: d.line([x+16,yl-12,x+16,yl+(len(items)-1)*70+28],fill=LINE,width=3)
        for j,(a,b) in enumerate(items):
            yy=yl+j*70
            d.line([x+16,yy+28,x+36,yy+28],fill=LINE,width=3)
            d.rounded_rectangle([x+36,yy,x+WS,yy+62],12,fill=(255,255,255),outline=(222,225,230),width=2)
            d.text((x+54,yy+6),a,font=F(1,23),fill=INK); d.text((x+54,yy+35),b,font=F(0,19),fill=SUB)
    if extra: extra(c,d)
    c.save('s169/'+fname+'.png',optimize=True); save_w(c,fname)
GREEN=(15,122,81); BLUE=(29,78,168); ORANGE=(181,107,0)
if DARK: GREEN=(22,160,104); BLUE=(53,119,241); ORANGE=(214,128,10)
board('s_motorista',GREEN,
 [('Início','m_inicio','início · serviços e mapa',[('Encontrar eletroposto','sugestões → rota no Google Maps'),('Já estou no eletroposto','QR Code → modo → pagamento'),('Sessão ao vivo → recibo','captura dos kWh entregues'),('Serviços','Assistente · Veículo · Carteira')]),
  ('Casa','m_casa','casa · entrada residencial',[('Smart Home','fluxo de energia da casa'),('Carregador residencial','HCA G2 da garagem')]),
  ('Carga','m_hist','carga · QR, histórico e carteira',[('Ler QR Code da vaga','libera a carga'),('Histórico','casa + eletropostos'),('Carteira','créditos e cartões')]),
  ('IA','m_ia','assistente IA · conversa',[('Assistente IA','preço, rota e ociosidade'),('Respostas com dados','previsão e tarifa do momento')]),
  ('Impacto','m_impacto','métricas de sustentabilidade',[('CO₂ evitado','por mês e acumulado'),('Equivalentes','árvores e km sem emissão')])],
 ['Escolha de papel','Login'])
board('s_gestor',BLUE,
 [('Início','g_dash','início · eletroposto e serviços',[('Previsão · IA','demanda, geração, load shifting'),('Alertas','críticos, atenção e previsão'),('Vagas e falhas','detalhe da vaga · DLM e OCPP'),('Tarifa · Horários · Simulador','base, fator α e fases'),('Parceiros · Repasses · Conta','LEED, AQUA e Pix')]),
  ('Painel','g_painel','painel · energia e balanço do dia',[('Fluxo de energia','solar, bateria, rede e vagas'),('Vagas','potência repartida pelo DLM')]),
  ('Financeiro','g_fin','receita, economia e repasse',[('Faturamento','dia, mês e ano'),('Gasto com a rede','galeria e eletroposto'),('Tarifa base','fator α da IA')]),
  ('Síndico','g_sindico','Síndico Virtual',[('Perguntas sugeridas','DLM, tarifa, mês'),('Abre a Previsão','semana e alertas')]),
  ('Impacto','g_impacto','impacto ambiental da galeria',[('CO₂ e árvores','dia, mês e ano'),('ESG e certificação','trilha LEED e AQUA')])],
 ['Escolha de papel','Login','Acesse o ChargeGrid'])
def resultado(c,d):
    x=1920; y=380; w=1160
    d.rounded_rectangle([x,y,x+w,y+1365],28,fill=(255,255,255),outline=(222,225,230),width=2)
    d.text((x+56,y+50),'O QUE É A SIMULAÇÃO',font=F(1,24),fill=ORANGE)
    txt=['Antes de instalar, o gestor descreve a galeria e o app','estima quantas vagas de recarga o sol consegue','alimentar, a energia gerada e o faturamento.']
    for i,l in enumerate(txt): d.text((x+56,y+96+i*40),l,font=F(0,28),fill=INK)
    d.text((x+56,y+262),'A LÓGICA',font=F(1,24),fill=ORANGE)
    steps=[('Entradas','área, superfícies solares, baterias e vagas desejadas'),
           ('Geração solar','kWp efetivo × irradiação de SP × 0,72 de desempenho'),
           ('Rateio do sol','% para o eletroposto (sugestão 80%), o resto à galeria'),
           ('Vagas','energia para EVs ÷ (7 kW × horas de sol pleno), arredondado para baixo'),
           ('Ajustes','eficiência no HVAC (15% a 25%) e regra do LPUOS para o carport')]
    ys=[y+350+i*182 for i in range(len(steps))]
    for i,(a_,b_) in enumerate(steps):
        yy=ys[i]
        d.ellipse([x+56,yy+8,x+84,yy+36],fill=ORANGE)
        if i<len(steps)-1:
            d.line([x+70,yy+44,x+70,ys[i+1]-4],fill=ORANGE,width=4)
            d.polygon([(x+60,ys[i+1]-16),(x+80,ys[i+1]-16),(x+70,ys[i+1]-2)],fill=ORANGE)
        d.text((x+110,yy),a_,font=F(1,30),fill=INK); d.text((x+110,yy+46),b_,font=F(0,25),fill=SUB)
    d.text((x+56,y+1300),'Estimativa paramétrica: confirmar com levantamento técnico.',font=F(0,23),fill=SUB)
board('s_prospect',ORANGE,
 [('Viabilidade','p_viab','viabilidade e preço',[('Dados da galeria','área, consumo e vagas desejadas'),('Área solar e baterias','cobertura, fachada e carport'),('Resultado estimado','vagas, energia e faturamento'),('Parceiros GoodWe','instaladores e retrofit')]),
  ('Vagas','p_sim','simulador de vagas',[('Acrescentar área solar','kWp por superfície'),('Vagas que cabem','regra RN009 com fator 0,72')]),
  ('Conta','p_conta','conta',[('Status ChargeGrid','avaliando'),('Conta de repasse','Pix'),('Segurança da conta','2FA')])],
 ['Escolha de papel','Login','Faça aqui a sua simulação'],x0=120,extra=resultado)
# ---------- três personas
def tres(bg):
  c=Image.new('RGB',(W,H),bg); d=ImageDraw.Draw(c)
  if bg==BG: d.rectangle([0,0,W,16],fill=RED)
  ws=560; ry=300
  hr=paste(c,d,'x_role',120,ry,ws); d.text((124,ry+hr+16),'escolha de papel',font=F(1,28),fill=TXT)
  gx=120+ws+230
  hg=paste(c,d,'x_gate',gx,ry,ws); d.text((gx+4,ry+hg+16),'gestor: tem a solução?',font=F(1,28),fill=TXT)
  cx=gx+ws+470; cw=W-120-cx
  cards=[('Motorista',GREEN,'Início · Casa · Carga · IA · Impacto','encontrar, carregar, pagar e ver o impacto'),
         ('Gestor da galeria',BLUE,'Início · Painel · Financeiro · Síndico · Impacto','operar vagas, energia, tarifa e repasse'),
         ('Gestor prospect',ORANGE,'Viabilidade · Vagas · Conta','avaliar a galeria antes de instalar')]
  top=ry-50; gf=ry+int(hg*0.759); ga=(top+gf)//2  # ga cai no card 'Acesse o ChargeGrid'
  CH=350; ys=[top-CH//2, ga-CH//2, gf-CH//2]  # setas retas entrando no centro de cada card, cards equidistantes
  for (nm,col,tabs,desc),yy in zip(cards,ys):
    d.rounded_rectangle([cx,yy,cx+cw,yy+CH],28,fill=(255,255,255),outline=col,width=5)
    tw=d.textlength(nm,font=F(1,34)); d.rounded_rectangle([cx+40,yy+40,cx+40+tw+48,yy+102],31,fill=col); d.text((cx+64,yy+50),nm,font=F(1,34),fill=(255,255,255))
    d.text((cx+40,yy+142),'barra de abas',font=F(1,24),fill=SUB)
    d.text((cx+40,yy+176),tabs,font=F(1,34),fill=INK)
    d.text((cx+40,yy+256),desc,font=F(0,30),fill=SUB)
  def path(pts,col):
    d.line(pts,fill=col,width=6,joint='curve')
    (x1,y1),(x2,y2)=pts[-2],pts[-1]; a=math.atan2(y2-y1,x2-x1); L=26
    d.polygon([(x2,y2),(x2-L*math.cos(a-0.45),y2-L*math.sin(a-0.45)),(x2-L*math.cos(a+0.45),y2-L*math.sin(a+0.45))],fill=col)
  def label(txt,x1,x2,y,col):
    # rótulo acima do segmento horizontal, sem tocar a linha
    f=F(1,26); tw=d.textlength(txt,font=f); mx=(x1+x2)/2; my=y-36
    d.rounded_rectangle([mx-tw/2-16,my-20,mx+tw/2+16,my+20],20,fill=(255,255,255),outline=col,width=2); d.text((mx-tw/2,my-16),txt,font=f,fill=INK)
  bm=ry+int(hr*0.684); bg_=ry+int(hr*0.813)
  rr=120+int(ws*0.97); gr=gx+int(ws*0.97)
  xm=gx+ws+130; xg=gx+ws+70; end=cx-10
  cy=[yy+CH//2 for yy in ys]
  # motorista: contorna o celular do gestor por cima e entra no card
  path([(rr,bm),(rr+80,bm),(rr+80,top),(end,top)],GREEN); label('Motorista',gx+ws,end,top,GREEN)
  path([(rr,bg_),(gx-10,bg_)],BLUE); label('Gestor',rr,gx,bg_,BLUE)
  path([(gr,ga),(end,ga)],BLUE); label('Acesse o ChargeGrid',gx+ws,end,ga,BLUE)
  path([(gr,gf),(end,gf)],ORANGE); label('Faça a simulação',gx+ws,end,gf,ORANGE)
  return c
_t=tres(NAVY if DARK else BG); _t.save('s169/s_personas.png',optimize=True); save_w(_t,'s_personas')
print('ok')
