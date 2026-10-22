from html import escape as esc
W,H=960,1140
INK='#14171f'; SUB='#5d6572'; ICON='#4a5160'; BLUE='#1e6fc8'
C={'pot':'#14171f','rs485':'#49b6e6','lan':'#1f9d4b','wifi':'#2f74d0','bt':'#f0912b','net':'#2f74d0'}
o=[]; top=[]
def t(x,y,s,size=13.5,w=400,c=INK,a='start',bg=False):
    (top if bg else o).append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{w}" fill="{c}" text-anchor="{a}"{" stroke=\"#ffffff\"" if bg else ""}>{esc(s)}</text>')
def ln(pts,k,dash=False,arrow=None,width=2.2,color=None):
    d='M'+' L'.join(f'{x},{y}' for x,y in pts)
    da={'wifi':'6 4','bt':'5 4','net':'3 4'}.get(k,'') if dash else ''
    m=(' marker-end="url(#a-%s)"'%k if arrow in('end','both') else '')+(' marker-start="url(#a-%s)"'%k if arrow in('start','both') else '')
    o.append(f'<path d="{d}" fill="none" stroke="{color or C[k]}" stroke-width="{width}" stroke-dasharray="{da}" stroke-linejoin="round"{m}/>')
def badge(x,y,n,col=BLUE):
    return
    top.append(f'<circle cx="{x}" cy="{y}" r="11" fill="{col}"/><text x="{x}" y="{y+4.5}" text-anchor="middle" font-size="13" font-weight="700" fill="#fff">{n}</text>')
S=f'stroke="{ICON}" stroke-width="2" fill="#ffffff"'
LIME='#7dbb00'; LIMEF='#f2fbd6'
SL=f'stroke="{LIME}" stroke-width="2.4" fill="{LIMEF}"'
RED='#e5323d'; REDF='#fdeeee'
SR=f'stroke="{RED}" stroke-width="2.4" fill="{REDF}"'
def cloud(cx,cy,lime=False,red=False):
    o.append(f'<path d="M{cx-48},{cy+22} h96 a20,20 0 0 0 2,-40 a28,28 0 0 0 -50,-14 a22,22 0 0 0 -40,10 a18,18 0 0 0 -8,44 z" {SR if red else (SL if lime else S)}/>')
def router(cx,cy):
    o.append(f'<rect x="{cx-38}" y="{cy-11}" width="76" height="22" rx="6" {S}/>')
    for i in range(4): o.append(f'<circle cx="{cx-24+i*10}" cy="{cy}" r="2.2" fill="{ICON}"/>')
    o.append(f'<path d="M{cx-12},{cy-22} a17,17 0 0 1 24,0 M{cx-6},{cy-16} a8,8 0 0 1 12,0" fill="none" stroke="{ICON}" stroke-width="2"/>')
def phone(x,y,w=34,h=58,lime=False,red=False):
    c=RED if red else (LIME if lime else ICON)
    o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="7" {SR if red else (SL if lime else S)}/><line x1="{x+w/2-6}" y1="{y+h-8}" x2="{x+w/2+6}" y2="{y+h-8}" stroke="{c}" stroke-width="2"/>')
def monitor(cx,y):
    o.append(f'<rect x="{cx-40}" y="{y}" width="80" height="50" rx="5" {SL}/><path d="M{cx-28},{y+38} l12,-12 l10,6 l16,-18" fill="none" stroke="{LIME}" stroke-width="2.4"/><line x1="{cx}" y1="{y+50}" x2="{cx}" y2="{y+60}" stroke="{LIME}" stroke-width="2.4"/><line x1="{cx-16}" y1="{y+60}" x2="{cx+16}" y2="{y+60}" stroke="{LIME}" stroke-width="2.6"/>')
def esp32(x,y):
    o.append(f'<rect x="{x}" y="{y}" width="64" height="40" rx="4" {SL}/><rect x="{x+14}" y="{y+10}" width="20" height="16" rx="2" fill="{LIME}"/><circle cx="{x+48}" cy="{y+14}" r="5" fill="#e5323d"/><circle cx="{x+48}" cy="{y+29}" r="4" fill="none" stroke="{LIME}" stroke-width="2"/>')
    for i in range(6): o.append(f'<line x1="{x+6+i*10}" y1="{y+40}" x2="{x+6+i*10}" y2="{y+46}" stroke="{LIME}" stroke-width="1.8"/>')
