from playwright.sync_api import sync_playwright
import sys
with sync_playwright() as p:
    b=p.chromium.launch()
    for f in sys.argv[1:]:
        svg=open(f).read()
        import re; w,h=map(int,re.search(r'width="(\d+)" height="(\d+)"',svg).groups())
        pg=b.new_page(viewport={'width':w,'height':h},device_scale_factor=2)
        pg.set_content(f'<html><body style="margin:0">{svg}</body></html>'); pg.wait_for_timeout(300)
        pg.screenshot(path=f.replace('.svg','.png'),clip={'x':0,'y':0,'width':w,'height':h})
    b.close()
