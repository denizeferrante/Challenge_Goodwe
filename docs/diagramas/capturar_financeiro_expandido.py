from playwright.sync_api import sync_playwright
import sys
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':430,'height':900},device_scale_factor=2)
    pg.goto('file:///tmp/claude-0/-home-claude/2cf14cae-215a-5ad0-97e3-6c5a7c050eb7/scratchpad/app-sandbox.html'); pg.wait_for_timeout(2500)
    for t in ['Gestor','Entrar como gestor da galeria','Acesse o ChargeGrid','Financeiro']:
        pg.get_by_text(t,exact=True).first.click(); pg.wait_for_timeout(1000)
    pg.get_by_text('Faturamento',exact=True).first.click(); pg.wait_for_timeout(800)
    pg.get_by_text('Gasto com energia da rede',exact=True).first.click(); pg.wait_for_timeout(800)
    # mede o conteúdo rolável
    h=pg.evaluate('''()=>{let best=null;document.querySelectorAll('*').forEach(e=>{const s=getComputedStyle(e);if(/(auto|scroll)/.test(s.overflowY)&&e.scrollHeight>e.clientHeight+20){if(!best||e.scrollHeight>best.scrollHeight)best=e}});return best?[best.scrollHeight,best.clientHeight]:null}''')
    print('scroll',h)
    pg.set_viewport_size({'width':430,'height':900+h[0]-h[1]}); pg.wait_for_timeout(1500)
    pg.screenshot(path='shots/fin_full.png',full_page=True)
    b.close()
