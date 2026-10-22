from playwright.sync_api import sync_playwright
JS='''()=>{let best=null;document.querySelectorAll('*').forEach(e=>{const s=getComputedStyle(e);if(/(auto|scroll)/.test(s.overflowY)&&e.scrollHeight>e.clientHeight+20){if(!best||e.scrollHeight>best.scrollHeight)best=e}});return best?[best.scrollHeight,best.clientHeight]:null}'''
def box(pg,t):
    return pg.get_by_text(t,exact=True).first.bounding_box()
with sync_playwright() as p:
    b=p.chromium.launch()
    for tab,clicks,marks,out in [
        ('Painel',['Consumo solar e da rede por período','Carregadores EV'],['Consumo solar e da rede por período','Carregadores EV'],'painel_full'),
        ('Financeiro',['Detalhe por destino'],['Distribuição da energia solar','Detalhe por destino'],'fin_full2')]:
        pg=b.new_page(viewport={'width':430,'height':900},device_scale_factor=2)
        pg.goto('file:///tmp/claude-0/-home-claude/2cf14cae-215a-5ad0-97e3-6c5a7c050eb7/scratchpad/app-sandbox.html'); pg.wait_for_timeout(2500)
        for t in ['Gestor','Entrar como gestor da galeria','Acesse o ChargeGrid',tab]:
            pg.get_by_text(t,exact=True).first.click(); pg.wait_for_timeout(1000)
        for t in clicks:
            try: pg.get_by_text(t,exact=False).first.click(); pg.wait_for_timeout(900)
            except Exception as e: print('fail',t,e)
        h=pg.evaluate(JS); print(out,'scroll',h)
        if h: pg.set_viewport_size({'width':430,'height':900+h[0]-h[1]}); pg.wait_for_timeout(1500)
        pg.screenshot(path=f'shots/{out}.png',full_page=True)
        for t in marks+['Carregadores EV','Distribuição da energia solar','Gasto com energia da rede','Geração solar por período','Consumo hoje','Economia = o que']:
            try: print(' ',t,pg.get_by_text(t,exact=False).first.bounding_box(timeout=1000))
            except Exception: pass
        pg.close()
    b.close()
