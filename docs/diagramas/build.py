import sys; sys.path.insert(0,'.')
from lib import *
def dbl(d,pts,**k):  # seta de ida e volta
    k.setdefault('color',LINE)
    d.arrow(pts,**k); d.out[-1]=d.out[-1].replace('marker-end','marker-start="url(#ah)" marker-end')
# ---------------- 1. hoje
d=D(900,940,'Fluxo de dados',None)
d.group(20,100,860,130,'Pipeline de ML · Python, offline','ml')
d.box(40,145,160,64,'Open-Meteo','clima','ml')
d.box(235,145,180,64,'Base simulada','medidor · OCPP · clima','ml')
d.box(450,145,170,64,'ETL','preparar_dataset.py','ml')
d.box(655,145,205,64,'Treino','Random Forest · K-Means','ml')
for a,b in [(200,235),(415,450),(620,655)]: d.arrow([(a,177),(b,177)])
d.box(30,315,170,100,'ESP32 da demo','botão = plugue\nLED = status','hw')
d.group(280,275,600,175,'App ChargeGrid · navegador','app')
d.box(310,315,250,105,'Telas','motorista · gestor\nprospect','app')
d.box(610,315,250,105,'Motor local','previsão · DLM\nα · load shifting','app')
d.arrow([(775,209),(775,315)],num=1,label='árvores exportadas\nno build',lpos=(758,252),anchor='end',npos=(775,246))
d.arrow([(610,367),(560,367)])
d.arrow([(200,345),(310,345)],num=2,label='botão',lpos=(255,325),anchor='middle',npos=(255,345))
d.arrow([(310,392),(200,392)],num=3,label='LED',lpos=(255,424),anchor='middle',npos=(255,392))
d.group(280,520,600,290,'Supabase','supa')
d.box(310,560,250,80,'Edge Function','assistente','supa')
d.box(610,560,250,80,'Edge Function','pagamentos','supa')
d.box(310,700,250,80,'PostgreSQL','pgvector · tabelas da IA\ne dos pagamentos','supa')
d.box(30,570,130,60,'OpenAI')
d.box(610,850,250,60,'Mercado Pago')
dbl(d,[(435,420),(435,560)],num=4,label='pergunta + snapshot',lpos=(414,494),anchor='end',npos=(435,490))
dbl(d,[(540,420),(540,468),(735,468),(735,560)],num=5,label='autorizar · consultar\ncapturar · cancelar',lpos=(552,492),npos=(735,494))
dbl(d,[(310,600),(160,600)],num=6,label='LLM\nembeddings',lpos=(222,626),anchor='middle',npos=(222,600))
dbl(d,[(435,640),(435,700)],num=7,label='RAG · memória · log',lpos=(456,675),npos=(435,670))
dbl(d,[(720,640),(720,850)],num=8,label='Payments API',lpos=(708,838),anchor='end',npos=(720,745))
d.arrow([(830,850),(830,640)],num=9,label='webhook',lpos=(818,838),anchor='end',dashed=True,npos=(830,745))
d.arrow([(640,640),(640,740),(560,740)],num=10,label='split 90/10',lpos=(600,729),anchor='middle',npos=(640,690))
open('fluxo-dados-hoje.svg','w').write(d.svg())
# ---------------- 2. alvo
d=D(900,800,'Fluxo de dados',None)
d.group(20,100,860,140,'Galeria · campo','campo')
d.box(40,145,240,72,'ESP32','processador de estado','hw')
d.box(310,145,270,72,'Smart meter + inversor','GM3000 · BESS','campo')
d.box(610,145,250,72,'Wallbox HCA G2','7 kW · Tipo 2','campo')
d.box(310,300,270,70,'Nuvem SEMS Plus','geração medida')
d.box(610,300,250,70,'Gateway OCPP 1.6','Modbus → OCPP')
d.arrow([(445,217),(445,300)],num=1,label='RS485 · Modbus',lpos=(467,263),npos=(445,258))
d.arrow([(735,217),(735,300)],num=2,label='Modbus',lpos=(757,263),npos=(735,258))
d.group(20,440,860,170,'Supabase','supa')
d.box(40,488,380,90,'PostgreSQL','ER de 15 tabelas','supa')
d.box(480,488,380,90,'Edge Functions','previsão · DLM · α · load shifting','supa')
dbl(d,[(120,217),(120,488)],num=3,label='HTTPS: plugue, kWh\nRealtime: parâmetros',lpos=(135,330),npos=(120,280))
d.arrow([(360,370),(360,488)],num=4,label='API SEMS',lpos=(382,412),npos=(360,420))
d.arrow([(645,370),(645,488)],num=5,label='MeterValues ·\nStatusNotification',lpos=(632,400),anchor='end',npos=(645,466))
d.arrow([(830,488),(830,370)],num=6,label='SetChargingProfile\n(limite do DLM)',lpos=(816,400),anchor='end',npos=(830,466))
dbl(d,[(420,533),(480,533)],num=7,npos=(450,533))
d.box(40,690,380,72,'App ChargeGrid','motorista · gestor · prospect','app')
d.box(480,690,380,72,'Open-Meteo','previsão de irradiância')
d.arrow([(170,578),(170,690)],num=8,label='Realtime',lpos=(192,648),npos=(170,634))
d.arrow([(310,690),(310,578)],num=9,label='comandos · pagamentos',lpos=(332,648),npos=(310,634))
d.arrow([(670,690),(670,578)],num=10,label='previsão do tempo',lpos=(692,648),npos=(670,634))
open('fluxo-dados-alvo.svg','w').write(d.svg())
# ---------------- 3. recarga
lanes=[('Motorista','',112,'ext'),('ESP32','vaga',256,'hw'),('App','navegador',400,'app'),('Pagamentos','Edge Function',543,'supa'),('Mercado Pago','',687,'ext'),('Supabase','banco',830,'supa')]
X={k:x for k,_,x,_ in lanes}
msgs=[('P','Escolha da recarga'),
 ('Motorista','App','lê o QR Code e escolhe a meta',0),
 ('App','App','estimativa = kWh × preço do ponto',0),
 ('P','Plugue (só com o ESP32 na rede)'),
 ('Motorista','ESP32','aperta o botão = plugue',0),
 ('App','ESP32','lê /button a cada 400 ms',0),
 ('ESP32','App','evento do plugue',1),
 ('App','ESP32','LED âmbar: aguardando',0),
 ('P','Pré-autorização'),
 ('Motorista','App','Pagar e liberar carga',0),
 ('App','Pagamentos','POST /autorizar',0),
 ('Pagamentos','Mercado Pago','cartão: reserva · Pix: cobra e gera QR',0),
 ('Pagamentos','Supabase','grava valor_autorizado',0),
 ('Pagamentos','App','autorizado (ou QR do Pix)',1),
 ('App','Pagamentos','Pix: /consultar a cada 1 s até aprovar',0),
 ('Mercado Pago','Pagamentos','webhook de status',1),
 ('P','Sessão'),
 ('App','App','trava a tarifa e inicia a sessão',0),
 ('App','ESP32','LED verde: carregando',0),
 ('App','App','kWh e custo a cada 1 s',0),
 ('P','Encerramento e cobrança'),
 ('Motorista','App','Encerrar (no app ou no botão)',0),
 ('App','ESP32','LED azul: disponível',0),
 ('App','Pagamentos','POST /capturar (kWh × tarifa)',0),
 ('Pagamentos','Mercado Pago','cartão: captura parcial · Pix: estorna a sobra',0),
 ('Pagamentos','Supabase','valor_total · split 90/10',0),
 ('Pagamentos','App','valor capturado e estornado',1),
 ('App','Motorista','recibo com CO₂ evitado',1)]
