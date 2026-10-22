# compõe as figuras vetoriais em 16:9 (1600x900), mantendo o desenho original
import re
from html import escape as esc
D='diag/'
def inner(path,vx,vy,vw,vh,x,y,w,h):
    s=open(D+path).read()
    s=re.sub(r'<svg [^>]*?>', f'<svg x="{x}" y="{y}" width="{w}" height="{h}" viewBox="{vx} {vy} {vw} {vh}" preserveAspectRatio="xMidYMid meet" font-family="Nunito, Helvetica, Arial, sans-serif">',s,count=1)
    return s
def fit(vw,vh,W,H):
    k=min(W/vw,H/vh); return vw*k,vh*k
BG='#f4f5f7'; INK='#14171f'; SUB='#4d5462'
LIME='#7dbb00'; LIMEF='#f2fbd6'
def base(): return [f'<rect width="1600" height="900" fill="{BG}"/>','<rect width="1600" height="8" fill="#e5323d"/>']
def panel(x,y,w,h): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="22" fill="#ffffff" stroke="#e1e3e8" stroke-width="2"/>'
def T(x,y,s,size,w=400,c=INK,a='start'): return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{w}" fill="{c}" text-anchor="{a}">{esc(s)}</text>'
def out(name,parts):
    open('s169/'+name+'.svg','w').write('<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" viewBox="0 0 1600 900" font-family="Nunito, Helvetica, Arial, sans-serif">'+''.join(parts)+'</svg>')

# ---------- 1 · arquitetura + fluxo de dados
p=base()
p.append(panel(40,160,980,712))
w,h=fit(930,718,950,690); p.append(inner('arquitetura.svg',15,92,930,718,40+(980-w)/2,170,w,h))
p.append(panel(1040,160,520,712))
p.append(T(1068,200,'FLUXO DE DADOS',15,700,'#7a818d'))
st=[('Inversor e Medidor',['Os inversores GoodWe transformam corrente','contínua em alternada e orquestram a energia.','O Medidor Inteligente mede todo o fluxo de','energia e o comunicaria via OCPP ao SEMS Plus.'],False),
    ('Supabase',['backend da solução','banco único: sessões e medições','Realtime para o app'],True),
    ('Preditividade e Síndico Virtual',['Base sintética horária de 649 dias, calibrada','para SP e com falhas de telemetria, treina','Random Forest (R² 0,961 na galeria) e K-Means.','Saída: previsão, DLM, tarifa α e load shifting.'],True),
    ('App',['gestor: painel e alertas','motorista: recarga e Pix'],True)]
cy=[]; y=214
for i,(a,ls,lime) in enumerate(st):
    hh=64+22*(len(ls)-1)+26; cy.append((y,hh))
    p.append(f'<rect x="1066" y="{y}" width="420" height="{hh}" rx="14" fill="{LIMEF if lime else "#ffffff"}" stroke="{LIME if lime else "#c9ccd3"}" stroke-width="{2.6 if lime else 1.8}"/>')
    p.append(T(1088,y+36,a,20,700))
    for j,l in enumerate(ls): p.append(T(1088,y+64+j*22,l,14.5 if len(ls)>3 else 15,400,SUB))
    if i<3: p.append(f'<path d="M1276,{y+hh+2} V{y+hh+26}" stroke="{INK}" stroke-width="2.6" marker-end="url(#ak)"/>')
    y+=hh+30
# volta do DLM ao carregador
y4=cy[2][0]+cy[2][1]//2; y1=cy[0][0]+cy[0][1]//2
p.append(f'<path d="M1486,{y4} H1522 V{y1} H1492" fill="none" stroke="#e5323d" stroke-width="2.6" marker-end="url(#ar)"/>')
p.append(f'<text transform="translate(1542,{(y1+y4)/2}) rotate(-90)" font-size="13.5" font-weight="700" fill="#c0212b" text-anchor="middle">limite de potência do DLM</text>')
p.insert(0,'<defs><marker id="ak" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#14171f"/></marker><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#e5323d"/></marker></defs>')
out('s_arquitetura',p)

# ---------- 2 · fluxo detalhado
p=base()
p.append(panel(40,160,752,610)); p.append(panel(808,160,752,610)); p.append(panel(40,786,1520,98))
k=732/936
p.append(inner('fluxo-detalhado.svg',12,66,936,744,50,172,936*k,744*k))
p.append(inner('fluxo-detalhado.svg',12,66,936,38,818,172,936*k,38*k))
p.append(inner('fluxo-detalhado.svg',12,810,936,276,818,172+38*k,936*k,276*k))
p.append(inner('fluxo-detalhado.svg',12,1098,936,96,40+(1520-936*0.98)/2,788,936*0.98,96*0.98))
y0=172+(38+276)*k+26
p.append(T(832,y0+20,'STACK',16,700,'#7a818d'))
chips=['C++ · Arduino','React 18','JavaScript','Deno · TypeScript','LangGraph.js','PostgreSQL 16 · pgvector','pandas · scikit-learn','Supabase Edge Functions','Google Maps','Mercado Pago','OpenAI','Open-Meteo']
x=832; y=y0+40
for c in chips:
    wd=len(c)*8.0+28
    if x+wd>1235: x=832; y+=48
    p.append(f'<rect x="{x}" y="{y}" width="{wd}" height="36" rx="18" fill="#eef4ff" stroke="#1e6fc8" stroke-width="1.4"/>'); p.append(T(x+14,y+24,c,14,700,'#1e6fc8'))
    x+=wd+9
# protótipo físico do carregador (foto sem fundo), à direita da stack
import base64
from PIL import Image as _I
_c=_I.open('s169/carregador.png'); _c=_c.crop((0,0,_c.width,int(_c.height*0.80))); _c.save('s169/carregador_top.png')
# card em destaque com borda limão
X0,X1,Y0,Y1=1250,1546,y0-10,764
p.append(f'<rect x="{X0}" y="{Y0}" width="{X1-X0}" height="{Y1-Y0}" rx="20" fill="#ffffff" stroke="#7dbb00" stroke-width="3"/>')
p.append(T(X0+20,Y0+30,'PROTÓTIPO FÍSICO',13,800,'#4e9a06'))
_h=Y1-Y0-104; _w=_h*_c.width/_c.height; _cx=(X0+X1)/2
p.append(f'<image href="data:image/png;base64,{base64.b64encode(open("s169/carregador_top.png","rb").read()).decode()}" x="{_cx-_w/2}" y="{Y0+42}" width="{_w}" height="{_h}"/>')
p.append(T(X0+20,Y1-36,'Carregador GoodWe + ESP32',14,700,INK)); p.append(T(X0+20,Y1-16,'botão = plugue · LED = status',13,400,SUB))
out('s_detalhado',p)
print('ok')
