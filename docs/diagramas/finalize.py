# põe um fundo branco atrás de cada rótulo de seta e reescreve o SVG
from playwright.sync_api import sync_playwright
import sys
JS=r'''() => {const svg=document.querySelector('svg'); const NS='http://www.w3.org/2000/svg';
 svg.querySelectorAll('rect.lbl').forEach(r=>r.remove());
 [...svg.querySelectorAll('text[stroke="#ffffff"]')].forEach(t=>{const b=t.getBBox();
   const r=document.createElementNS(NS,'rect'); r.setAttribute('class','lbl');
   r.setAttribute('x',(b.x-4).toFixed(1)); r.setAttribute('y',(b.y-1).toFixed(1));
   r.setAttribute('width',(b.width+8).toFixed(1)); r.setAttribute('height',(b.height+2).toFixed(1));
   r.setAttribute('rx','4'); r.setAttribute('fill','#ffffff'); t.parentNode.insertBefore(r,t);
   t.removeAttribute('stroke'); t.removeAttribute('stroke-width'); t.removeAttribute('paint-order');});
 return svg.outerHTML;}'''
with sync_playwright() as p:
    b=p.chromium.launch()
    for f in sys.argv[1:]:
        pg=b.new_page(); pg.set_content('<html><body style="margin:0">'+open(f).read()+'</body></html>'); pg.wait_for_timeout(300)
        open(f,'w').write(pg.evaluate(JS))
    b.close()
