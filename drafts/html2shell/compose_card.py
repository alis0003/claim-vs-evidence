"""AI-assisted local compositor. Draft only; never publishes or calls a network API.
Requires Pillow and DejaVu Sans fonts. Third-party screenshot rights are separate.
Run from any directory: python compose_card.py. See provenance.json.
"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import hashlib, json
ROOT=Path(__file__).resolve().parent
OUT=ROOT
SRC=ROOT/'html2shell-claim-context.jpg'
assert hashlib.sha256(SRC.read_bytes()).hexdigest()=='b32935ba44bda9de2cdcb33d506f093c6030408baf0b2ae0ef09b8ea76441511'
S=2
im=Image.new('RGB',(1080*S,1350*S),'#F4F3EF'); d=ImageDraw.Draw(im)
navy='#132C3A'; muted='#54636B'; red='#AC342A'; teal='#176B62'; line='#D5DCD9'
reg='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'; bold='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
checks=[]
def font(sz,b=False):return ImageFont.truetype(bold if b else reg, round(sz*S))
def rect(box,fill,outline=None,width=1):d.rectangle(tuple(round(n*S) for n in box),fill,outline,round(width*S))
def text(x,y,s,sz=24,color=navy,b=False):
 f=font(sz,b); box=d.textbbox((x*S,y*S),s,font=f,anchor='lt'); assert box[0]>=0 and box[2]<=1080*S and box[3]<=1350*S,(s,box)
 d.text((x*S,y*S),s,font=f,fill=color,anchor='lt'); checks.append({'text':s,'box':[round(v/S,2) for v in box]})
def para(x,y,s,width,sz=26,leading=36,color=navy,b=False):
 words=s.split(); rows=[]; row=''; f=font(sz,b)
 for w in words:
  cand=(row+' '+w).strip()
  if d.textlength(cand,font=f)>width*S and row: rows.append(row); row=w
  else: row=cand
 if row:rows.append(row)
 for n,r in enumerate(rows):text(x,y+n*leading,r,sz,color,b)
 return y+len(rows)*leading
# Editorial header.
rect((0,0,1080,12),navy)
text(48,44,'CLAIM / EVIDENCE',22,navy,True)
text(740,49,'DRAFT · NOT PUBLISHED',17,muted,True)
text(45,105,'Real CVE. False claim.',61,navy,True)
text(48,189,'CVE-2026-42069 is not an HTML remote-code-execution flaw.',25,muted)
rect((48,233,1032,235),line)
# The claim is documented with genuine pixels: crop removes only sidebar and excess lower article text.
text(48,257,'CIRCULATED GRAPHIC · NOT AN OFFICIAL ADVISORY',16,muted,True)
crop=(32,0,760,696)
pic=Image.open(SRC).convert('RGB').crop(crop)
box=(48,292,678,894)
# White backing and hairline border are outside the screenshot, not overlays.
rect((46,290,680,896),'#FFFFFF',line,1)
pic=pic.resize((630*S,602*S),Image.Resampling.LANCZOS)
im.paste(pic,(48*S,292*S))
# Claim/verdict rail.
text(714,297,'THE CLAIM',19,red,True)
end=para(714,338,'A satirical graphic calls CVE-2026-42069 “HTML2Shell” and claims critical remote code execution in HTML.',318,27,36)
assert end<=630,end
rect((714,636,1032,638),line)
text(714,670,'VERDICT',19,red,True)
text(708,711,'FALSE',63,red,True)
para(714,792,'Satirical graphic. Misused CVE number.',318,25,34,navy,True)
text(48,914,'Source: Lead Stories article, 25 Oct 2026; graphic credited to @polydaic on X.',19,muted)
# Evidence summary, based on the official advisory.
rect((48,955,54,1149),teal)
text(74,955,'WHAT THE PRIMARY EVIDENCE SAYS',19,teal,True)
text(74,992,'The real issue is in Kirby CMS.',34,navy,True)
end=para(74,1042,'Missing read-access controls for authenticated Panel users can expose site, user and role information.',950,26,35)
assert end<=1115,end
text(74,1123,'Patched in Kirby 4.9.0 and 5.4.0.',23,navy,True)
# Compact source bar. All full URLs and access limitations also accompany the draft.
rect((0,1182,1080,1350),navy)
text(48,1205,'PRIMARY SOURCES',15,'#B9D9D5',True)
text(48,1235,'github.com/getkirby/kirby/security/advisories/GHSA-2h7v-4372-f6x2',19,'#FFFFFF')
text(48,1265,'getkirby.com/security',19,'#FFFFFF')
text(48,1306,'This verdict does not rule out real browser or web-app vulnerabilities.',20,'#DCE7E7')
# No re-creation, retouching, recoloring, or alteration of screenshot content.
im=im.resize((1080,1350),Image.Resampling.LANCZOS)
path=OUT/'html2shell-claim-vs-evidence-DRAFT.png';im.save(path,optimize=True)
print('Draft PNG SHA-256:', hashlib.sha256(path.read_bytes()).hexdigest())
