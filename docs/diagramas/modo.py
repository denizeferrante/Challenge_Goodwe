from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':430,'height':900},device_scale_factor=2)
    pg.goto('file:///tmp/claude-0/-home-claude/2cf14cae-215a-5ad0-97e3-6c5a7c050eb7/scratchpad/app-sandbox.html'); pg.wait_for_timeout(2500)
    pg.get_by_text('Motorista',exact=True).first.click(); pg.wait_for_timeout(1000)
    pg.get_by_text('Entrar como motorista',exact=True).first.click(); pg.wait_for_timeout(1200)
    pg.get_by_text('Já estou no eletroposto',exact=True).first.click(); pg.wait_for_timeout(3500)
    pg.get_by_text('Continuar',exact=True).first.click(); pg.wait_for_timeout(1500)
    pg.get_by_text('Tempo de permanência',exact=True).first.click(); pg.wait_for_timeout(1000)
    inp=pg.locator('input >> visible=true').first
    try: inp.fill('45'); inp.evaluate('e=>e.blur()'); pg.mouse.move(5,890); pg.wait_for_timeout(800)
    except Exception as e: print('fill',e)
    print(pg.locator('body').inner_text()[:700]); pg.screenshot(path='shots/m_modo_tempo.png')
    b.close()
