"""Compose the approved original illustration and verified claim text; no network."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import hashlib
ROOT=Path(__file__).resolve().parents[2]
source=ROOT/'cards/polar-bear-original-ai-illustration.png'
assert hashlib.sha256(source.read_bytes()).hexdigest()=='880aeae0e60953a194f3a8a1acb4cb25f1b94d3418ba019d0f30a31f5ffef250'
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
text(48,98,'AI story, not a real rescue.',55,True)
text(48,178,'Claim: a real man raised and released',30)
text(48,220,'an injured polar-bear cub in a viral video.',30)
rect((48,278,1032,340),navy)
text(72,296,'AI illustration — not actual footage',30,True,'#FFFFFF')
pic=Image.open(source).convert('RGB').resize((984*S,656*S),Image.Resampling.LANCZOS)
im.paste(pic,(48*S,340*S))
text(48,1020,'WHAT THE REPORT FOUND',21,True,teal)
text(48,1060,'Lead Stories traced the clip to an AI-content creator',27)
text(48,1100,'and reported an AI disclosure on the original post.',27)
text(48,1156,'We did not independently inspect the original video.',25,color=muted)
rect((48,1214,1032,1216),'#CED8DA')
text(48,1240,'Source: Lead Stories · 23 October 2026',24,True)
text(48,1282,'Generic illustration, not event evidence. Checked 28 Oct 2026.',22,color=muted)
im.resize((1080,1350),Image.Resampling.LANCZOS).save(ROOT/'drafts/polar-bear/card-final.png')