def inverter(x,y):
    o.append(f'<rect x="{x}" y="{y}" width="110" height="96" rx="6" {S}/><rect x="{x+10}" y="{y+68}" width="90" height="15" rx="3" fill="{ICON}"/>')
def panels(x,y):
    for r in range(2):
        for c in range(3):
            px,py=x+c*36+r*8,y+r*22
            o.append(f'<path d="M{px+6},{py} h30 l-6,20 h-30 z" {S} stroke-width="1.6"/>')
def carport(x,y):
    # cobertura inclinada com módulos solares, dois pilares e um carro embaixo
    o.append(f'<path d="M{x},{y+24} L{x+112},{y+8} L{x+112},{y+16} L{x},{y+32} z" {SL}/>')
    for i in range(4):
        px=x+8+i*26; py=y+22-i*3.7
        o.append(f'<path d="M{px},{py} l20,-3 l3,-9 l-20,3 z" fill="{LIME}" stroke="{LIME}" stroke-width="1"/>')
    o.append(f'<path d="M{x+10},{y+31} V{y+70} M{x+102},{y+16} V{y+70}" stroke="{LIME}" stroke-width="2.6"/>')
    o.append(f'<path d="M{x+26},{y+66} v-8 q0,-5 6,-6 l8,-3 l8,-8 h22 l9,9 q12,1 12,8 v8 z" fill="#ffffff" stroke="{LIME}" stroke-width="2"/>')
    o.append(f'<line x1="{x-4}" y1="{y+70}" x2="{x+116}" y2="{y+70}" stroke="{LIME}" stroke-width="2"/>')
def facade(x,y):
    # fachada BIPV: vidro fotovoltaico na envoltória do prédio
    o.append(f'<rect x="{x}" y="{y}" width="64" height="92" rx="4" {SL}/>')
    for r in range(4):
        for c in range(2):
            gx,gy=x+7+c*27,y+7+r*21
            o.append(f'<rect x="{gx}" y="{gy}" width="23" height="17" fill="#ffffff" stroke="{LIME}" stroke-width="1.6"/><path d="M{gx+4},{gy+17} l9,-17 M{gx+12},{gy+17} l9,-17" stroke="{LIME}" stroke-width="1.4"/>')
def battery(x,y):
    o.append(f'<rect x="{x}" y="{y}" width="70" height="42" rx="5" {S}/><rect x="{x+12}" y="{y-6}" width="12" height="6" fill="{ICON}"/><rect x="{x+46}" y="{y-6}" width="12" height="6" fill="{ICON}"/><text x="{x+18}" y="{y+28}" font-size="18" font-weight="700" fill="{ICON}" text-anchor="middle">+</text><text x="{x+52}" y="{y+27}" font-size="18" font-weight="700" fill="{ICON}" text-anchor="middle">−</text>')
def wallbox(x,y):
    o.append(f'<path d="M{x},{y+8} q0,-8 8,-8 h34 q8,0 8,8 v52 q0,10 -10,10 h-30 q-10,0 -10,-10 z" {S}/><rect x="{x+14}" y="{y+12}" width="22" height="14" rx="3" fill="none" stroke="{ICON}" stroke-width="2"/><path d="M{x+27},{y+34} l-6,10 h8 l-6,10" fill="none" stroke="{ICON}" stroke-width="2"/>')
def smallmeter(x,y,w=34,h=42):
    o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="5" {S}/><rect x="{x+7}" y="{y+8}" width="{w-14}" height="11" rx="2" fill="none" stroke="{ICON}" stroke-width="1.8"/><circle cx="{x+w/2}" cy="{y+h-11}" r="4" fill="none" stroke="{ICON}" stroke-width="1.8"/>')
def rcbo(x,y):
    o.append(f'<rect x="{x}" y="{y}" width="38" height="34" rx="4" {S}/><rect x="{x+7}" y="{y+9}" width="10" height="16" rx="2" fill="{ICON}"/><rect x="{x+21}" y="{y+9}" width="10" height="16" rx="2" fill="none" stroke="{ICON}" stroke-width="1.8"/>')
