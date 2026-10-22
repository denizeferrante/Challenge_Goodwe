from playwright.sync_api import sync_playwright
import sys
JS=r'''() => {
 const svg=document.querySelector('svg'); const out=[];
 const boxes=[...svg.querySelectorAll('rect')].filter(r=>r.getAttribute('rx')==='10').map(r=>({x0:+r.getAttribute('x'),y0:+r.getAttribute('y'),x1:+r.getAttribute('x')+ +r.getAttribute('width'),y1:+r.getAttribute('y')+ +r.getAttribute('height')}));
 const S=[];[...svg.querySelectorAll('path')].forEach((p,pi)=>{if(p.closest('marker'))return;const d=p.getAttribute('d').replace(/[ML]/g,' ').trim().split(/\s+/).map(q=>q.split(',').map(Number));for(let k=0;k<d.length-1;k++)S.push({pi,a:d[k],b:d[k+1]});});
 const inside=(x,y,r,m)=>x>r.x0+m&&x<r.x1-m&&y>r.y0+m&&y<r.y1-m;
 for(const s of S){ for(const r of boxes){ // amostra o segmento
   for(let t=0.05;t<0.96;t+=0.05){const x=s.a[0]+(s.b[0]-s.a[0])*t,y=s.a[1]+(s.b[1]-s.a[1])*t; if(inside(x,y,r,1)){out.push(['seta atravessa caixa',JSON.stringify([s.a,s.b]),JSON.stringify(r)]);break;}}}}
 const cross=(p,q)=>{const [a,b]=[p.a,p.b],[c,d]=[q.a,q.b];
   const h1=a[1]===b[1],h2=c[1]===d[1]; if(h1===h2) return false;
   const H=h1?p:q,V=h1?q:p; const y=H.a[1],x=V.a[0];
   const inH=x>Math.min(H.a[0],H.b[0])+1&&x<Math.max(H.a[0],H.b[0])-1, inV=y>Math.min(V.a[1],V.b[1])+1&&y<Math.max(V.a[1],V.b[1])-1; return inH&&inV;};
 for(let i=0;i<S.length;i++)for(let j=i+1;j<S.length;j++) if(S[i].pi!==S[j].pi&&cross(S[i],S[j])) out.push(['setas se cruzam',JSON.stringify([S[i].a,S[i].b]),JSON.stringify([S[j].a,S[j].b])]);
 // rótulos x linhas de vida
 const L=[...svg.querySelectorAll('line')].map(l=>+l.getAttribute('x1'));
 [...svg.querySelectorAll('text')].forEach(t=>{const b=t.getBBox(); if(t.getAttribute('fill')==='#fff')return; const pr=t.previousElementSibling; if(pr&&pr.getAttribute('class')==='lbl')return; if(t.getAttribute('font-weight')==='700'&&t.getAttribute('x')==='24')return; for(const x of L) if(x>b.x&&x<b.x+b.width && b.y>140) {out.push(['rótulo sobre linha de vida',t.textContent,x]);break;}});
 return out;}'''
with sync_playwright() as p:
    b=p.chromium.launch()
    for f in sys.argv[1:]:
        pg=b.new_page(); pg.set_content('<html><body style="margin:0">'+open(f).read()+'</body></html>'); pg.wait_for_timeout(300)
        r=pg.evaluate(JS); print('==',f,len(r)); [print('  ',*x) for x in r]
    b.close()
