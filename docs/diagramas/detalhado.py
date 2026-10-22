from html import escape as esc
W,H=960,960
INK='#14171f'; SUB='#4d5462'; LINE='#3a4150'
STY={'lime':('#f2fbd6','#7dbb00'),'red':('#fdeeee','#e5323d'),'gray':('#ffffff','#9aa1ad'),'ml':('#fff6e6','#c98a12')}
o=[]; top=[]
def t(x,y,s,size=13,w=400,c=INK,a='start',bg=False):
    (top if bg else o).append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{w}" fill="{c}" text-anchor="{a}"{" stroke=\"#ffffff\"" if bg else ""}>{esc(s)}</text>')
def box(x,y,w,h,kind,title,lines=(),alvo=False,tech=None):
    f,c=STY[kind]
    o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{f}" stroke="{c}" stroke-width="2.2"{" stroke-dasharray=\"7 4\"" if alvo else ""}/>')
    t(x+12,y+22,title,13.5,700)
    for i,l in enumerate(lines): t(x+12,y+40+i*16,l,12,400,SUB)
    if tech:
        o.append(f'<line x1="{x+12}" y1="{y+h-24}" x2="{x+w-12}" y2="{y+h-24}" stroke="{c}" stroke-opacity="0.45" stroke-width="1"/>')
        t(x+12,y+h-9,tech,11.5,700,'#1e6fc8')
def ar(pts,dash=False,both=False,w=2):
    d='M'+' L'.join(f'{a},{b}' for a,b in pts)
    o.append(f'<path d="{d}" fill="none" stroke="{LINE}" stroke-width="{w}"{" stroke-dasharray=\"6 5\"" if dash else ""} marker-end="url(#ah)"{" marker-start=\"url(#ah)\"" if both else ""}/>')
o.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/><rect width="{W}" height="6" fill="#e5323d"/>')
t(32,46,'Fluxo de dados detalhado',24,700)
C=[(20,160,'Dispositivos'),(230,170,'APIs e integrações'),(450,230,'Backend'),(730,210,'App ChargeGrid')]
for x,w,s in C:
    o.append(f'<rect x="{x}" y="72" width="{w}" height="28" rx="14" fill="{INK}"/>'); t(x+w/2,91,s,13.5,700,'#ffffff','middle')
X={i:(x,w) for i,(x,w,_) in enumerate(C)}
def cb(i,y0,kind,title,lines=(),alvo=False,tech=None,h=104):
    x,w=X[i]; box(x,y0+20,w,h,kind,title,lines,alvo,tech)
def row(y0,cap):
    t(20,y0+12,cap,11.5,700,'#7a818d'); o.append(f'<line x1="20" y1="{y0}" x2="{W-20}" y2="{y0}" stroke="#eceef2" stroke-width="1.2"/>')
R=lambda i:120+i*138
def gap(i,j,y,dash=False,both=False):
    a=X[i][0]+X[i][1]; b=X[j][0]
    if i<j: ar([(a,y),(b,y)],dash,both)
    else:
        a=X[i][0]; b=X[j][0]+X[j][1]; ar([(a,y),(b,y)],dash,both)