def car(x,y):
    o.append(f'<path d="M{x},{y+34} v-12 q0,-8 9,-9 l16,-4 l14,-12 h40 l16,14 q20,2 20,13 v10 z" {S}/><circle cx="{x+27}" cy="{y+36}" r="8" {S}/><circle cx="{x+91}" cy="{y+36}" r="8" {S}/>')
def gauge(cx,cy):
    o.append(f'<rect x="{cx-24}" y="{cy-20}" width="48" height="40" rx="5" {S}/><path d="M{cx-14},{cy+6} a15,15 0 0 1 28,0" fill="none" stroke="{ICON}" stroke-width="1.8"/><line x1="{cx}" y1="{cy+6}" x2="{cx+8}" y2="{cy-5}" stroke="{ICON}" stroke-width="2"/>')
def pylon(x,y):
    o.append(f'<path d="M{x+20},{y} L{x+4},{y+76} M{x+20},{y} L{x+36},{y+76} M{x},{y+18} h40 M{x+4},{y+36} h32 M{x+8},{y+38} L{x+32},{y+76} M{x+32},{y+38} L{x+8},{y+76}" fill="none" stroke="{ICON}" stroke-width="2"/>')
def building(x,y):
    o.append(f'<path d="M{x},{y+70} v-48 h96 v48 z" {SL}/>')
    o.append(f'<path d="M{x-6},{y+22} l12,-14 h84 l12,14" {SL}/>')
    for i in range(3): o.append(f'<rect x="{x+10+i*28}" y="{y+32}" width="18" height="16" fill="#ffffff" stroke="{LIME}" stroke-width="1.8"/>')
    o.append(f'<rect x="{x+38}" y="{y+52}" width="20" height="18" fill="#ffffff" stroke="{LIME}" stroke-width="1.8"/>')

# ---------- cabeçalho
o.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/><rect width="{W}" height="6" fill="#e5323d"/>')
t(32,46,'Arquitetura ChargeGrid',24,700)
def section(y,s):
    t(32,y,s,12.5,700,SUB); o.append(f'<line x1="32" y1="{y+10}" x2="{W-32}" y2="{y+10}" stroke="#e4e5e9" stroke-width="1.5"/>')
section(78,'CAMADA DE HARDWARE')

# ---------- nuvem e pessoas
t(200,106,'Servidor SEMS Portal',13.5,700,INK,'middle'); t(200,121,'medições do inversor',12.5,400,SUB,'middle'); cloud(200,180,red=True)
t(470,106,'Supabase · ChargeGrid',13.5,700,INK,'middle'); t(470,121,'banco · IA · pagamentos',12.5,400,SUB,'middle'); cloud(470,180,True)
ln([(262,180),(406,180)],'net',True,'both'); t(334,172,'API SEMS',12.5,400,INK,'middle',True)
# gestor e usuário
phone(763,108,lime=True); t(832,112,'GESTOR',12.5,700,BLUE); t(832,132,'App ChargeGrid',13.5,700); t(832,148,'painel e previsão',12.5,400,SUB)
phone(763,200,lime=True); t(832,206,'USUÁRIO',12.5,700,BLUE); t(832,226,'App ChargeGrid',13.5,700); t(832,242,'recarga e Pix',12.5,400,SUB)
ln([(532,180),(690,180)],'net',True,'start'); ln([(690,180),(690,137),(736,137)],'net',True,'end'); ln([(690,180),(690,229),(759,229)],'net',True,'end')
t(610,172,'Realtime · HTTPS',12.5,400,INK,'middle',True)
# roteador
router(200,300); t(244,326,'Roteador',13.5,700,INK,'start',True)
ln([(200,278),(200,206)],'net',True,'end')
ln([(238,292),(440,292),(440,206)],'net',True,'end'); t(340,286,'OCPP 1.6',12.5,400,INK,'middle',True)

# ---------- campo
panels(30,362); t(30,354,'Painéis fotovoltaicos',13.5,700,INK,'start',True)
inverter(170,440); badge(170,440,1); t(225,476,'Inversor',14.5,700,INK,'middle')
ln([(130,406),(130,466),(170,466)],'pot')
# carport e fachada BIPV também geram para o inversor
def scaled(fn,x,y,cx,cy,k=0.8):
    o.append(f'<g transform="translate({cx},{cy}) scale({k}) translate({-cx},{-cy})">'); fn(x,y); o.append('</g>')
