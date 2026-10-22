from html import escape as esc
INK='#14171f'; SUB='#5d6572'; LINE='#3a4150'; RED='#e5323d'
FILL={'app':('#eef4ff','#3d6fd6'),'supa':('#ecf8f1','#1f9d5b'),'ml':('#fff6e6','#c98a12'),
      'campo':('#f4f5f7','#8d94a2'),'ext':('#ffffff','#8d94a2'),'hw':('#fdeeee','#e5323d')}
class D:
    def __init__(s,w,h,title,sub):
        s.dy=0 if sub else -26; s.w,s.h=w,h+s.dy; s.out=[]; s.top=[]; s.head=[]
        s.head.append(f'<rect width="{w}" height="{s.h}" fill="#ffffff"/>')
        s.head.append(f'<rect width="{w}" height="6" fill="{RED}"/>')
        s.head.append(f'<text x="32" y="46" font-size="24" font-weight="700" fill="{INK}">{esc(title)}</text>')
        if sub: s.head.append(f'<text x="32" y="72" font-size="15" fill="{SUB}">{esc(sub)}</text>')
    def group(s,x,y,w,h,label,kind):
        f,c=FILL[kind]
        s.out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="{f}" stroke="{c}" stroke-width="1.5" stroke-dasharray="{"6 5" if kind=="campo" else "0"}"/>')
        s.out.append(f'<text x="{x+16}" y="{y+24}" font-size="13" font-weight="700" letter-spacing="0.8" fill="{c}">{esc(label.upper())}</text>')
    def box(s,x,y,w,h,title,sub=None,kind='ext',dashed=False):
        f,c=FILL[kind]
        s.out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="#ffffff" stroke="{c}" stroke-width="2" {"stroke-dasharray=\'6 4\'" if dashed else ""}/>')
        cy=y+h/2+(-8 if sub else 6)
        s.out.append(f'<text x="{x+w/2}" y="{cy}" text-anchor="middle" font-size="16" font-weight="700" fill="{INK}">{esc(title)}</text>')
        if sub:
            for i,l in enumerate(sub.split('\n')):
                s.out.append(f'<text x="{x+w/2}" y="{cy+20+i*17}" text-anchor="middle" font-size="13.5" fill="{SUB}">{esc(l)}</text>')
    def arrow(s,pts,num=None,label=None,lpos=None,dashed=False,color=LINE,anchor='start',npos=None):
        d='M'+' L'.join(f'{x},{y}' for x,y in pts)
        s.out.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2" {"stroke-dasharray=\'7 5\'" if dashed else ""} marker-end="url(#ah)"/>')
        if label:
            lx,ly=lpos
            lines=label.split('\n')
            for i,l in enumerate(lines):
                s.top.append(f'<text x="{lx}" y="{ly+i*17}" text-anchor="{anchor}" font-size="13.5" fill="{INK}" stroke="#ffffff" stroke-width="5" paint-order="stroke">{esc(l)}</text>')
        if False:
            nx,ny=npos if npos else ((pts[0][0]+pts[1][0])/2,(pts[0][1]+pts[1][1])/2)
            s.top.append(f'<circle cx="{nx}" cy="{ny}" r="12" fill="{INK}"/><text x="{nx}" y="{ny+4.5}" text-anchor="middle" font-size="13" font-weight="700" fill="#fff">{num}</text>')
    def text(s,x,y,t,size=13.5,color=SUB,anchor='start',weight=400):
        s.top.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{size}" font-weight="{weight}" fill="{color}">{esc(t)}</text>')
    def raw(s,t): s.out.append(t)
    def svg(s):
        defs=f'<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{LINE}"/></marker></defs>'
        return f'<svg xmlns="http://www.w3.org/2000/svg" width="{s.w}" height="{s.h}" viewBox="0 0 {s.w} {s.h}" font-family="Nunito, Helvetica, Arial, sans-serif">{defs}{"".join(s.head)}<g transform="translate(0,{s.dy})">{"".join(s.out)}{"".join(s.top)}</g></svg>'
