from PIL import Image, ImageDraw
B=14; RAD=44
items={'fat':('fin_fat_x',(0,0,860,1068)),'gasto':('fin_gasto_x',(0,0,860,1447)),'eco':('g_sim',(0,295,860,1400)),'painel':('g_painel',(0,236,860,1528)),'parc':('p_parc',(0,215,860,1320)),'ia':('g_previsao',(0,440,860,1420)),'llm':('g_sindico',(0,212,860,1070)),
       'tarifa':('g_tarifa',(0,232,860,1022)),'ls':('g_previsao3',(0,630,860,1650)),'dash':('g_fin',(0,105,860,1405)),'sus':('g_impacto',(0,305,860,1300)),'funil':('m_casa',(0,236,860,1560)),'smart':('m_smarthome',(0,90,860,1470)),'modo':('m_modo_tempo',(0,90,860,1350)),'consumo':('p_consumo_x',(0,0,860,1150)),'ev':('p_ev_x',(0,0,860,860)),'dist':('fin_dist_x',(0,0,860,1020))}
for k,(f,box) in items.items():
    im=Image.open('shots/'+f+'.png').convert('RGB').crop(box)
    W,H=im.size[0]+2*B,im.size[1]+2*B
    out=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(out)
    d.rounded_rectangle([0,0,W-1,H-1],RAD,fill=(156,254,51,255))
    m=Image.new('L',im.size,0); ImageDraw.Draw(m).rounded_rectangle([0,0,im.size[0]-1,im.size[1]-1],RAD-B,fill=255)
    out.paste(im,(B,B),m); out.save('s169/rect_'+k+'.png'); print(k,out.size)
ims=[Image.open('s169/rect_'+k+'.png') for k in items]
c=Image.new('RGB',(sum(i.width//3 for i in ims)+70,560),'white'); x=0
for i in ims:
    t=i.resize((i.width//3,i.height//3)); c.paste(t,(x,0),t); x+=t.width+10
c.save('rects.png')