scaled(carport,28,232,88,267); t(88,308,'Carport solar',13,700,INK,'middle')
ln([(126,280),(158,280),(158,450),(170,450)],'pot')
scaled(facade,30,432,62,478); t(62,532,'Fachada BIPV',13,700,INK,'middle',True)
ln([(88,500),(170,500)],'pot')
ln([(190,311),(190,440)],'lan'); ln([(212,311),(212,440)],'wifi',True)
t(224,380,'LAN < 100 m',12.5,400,INK,'start',True); t(224,400,'Wi-Fi < 15 m',12.5,400,INK,'start',True)
# bateria
o.append(f'<rect x="30" y="564" width="132" height="98" rx="10" fill="none" stroke="{BLUE}" stroke-width="1.6" stroke-dasharray="6 4"/>')
battery(61,584); badge(30,564,2); t(96,644,'Bateria',13.5,700,INK,'middle'); t(96,658,'BESS 2 × 15 kWh',12,400,SUB,'middle')
ln([(200,536),(200,550),(96,550),(96,578)],'pot')
# barramento da galeria
ln([(280,516),(760,516),(760,450),(796,450)],'pot')
# ramal do carregador
ln([(450,516),(450,504)],'pot'); rcbo(431,470); badge(431,470,3); t(492,492,'RCBO',13.5,700)
ln([(450,470),(450,452)],'pot'); smallmeter(433,410); badge(433,410,5); t(492,436,'Medidor MID',13.5,700)
ln([(467,430),(480,430),(480,376),(475,376)],'rs485')
ln([(450,410),(450,400)],'pot'); wallbox(425,330); badge(425,330,4); t(456,312,'Carregador HCA G2 · ×4',13.5,700,INK,'middle')
ln([(475,350),(528,352)],'pot'); car(530,322); t(589,386,'Veículo elétrico',13.5,700,INK,'middle')
# ESP32 da demonstração
esp32(590,398); t(622,462,'ESP32 da demo',13,700,INK,'middle'); t(622,476,'botão = plugue · LED',12,400,SUB,'middle')
ln([(654,412),(740,412),(740,290),(780,290),(780,262)],'wifi',True,'both'); t(750,340,'Wi-Fi local',12.5,400,INK,'start',True); t(750,356,'(demo)',12,400,SUB,'start',True)
# SolarGo
phone(326,356,26,44,red=True); t(339,418,'SolarGo',13,700,INK,'middle'); t(339,432,'comissionamento',12,400,SUB,'middle')
ln([(352,378),(425,378)],'bt',True,'end'); t(390,370,'< 10 m',12,400,INK,'middle',True)
# edificação (carga da galeria)
ln([(600,516),(600,568)],'pot'); building(552,560); t(600,650,'Edificação · galeria',13.5,700,INK,'middle'); t(600,665,'consumo restante',12,400,SUB,'middle')
# CT e medidor inteligente (no ponto de conexão, depois de todas as cargas)
o.append(f'<circle cx="690" cy="516" r="8" fill="#fff" stroke="{ICON}" stroke-width="2.4"/>'); t(690,500,'CT',12.5,700,INK,'middle',True)
ln([(690,524),(690,556)],'rs485'); smallmeter(673,556); badge(673,556,6)
t(718,574,'Medidor inteligente',13.5,700); t(718,590,'GM3000 · controle',12,400,SUB)
ln([(690,598),(690,712),(230,712),(230,536)],'rs485')
# medidor da concessionária e rede
gauge(820,450); ln([(844,450),(878,450)],'pot'); pylon(880,414)
t(820,410,'Medidor da',12.5,700,INK,'middle'); t(820,424,'concessionária',12.5,700,INK,'middle'); t(820,488,'faturamento',12,400,SUB,'middle')
t(900,508,'Rede elétrica',13.5,700,INK,'middle')
# prioridades: linha do tempo vertical, sem números
px,py=718,612
o.append(f'<rect x="{px}" y="{py}" width="214" height="124" rx="10" fill="#f4f8fe" stroke="{BLUE}" stroke-width="1.4"/>')
t(px+14,py+21,'PRIORIDADE DO SOL · RN001',11.5,700,BLUE)
ys=[py+46,py+76,py+106]
for i,a in enumerate(['Carregador EV','Bateria','Edificação']):
    o.append(f'<circle cx="{px+22}" cy="{ys[i]}" r="5" fill="{BLUE}"/>'); t(px+36,ys[i]+4.5,a,13,700)
