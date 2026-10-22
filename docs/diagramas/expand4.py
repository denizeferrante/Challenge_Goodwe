from playwright.sync_api import sync_playwright
JS='''()=>{let best=null;document.querySelectorAll('*').forEach(e=>{const s=getComputedStyle(e);if(/(auto|scroll)/.test(s.overflowY)&&e.scrollHeight>e.clientHeight+20){if(!best||e.scrollHeight>best.scrollHeight)best=e}});return best?[best.scrollHeight,best.clientHeight]:null}'''
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':430,'height':900},device_scale_factor=2)
    pg.goto('file:///tmp/claude-0/-home-claude/2cf14cae-215a-5ad0-97e3-6c5a7c050eb7/scratchpad/app-sandbox.html'); pg.wait_for_timeout(2500)
    for t in ['Gestor','Entrar como gestor da galeria','Acesse o ChargeGrid','Financeiro']:
        pg.get_by_text(t,exact=True).first.click(); pg.wait_for_timeout(1000)
    print('n',pg.get_by_text('Detalhe por destino',exact=True).count()); el=pg.locator('button:has-text("Detalhe por destino") >> visible=true').first
    print(el.evaluate('e=>e.parentElement.outerHTML.slice(0,300)'))
    pass
    print(pg.get_by_text('ocultar',exact=False).count(), pg.get_by_text('DESTINO',exact=True).count(), pg.get_by_text('Destino',exact=True).count())
    print(pg.get_by_text('Total',exact=True).count())
    h=pg.evaluate(JS); print(h)
    pg.set_viewport_size({'width':430,'height':900+h[0]-h[1]}); pg.wait_for_timeout(1500)
    pg.screenshot(path='shots/fin_full2.png',full_page=True)
    for t in ['Distribuição da energia solar','Economia = o que','Repasse do mês','Total']:
        print(t,pg.get_by_text(t,exact=False).first.bounding_box())
    b.close()
