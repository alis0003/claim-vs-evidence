"""Compose the approved original illustration and verified claim text; no network."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import hashlib
ROOT=Path(__file__).resolve().parents[2]
source=ROOT/'cards/iphone-recovery-original-ai.png'
assert hashlib.sha256(source.read_bytes()).hexdigest()=='7006774ba54bbb87adb2dfa4a23fc44fb6321d114132825b23ff0344ee3b2d9e'
S=2
im=Image.new('RGB',(1080*S,1350*S),'#F6F5F0');d=ImageDraw.Draw(im)
navy='#132D3B';teal='#126B6C';muted='#4B5E68'
fontdir='/usr/share/fonts/truetype/dejavu/'
def text(x,y,value,size=28,bold=False,color=navy):
 f=ImageFont.truetype(fontdir+('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'),size*S)
 box=d.textbbox((x*S,y*S),value,font=f,anchor='lt')
 assert box[2]<=1036*S and box[3]<=1340*S,(value,box)
 d.text((x*S,y*S),value,font=f,fill=color,anchor='lt')
def rect(box,color):d.rectangle(tuple(n*S for n in box),fill=color)
rect((0,0,1080,12),navy)
text(48,42,'CLAIM / EVIDENCE',22,True)
text(850,44,'FALSE',23,True,'#AB352B')
text(48,98,'Real sinking. AI iPhone video.',49,True)
text(48,178,'Claim: this clip shows people recovering',29)
text(48,220,'floating iPhone boxes in the Strait of Hormuz.',29)
rect((48,278,1032,340),navy)
text(72,296,'AI illustration — not actual footage',30,True,'#FFFFFF')
pic=Image.open(source).convert('RGB').resize((984*S,656*S),Image.Resampling.LANCZOS)
im.paste(pic,(48*S,340*S))
text(48,1020,'WHAT THE REPORT FOUND',21,True,teal)
text(48,1060,'Full Fact reports a SynthID watermark',27)
text(48,1100,'and continuity errors in this specific clip.',27)
text(48,1156,'GFS PRIDE really sank, Singapore’s MPA confirms.',25,color=muted)
rect((48,1214,1032,1216),'#CED8DA')
text(48,1240,'Sources: Full Fact (27 Oct); MPA (14 Oct 2026)',22,True)
text(48,1282,'This check does not establish the ship’s cargo.',22,color=muted)
im.resize((1080,1350),Image.Resampling.LANCZOS).save(ROOT/'drafts/iphone-recovery/card-final.png')