for i in range(2):
    o.append(f'<path d="M{px+22},{ys[i]+7} V{ys[i+1]-9}" stroke="{BLUE}" stroke-width="1.5" marker-end="url(#a-net)"/>')

# legenda
ly=760; x=32
for k,s,d in [('pot','Potência',False),('rs485','RS485',False),('lan','LAN',False),('wifi','Wi-Fi',True),('bt','Bluetooth',True),('net','Internet',True)]:
    ln([(x,ly),(x+34,ly)],k,d); t(x+42,ly+4.5,s,13); x+=42+len(s)*7.6+30
ly2=ly+32; x=32
o.append(f'<rect x="{x}" y="{ly2-9}" width="34" height="18" rx="4" fill="{LIMEF}" stroke="{LIME}" stroke-width="2.4"/>'); t(x+42,ly2+4.5,'solução ChargeGrid',13)
x=260
o.append(f'<rect x="{x}" y="{ly2-9}" width="34" height="18" rx="4" fill="{REDF}" stroke="{RED}" stroke-width="2.4"/>'); t(x+42,ly2+4.5,'existe na solução real, mas fora do protótipo',13)

# ---------- fluxo de dados
section(840,'FLUXO DE DADOS')
st=[('Inversor e Medidor','inversor GoodWe: CC → CA','e orquestra a energia','medidor: todo o fluxo'),
    ('Supabase','backend da solução','banco único: sessões','e medições · Realtime'),
    ('Preditividade e','Síndico Virtual','previsão (ML) · DLM','tarifa α · load shifting'),
    ('App','gestor: painel, alertas','motorista: recarga','pagamento Pix/cartão')]
n=len(st); cw=196; gap=(W-64-n*cw)/(n-1)
for i,(a,b,c,d) in enumerate(st):
    x=32+i*(cw+gap); lime=i>0
    o.append(f'<rect x="{x}" y="872" width="{cw}" height="118" rx="12" fill="{LIMEF if lime else "#ffffff"}" stroke="{LIME if lime else "#c9ccd3"}" stroke-width="{2.4 if lime else 1.6}"/>')
    if i==2: t(x+14,899,a,15,700); t(x+14,917,b,15,700); rows=(c,d); y0=948
    else: t(x+14,899,a,15,700); rows=(b,c,d); y0=930
    for j,l in enumerate(rows): t(x+14,y0+j*18,l,12.5,400,SUB)
    if i<n-1: ln([(x+cw+4,931),(x+cw+gap-4,931)],'pot',False,'end',2.4)
x4=32+2*(cw+gap)+cw/2; x1=32+cw/2
ln([(x4,990),(x4,1020),(x1,1020),(x1,994)],'pot',False,'end',2,'#e5323d')
t((x1+x4)/2,1014,'comandos de volta ao carregador: limite de potência do DLM',12.5,700,'#c0212b','middle',True)
t(32,1058,'Inversor e Medidor: os inversores GoodWe transformam corrente contínua em alternada e orquestram a energia;',12.5,400,SUB)
t(32,1077,'o Medidor Inteligente mede todo o fluxo de energia e o comunicaria via OCPP ao SEMS Plus.',12.5,400,SUB)
t(32,1100,'Na demonstração, o ESP32 faz o papel do carregador: o botão é o plugue e o LED mostra o status da vaga.',12.5,400,SUB)
t(32,1119,'Hoje as medições vêm da base simulada de 649 dias; API SEMS, OCPP 1.6 e Realtime são a arquitetura alvo.',12.5,400,SUB)

defs='<defs>'+''.join(f'<marker id="a-{k}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>' for k,c in C.items())+'</defs>'
open('arquitetura.svg','w').write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Nunito, Helvetica, Arial, sans-serif">{defs}{"".join(o)}{"".join(top)}</svg>')
