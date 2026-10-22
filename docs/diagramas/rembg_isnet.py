# Remove o fundo com o modelo ISNet (o mesmo do rembg), rodando no onnxruntime
import sys, numpy as np, onnxruntime as ort
from PIL import Image
src,dst=sys.argv[1],sys.argv[2]
im=Image.open(src).convert('RGB'); W,H=im.size
x=np.asarray(im.resize((1024,1024),Image.LANCZOS)).astype(np.float32)/255.0
x=(x-0.5)/1.0; x=x.transpose(2,0,1)[None]
sess=ort.InferenceSession('models/isnet.onnx',providers=['CPUExecutionProvider'])
out=sess.run(None,{sess.get_inputs()[0].name:x})[0][0,0]
m=(out-out.min())/(out.max()-out.min())
mask=Image.fromarray((m*255).astype(np.uint8)).resize((W,H),Image.LANCZOS)
rgba=im.copy(); rgba.putalpha(mask)
bb=mask.point(lambda v:255 if v>20 else 0).getbbox(); rgba=rgba.crop(bb)
rgba.save(dst); print(dst,rgba.size)
