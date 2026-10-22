from playwright.sync_api import sync_playwright
import sys, json
JS=r'''() => {
 const svg=document.querySelector('svg'); const P=4; // padding
 const T=[...svg.querySelectorAll('text')].map((t,i)=>{const b=t.getBBox();return {i,s:t.textContent,x0:b.x-P,y0:b.y,x1:b.x+b.width+P,y1:b.y+b.height, badge: !!(t.previousElementSibling&&t.previousElementSibling.tagName==='circle'&&t.getAttribute('fill')==='#fff')}});
 const C=[...svg.querySelectorAll('circle')].filter(c=>+c.getAttribute('r')>=10).map(c=>({x:+c.getAttribute('cx'),y:+c.getAttribute('cy'),r:+c.getAttribute('r')}));
 const R=[...svg.querySelectorAll('rect')].slice(2).filter(r=>r.getAttribute('class')!=='lbl').map(r=>({x0:+r.getAttribute('x'),y0:+r.getAttribute('y'),x1:+r.getAttribute('x')+ +r.getAttribute('width'),y1:+r.getAttribute('y')+ +r.getAttribute('height')}));
 const S=[]; [...svg.querySelectorAll('path,line')].forEach(p=>{ if(p.closest('marker'))return;
   let pts=[]; if(p.tagName==='line'){return;} // linhas de vida: ignoradas
   const d=p.getAttribute('d').replace(/[ML]/g,' ').trim().split(/\s+/).map(q=>q.split(',').map(Number));
   for(let k=0;k<d.length-1;k++) S.push([d[k],d[k+1]]);});
 const hitSeg=(t,[a,b])=>{ // segmento horizontal/vertical vs caixa
   const xa=Math.min(a[0],b[0]),xb=Math.max(a[0],b[0]),ya=Math.min(a[1],b[1]),yb=Math.max(a[1],b[1]);
   return xb>=t.x0&&xa<=t.x1&&yb>=t.y0&&ya<=t.y1;};
 const out=[];
 const tx=T.filter(t=>!t.badge);
 for(const t of tx){
   for(const u of tx) if(u.i>t.i && t.x1>u.x0&&u.x1>t.x0&&t.y1>u.y0&&u.y1>t.y0) out.push(['texto×texto',t.s,u.s]);
   for(const s of S) if(hitSeg(t,s)) out.push(['texto×seta',t.s,JSON.stringify(s)]);
   for(const c of C){const nx=Math.max(t.x0,Math.min(c.x,t.x1)),ny=Math.max(t.y0,Math.min(c.y,t.y1)); if((nx-c.x)**2+(ny-c.y)**2<(c.r+1)**2) out.push(['texto×número',t.s,c.x+','+c.y]);}
   for(const r of R){const inside=t.x0>=r.x0&&t.x1<=r.x1&&t.y0>=r.y0&&t.y1<=r.y1; const inter=t.x1>r.x0&&r.x1>t.x0&&t.y1>r.y0&&r.y1>t.y0; if(inter&&!inside) out.push(['texto×borda',t.s,JSON.stringify(r)]);}
 }
 for(const c of C) for(const r of R){ const nearX=Math.min(Math.abs(c.x-r.x0),Math.abs(c.x-r.x1)), nearY=Math.min(Math.abs(c.y-r.y0),Math.abs(c.y-r.y1)); const inY=c.y>r.y0-c.r&&c.y<r.y1+c.r, inX=c.x>r.x0-c.r&&c.x<r.x1+c.r; if((nearX<c.r+3&&inY)||(nearY<c.r+3&&inX)) out.push(['número×borda',c.x+','+c.y,JSON.stringify(r)]);}
 for(let a=0;a<C.length;a++)for(let b=a+1;b<C.length;b++){const A=C[a],B=C[b]; if((A.x-B.x)**2+(A.y-B.y)**2<(A.r+B.r)**2) out.push(['número×número',A.x+','+A.y,B.x+','+B.y]);}
 return {svgW:+svg.getAttribute('width'), out, longest: tx.map(t=>[t.s,Math.round(t.x0),Math.round(t.x1)]).filter(q=>q[2]>+svg.getAttribute('width')-4||q[1]<4)};
}'''
with sync_playwright() as p:
    b=p.chromium.launch()
    for f in sys.argv[1:]:
        pg=b.new_page(); pg.set_content('<html><body style="margin:0">'+open(f).read()+'</body></html>'); pg.wait_for_timeout(300)
        r=pg.evaluate(JS)
        print('==',f,len(r['out']),'problemas'); [print('  ',*x) for x in r['out']]; 
        if r['longest']: print('  fora da área:',r['longest'])
    b.close()