H=170+sum(48 if m[0]=='P' else (56 if m[0]==m[1] else 46) for m in msgs)+40
d=D(900,H,'Fluxo de uma recarga',None)
for n,s,x,k in lanes:
    d.box(x-66,95,132,52,n,s or None,k)
    d.raw(f'<line x1="{x}" y1="147" x2="{x}" y2="{H-30}" stroke="#c9ccd3" stroke-width="2" stroke-dasharray="2 5"/>')
y=175; i=0
for m in msgs:
    if m[0]=='P':
        d.raw(f'<rect x="12" y="{y+8}" width="876" height="28" rx="8" fill="#f4f5f7"/>')
        d.text(24,y+27,m[1],size=13.5,color=INK,weight=700); y+=48; continue
    a,b,l,dash=m; i+=1; xa,xb=X[a],X[b]; y+=33
    if a==b:
        d.arrow([(xa,y-10),(xa+40,y-10),(xa+40,y+6),(xa+5,y+6)],dashed=dash)
        d.top.append(f'<text x="{xa+52}" y="{y+3}" font-size="13.5" fill="{INK}" stroke="#ffffff">{esc(l)}</text>')
        y+=10
    else:
        dirn=1 if xb>xa else -1
        d.arrow([(xa,y),(xb-dirn*3,y)],dashed=dash,label=l,lpos=((xa+xb)/2,y-9),anchor='middle')
        d.raw(f'<circle cx="{xa}" cy="{y}" r="4" fill="{LINE}"/>')
    y+=12
open('fluxo-recarga.svg','w').write(d.svg())
