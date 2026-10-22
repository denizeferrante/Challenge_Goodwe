from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':430,'height':900},device_scale_factor=2)
    pg.goto('file:///tmp/claude-0/-home-claude/2cf14cae-215a-5ad0-97e3-6c5a7c050eb7/scratchpad/app-sandbox.html'); pg.wait_for_timeout(2500)
    pg.get_by_text('Motorista',exact=True).first.click(); pg.wait_for_timeout(1200)
    for t in ['Entrar como motorista','Entrar']:
        try: pg.get_by_text(t,exact=True).first.click(timeout=1500); pg.wait_for_timeout(1000); print('ok',t)
        except Exception: print('no',t)
    pg.screenshot(path='shots/tmp1.png')
    pg.get_by_text('Casa',exact=True).last.click(); pg.wait_for_timeout(1000)
    pg.locator('button:has-text("Entrar") >> visible=true').first.click(); pg.wait_for_timeout(2500)
    pg.screenshot(path='shots/m_smarthome.png')
    b.close()