# 1 demonstração física
y=R(0); row(y,'DEMONSTRAÇÃO FÍSICA')
cb(0,y,'lime','ESP32',('botão = plugue','LED WS2812B'),tech='C++ · Arduino · NeoPixel')
cb(3,y,'lime','Integração com o ESP32',('hwPoll · hwSet','em app.js'),tech='JavaScript · fetch')
ar([(180,y+58),(730,y+58)]); t(455,y+52,'evento do botão · GET /button a cada 400 ms',12,400,INK,'middle',True)
ar([(730,y+86),(180,y+86)]); t(455,y+80,'cor do LED · GET /led',12,400,INK,'middle',True)
# mapa e rotas
y=R(1); row(y,'MAPA E ROTAS')
cb(1,y,'lime','Google Maps',('mapa embutido (iframe)','rota: Maps URLs (api=1)','postos e trajeto'),tech='Maps Embed · Maps URLs')
cb(3,y,'lime','Encontrar recarga',('postos com status','“Ir até lá” abre a rota'),tech='React 18 · Claude Design')
gap(3,1,y+72,False,True) if False else ar([(730,y+72),(400,y+72)],False,True)
t(565,y+64,'coordenadas do posto',12,400,INK,'middle',True)
# 2 recarga OCPP
y=R(2); row(y,'RECARGA · OCPP 1.6')
cb(0,y,'gray','Carregador HCA G2',('Modbus nativo','7 kW por vaga'),tech='firmware GoodWe')
cb(1,y,'gray','Gateway OCPP 1.6',('MeterValues','StatusNotification'),alvo=True,tech='OCPP-J · WebSocket')
cb(2,y,'lime','Tabelas da sessão',('recargas · recarga_eventos','alocacoes_potencia','DLM → SetChargingProfile'),alvo=True,tech='PostgreSQL 16 · Supabase')
cb(3,y,'lime','Telas da sessão',('kWh, kW e custo ao vivo','hoje: estado em memória'),tech='React 18 · Claude Design')
gap(0,1,y+58,True); gap(1,2,y+58,True); gap(2,1,y+86,True); gap(1,0,y+86,True); gap(2,3,y+72,True)
# 3 energia
y=R(3); row(y,'ENERGIA DA GALERIA')
cb(0,y,'gray','Inversor + GM3000',('geração, bateria','importação e exportação'),tech='RS485 · Modbus RTU')
cb(1,y,'red','API SEMS Plus',('geração medida','usada para faturar'),alvo=True,tech='REST · HTTPS')
cb(2,y,'lime','leituras_energia',('medições a cada 5 min','teto do DLM'),alvo=True,tech='PostgreSQL · Edge Functions')
cb(3,y,'lime','Painel e Financeiro',('fluxo de energia','hoje: dados simulados'),tech='React 18 · Claude Design')
gap(0,1,y+72,True); gap(1,2,y+72,True); gap(2,3,y+72,True)
# 4 previsão
y=R(4); row(y,'PREVISÃO DE DEMANDA')
cb(1,y,'lime','API Open-Meteo',('clima e irradiância','previsão de 7 dias'),tech='REST · ERA5')
cb(2,y,'ml','Pipeline de ML · Python',('ETL da base simulada','Random Forest · K-Means','exporta previsao-dados.js'),tech='pandas · scikit-learn · Jupyter')
cb(3,y,'lime','Motor local',('previsao-motor.js','DLM · tarifa α','load shifting · alertas'),tech='JavaScript')
gap(1,2,y+72); gap(2,3,y+72)
# 5 IA
y=R(5); row(y,'ASSISTENTE IA E SÍNDICO VIRTUAL')
cb(1,y,'lime','API OpenAI',('gpt-4o-mini','text-embedding-3-small'),tech='REST · function calling')
cb(2,y,'lime','Edge Function assistente',('grafo com guardrails','RAG: ia_conhecimento (pgvector)','log: ia_turnos'),tech='Deno · TypeScript · LangGraph.js')
cb(3,y,'lime','assistente.js',('pergunta + snapshot do ML','fallback: regras locais'),tech='JavaScript')
gap(2,1,y+72,False,True); gap(3,2,y+72,False,True)
# 6 pagamento
y=R(6); row(y,'PAGAMENTO')
cb(1,y,'lime','API Mercado Pago',('/v1/payments · /refunds','Pix · cartão','webhook de status'),tech='REST · sandbox')
cb(2,y,'lime','Edge Function pagamentos',('autorizar · consultar','capturar · cancelar','transacoes_pagamento · 90/10'),tech='Deno · TypeScript')
cb(3,y,'lime','gateway.js',('pré-autorização','captura dos kWh entregues'),tech='JavaScript')
gap(2,1,y+58); gap(1,2,y+86)
gap(3,2,y+72,False,True)
# legenda
ly=R(7)+20; o.append(f'<line x1="20" y1="{ly-14}" x2="{W-20}" y2="{ly-14}" stroke="#eceef2" stroke-width="1.2"/>')
x=20
for k,s in [('lime','solução ChargeGrid'),('red','solução real, fora do protótipo'),('gray','hardware e integração externos'),('ml','pipeline offline')]:
    f,c=STY[k]; o.append(f'<rect x="{x}" y="{ly}" width="30" height="18" rx="4" fill="{f}" stroke="{c}" stroke-width="2.2"/>'); t(x+38,ly+14,s,12.5); x+=38+len(s)*6.9+24
ly2=ly+34
ar([(20,ly2+9),(56,ly2+9)]); t(64,ly2+13.5,'funciona hoje',12.5)
ar([(190,ly2+9),(226,ly2+9)],True); t(234,ly2+13.5,'arquitetura alvo',12.5)
t(20,ly2+44,'Texto em azul: linguagem e framework de cada componente',12.5,700,'#1e6fc8')
o.append(f'<rect x="370" y="{ly2}" width="30" height="18" rx="4" fill="#fff" stroke="#9aa1ad" stroke-width="2.2" stroke-dasharray="7 4"/>'); t(408,ly2+13.5,'componente ainda não implementado',12.5)
defs=f'<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{LINE}"/></marker></defs>'
Hh=ly2+64
open('fluxo-detalhado.svg','w').write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{Hh}" viewBox="0 0 {W} {Hh}" font-family="Nunito, Helvetica, Arial, sans-serif">{defs}{"".join(o)}{"".join(top)}</svg>')
