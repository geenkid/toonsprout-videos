#!/usr/bin/env python3
# render.py SRC SRT START END TITLE PARTLABEL HOOK CREDIT OUT
import sys, subprocess, re, os, tempfile
src,srt,start,end,title,part,hook,credit,out=sys.argv[1:10]
start,end=float(start),float(end)
def ts(x):
    h,m,r=x.split(':'); s,ms=r.split(','); return int(h)*3600+int(m)*60+int(s)+int(ms)/1000
def ass(t):
    h=int(t//3600); m=int(t%3600//60); s=t%60; return f"{h}:{m:02d}:{s:05.2f}"
ev=[]
for b in open(srt).read().replace('\r','').strip().split('\n\n'):
    L=b.split('\n'); a,c=[ts(x) for x in L[1].split(' --> ')]
    if c<=start or a>=end: continue
    a=max(a,start)-start; c=min(c,end)-start
    ev.append(f"Dialogue: 0,{ass(a)},{ass(c)},Main,,0,0,0,,"+'\\N'.join(L[2:]))
d=tempfile.mkdtemp()
open(f'{d}/s.ass','w').write("""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main,Inter,66,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,5,0,2,70,70,520,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""+'\n'.join(ev)+'\n')
open(f'{d}/hook.txt','w').write(hook.replace('|','\n'))
open(f'{d}/title.txt','w').write(title)
open(f'{d}/part.txt','w').write(part)
open(f'{d}/credit.txt','w').write(credit)
F='/usr/share/fonts/opentype/inter/Inter-Bold.otf'
fc=(f"[0:v]split[a][b];[a]scale=-2:1920,crop=1080:1920,boxblur=30:3,eq=brightness=-0.15[bg];"
 f"[b]scale=1500:-2,crop=1080:ih[fg];[bg][fg]overlay=0:(H-h)/2-80,ass={d}/s.ass,"
 f"drawtext=fontfile={F}:textfile={d}/title.txt:fontsize=96:fontcolor=white:x=(w-tw)/2:y=230,"
 f"drawtext=fontfile={F}:textfile={d}/part.txt:fontsize=56:fontcolor=0xFFD54A:x=(w-tw)/2:y=350,"
 f"drawtext=fontfile={F}:textfile={d}/hook.txt:fontsize=72:fontcolor=white:box=1:boxcolor=black@0.55:boxborderw=24:line_spacing=12:x=(w-tw)/2:y=1330:enable='lt(t,3.5)',"
 f"drawtext=fontfile={F}:textfile={d}/credit.txt:fontsize=26:fontcolor=white@0.7:x=(w-tw)/2:y=h-90,format=yuv420p[v]")
subprocess.run(['ffmpeg','-v','error','-y','-ss',str(start),'-t',str(end-start),'-i',src,'-filter_complex',fc,
 '-map','[v]','-map','0:a','-dn','-map_chapters','-1','-c:v','libx264','-preset','medium','-crf','20','-maxrate','3500k','-bufsize','7000k','-profile:v','high','-r','24',
 '-c:a','aac','-b:a','160k','-ac','2','-af','loudnorm=I=-14:TP=-1.5','-movflags','+faststart',out],check=True)
print(out,'ok')
