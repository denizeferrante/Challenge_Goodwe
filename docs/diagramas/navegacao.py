from PIL import Image, ImageDraw, ImageFont
B='/usr/share/fonts/opentype/inter/'
F=lambda w,s: ImageFont.truetype(B+('Inter-Bold.otf' if w else 'Inter-Regular.otf'),s)
INK=(20,23,31); SUB=(93,101,114); BG=(244,245,247); RED=(245,51,63); LINE=(185,190,200)
W_SH=500; H_SH=int(1800*W_SH/860)
def shot(name):
    im=Image.open('shots/'+name+'.png').convert('RGB').resize((W_SH,H_SH),Image.LANCZOS)
    m=Image.new('L',(W_SH,H_SH),0); ImageDraw.Draw(m).rounded_rectangle([0,0,W_SH-1,H_SH-1],30,fill=255); return im,m
def pill(d,x,y,w,txt,fill=INK,fg=(255,255,255),size=26):
    d.rounded_rectangle([x,y,x+w,y+52],26,fill=fill); f=F(1,size); tw=d.textlength(txt,font=f); d.text((x+(w-tw)/2,y+11),txt,font=f,fill=fg)
def board(fname,title,sub,accent,tabs,entry):
    pad=60; gap=44; n=len(tabs)
    W=pad*2+n*W_SH+(n-1)*gap
    maxlist=max(len(t[3]) for t in tabs)
    H=330+52+30+H_SH+60+maxlist*86+80
    c=Image.new('RGB',(W,H),BG); d=ImageDraw.Draw(c)
    d.rectangle([0,0,W,10],fill=RED)
    d.text((pad,52),'ARQUITETURA DE NAVEGAÇÃO',font=F(1,24),fill=accent)
    d.text((pad,88),title,font=F(1,58),fill=INK)
    d.text((pad,168),sub,font=F(0,28),fill=SUB)
    # entrada
    x=pad; y=232; f=F(1,22)
    for i,e in enumerate(entry):
        tw=d.textlength(e,font=f); d.rounded_rectangle([x,y,x+tw+36,y+46],23,fill=(255,255,255),outline=LINE,width=2); d.text((x+18,y+11),e,font=f,fill=INK); x+=tw+36
        if i<len(entry)-1: d.text((x+12,y+6),'→',font=F(1,28),fill=SUB); x+=56
    lastc=x-(tw+36)/2
    d.line([lastc,y+46,lastc,312],fill=LINE,width=4)
    y0=330
    # linha da barra de abas
    d.line([min(pad+W_SH/2,lastc),y0-18,max(pad+(n-1)*(W_SH+gap)+W_SH/2,lastc),y0-18],fill=LINE,width=4)
    for k,(tab,shotname,caption,children) in enumerate(tabs):
        x=pad+k*(W_SH+gap); cx=x+W_SH/2
        d.line([cx,y0-18,cx,y0],fill=LINE,width=4)
        pill(d,x+40,y0,W_SH-80,tab,accent)
        ys=y0+52+30
        im,m=shot(shotname); c.paste(im,(x,ys),m); d.rounded_rectangle([x,ys,x+W_SH-1,ys+H_SH-1],30,outline=(213,216,222),width=3)
        d.text((x+4,ys+H_SH+18),caption,font=F(0,22),fill=SUB)
        yl=ys+H_SH+70
        if children:
            d.line([x+18,yl-14,x+18,yl+(len(children)-1)*86+26],fill=LINE,width=3)
        for j,(a,b) in enumerate(children):
            yy=yl+j*86
            d.line([x+18,yy+26,x+40,yy+26],fill=LINE,width=3)
            d.rounded_rectangle([x+40,yy,x+W_SH,yy+70],14,fill=(255,255,255),outline=(222,225,230),width=2)
            d.text((x+58,yy+9),a,font=F(1,24),fill=INK); d.text((x+58,yy+40),b,font=F(0,20),fill=SUB)
    c.save(fname,optimize=True); return c.size
GREEN=(15,122,81); BLUE=(29,78,168); ORANGE=(181,107,0)
print(board('nav-motorista.png','Motorista','Encontra o eletroposto, libera a carga por QR Code, paga só os kWh entregues e acompanha o impacto.',GREEN,
 [('Início','m_inicio','início · serviços e mapa',[('Encontrar eletroposto','sugestões de destino → rota no Google Maps'),('Já estou no eletroposto','QR Code → modo de carga → pagamento'),('Sessão ao vivo → recibo','captura dos kWh entregues'),('Serviços','Assistente · Meu veículo · Carteira')]),
  ('Casa','m_casa','casa · entrada residencial',[('Smart Home','fluxo de energia da casa'),('Carregador residencial','HCA G2 da garagem')]),
  ('Carga','m_hist','carga · QR, histórico e carteira',[('Ler QR Code da vaga','libera a carga'),('Histórico','casa + eletropostos'),('Carteira','créditos e cartões')]),
  ('IA','m_ia','assistente IA · conversa',[('Assistente IA','preço, rota e ociosidade'),('Respostas com dados','previsão e tarifa do momento')]),
  ('Impacto','m_impacto','métricas de sustentabilidade',[('CO₂ evitado','por mês e acumulado'),('Equivalentes','árvores e km sem emissão')])],
 ['Escolha de papel','Login']))
print(board('nav-gestor.png','Gestor da galeria','Acompanha energia, vagas e faturamento, ajusta a tarifa base e conversa com o Síndico Virtual.',BLUE,
 [('Início','g_dash','início · eletroposto e serviços',[('Previsão · IA','demanda, geração e load shifting'),('Alertas','críticos, atenção e previsão'),('Vagas e falhas','detalhe da vaga · DLM e OCPP'),('Tarifa · Horários · Simulador','base, fator α e fases'),('Parceiros · Repasses · Conta','LEED, AQUA e Pix')]),
  ('Painel','g_painel','painel · energia e balanço do dia',[('Fluxo de energia','solar, bateria, rede e vagas'),('Vagas','potência repartida pelo DLM')]),
  ('Financeiro','g_fin','receita, economia e repasse',[('Faturamento','dia, mês e ano'),('Gasto com a rede','galeria e eletroposto'),('Tarifa base','fator α da IA')]),
  ('Síndico','g_sindico','Síndico Virtual',[('Perguntas sugeridas','DLM, tarifa, mês'),('Abre a Previsão','semana e alertas')]),
  ('Impacto','g_impacto','impacto ambiental da galeria',[('CO₂ e árvores','dia, mês e ano'),('ESG e certificação','trilha LEED e AQUA')])],
 ['Escolha de papel','Login','Acesse o ChargeGrid']))
print(board('nav-prospect.png','Gestor prospect','Avalia a galeria antes de instalar: viabilidade, vagas que cabem no sol, parceiros e contratação.',ORANGE,
 [('Viabilidade','p_viab','viabilidade e preço',[('Dados da galeria','área, consumo e vagas desejadas'),('Área solar e baterias','cobertura, fachada BIPV e carport'),('Resultado estimado','vagas, energia e faturamento'),('Parceiros GoodWe','instaladores e retrofit')]),
  ('Vagas','p_sim','simulador de vagas',[('Acrescentar área solar','kWp por superfície'),('Vagas que cabem','regra RN009 com fator 0,72')]),
  ('Conta','p_conta','conta',[('Status ChargeGrid','avaliando'),('Conta de repasse','Pix'),('Segurança da conta','2FA')])],
 ['Escolha de papel','Login','Faça aqui a sua simulação']))

# ---------- capa: entrada comum e as três personas
def cover():
    W,H=2796,1420; c=Image.new('RGB',(W,H),BG); d=ImageDraw.Draw(c)
    d.rectangle([0,0,W,10],fill=RED)
    d.text((60,52),'ARQUITETURA DE NAVEGAÇÃO',font=F(1,24),fill=RED)
    d.text((60,88),'ChargeGrid · três personas, um app',font=F(1,58),fill=INK)
    d.text((60,168),'Uma entrada comum separa o motorista do gestor; no gestor, ter ou não a solução instalada define o painel completo ou o modo de avaliação.',font=F(0,28),fill=SUB)
    y=250
    for k,(nm,cap) in enumerate([('x_role','1 · escolha de papel'),('x_gate','2 · gestor: tem a solução?')]):
        x=60+k*(W_SH+170); im,m=shot(nm); c.paste(im,(x,y),m); d.rounded_rectangle([x,y,x+W_SH-1,y+H_SH-1],30,outline=(213,216,222),width=3)
        d.text((x+4,y+H_SH+18),cap.split(' · ')[1],font=F(1,26),fill=INK)
    # setas ortogonais saindo dos botões reais das telas
    import math
    def path(pts,txt=None,tpos=None,col=INK):
        d.line(pts,fill=col,width=5,joint='curve')
        (x1,y1),(x2,y2)=pts[-2],pts[-1]; ang=math.atan2(y2-y1,x2-x1); L=22
        d.polygon([(x2,y2),(x2-L*math.cos(ang-0.45),y2-L*math.sin(ang-0.45)),(x2-L*math.cos(ang+0.45),y2-L*math.sin(ang+0.45))],fill=col)
        if txt:
            f=F(1,22); tw=d.textlength(txt,font=f); mx,my=tpos
            d.rounded_rectangle([mx-tw/2-14,my-17,mx+tw/2+14,my+17],17,fill=(255,255,255),outline=LINE,width=2); d.text((mx-tw/2,my-14),txt,font=f,fill=INK)
    cards=[('Motorista',(15,122,81),'Início · Casa · Carga · IA · Impacto','encontrar, carregar, pagar e ver o impacto'),
           ('Gestor da galeria',(29,78,168),'Início · Painel · Financeiro · Síndico · Impacto','operar vagas, energia, tarifa e repasse'),
           ('Gestor prospect',(181,107,0),'Viabilidade · Vagas · Conta','avaliar a galeria antes de instalar')]
    cx=1520; cw=W-60-cx; ys=[290,670,1050]
    for (nm,col,tabs,desc),yy in zip(cards,ys):
        d.rounded_rectangle([cx,yy,cx+cw,yy+300],24,fill=(255,255,255),outline=col,width=4)
        d.rounded_rectangle([cx+30,yy+30,cx+30+d.textlength(nm,font=F(1,30))+40,yy+82],26,fill=col); d.text((cx+50,yy+38),nm,font=F(1,30),fill=(255,255,255))
        d.text((cx+30,yy+112),'barra de abas',font=F(1,20),fill=SUB)
        d.text((cx+30,yy+140),tabs,font=F(1,30),fill=INK)
        d.text((cx+30,yy+200),desc,font=F(0,26),fill=SUB)
    path([(545,966),(645,966),(645,226),(1440,226),(1440,440),(cx-6,440)],'Motorista',(1020,226),(15,122,81))
    path([(545,1100),(722,1100)],'Gestor',(633,1100),(29,78,168))
    path([(1215,900),(1390,900),(1390,820),(cx-6,820)],'Acesse o ChargeGrid',(1390,860),(29,78,168))
    path([(1215,1044),(1390,1044),(1390,1200),(cx-6,1200)],'Faça a simulação',(1390,1122),(181,107,0))
    c.save('nav-capa.png',optimize=True); return c.size
print(cover())
