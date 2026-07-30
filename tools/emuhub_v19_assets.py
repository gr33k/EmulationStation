#!/usr/bin/env python3
from __future__ import annotations
import concurrent.futures as cf
import json, re, shutil, subprocess
from pathlib import Path
import requests

ROOT=Path.cwd(); OUT=ROOT/'v19_source_assets'; THEME=ROOT/'_nbba'; EJS=ROOT/'_ejs'; META=EJS/'metadata'
UA={'User-Agent':'EmuHub-V19-Final/2.0 authentic-media-collector'}
MAP={
 '3do':'3do','amiga':'amiga','atari2600':'atari2600','atari5200':'atari5200','atari7800':'atari7800','jaguar':'atarijaguar','lynx':'atarilynx','c64':'c64','segaGG':'gamegear','gb':'gb','gbc':'gbc','intv':'intellivision','segaMS':'mastersystem','segaMD':'megadrive','n64':'n64','nes':'nes','ngp':'ngp','pce':'pcengine','psx':'psx','segaSaturn':'saturn','sega32x':'sega32x','segaCD':'segacd','segaSG':'sg-1000','snes':'snes','odyssey2':'videopac','vb':'virtualboy','zxspectrum':'zxspectrum','arcade':'mame'}
ERAS={'atari2600':'1970s','intv':'1970s','odyssey2':'1970s','atari5200':'1980s','atari7800':'1980s','c64':'1980s','segaMS':'1980s','segaMD':'1980s','pce':'1980s','gb':'1980s','lynx':'1980s','amiga':'1980s','zxspectrum':'1980s','nes':'1980s','segaSG':'1980s','3do':'1990s','jaguar':'1990s','segaGG':'1990s','gbc':'1990s','n64':'1990s','ngp':'1990s','psx':'1990s','segaSaturn':'1990s','sega32x':'1990s','segaCD':'1990s','snes':'1990s','vb':'1990s','arcade':'arcade'}
VIDEOS=[('atari2600',['Pitfall','River Raid']),('intv',['Astrosmash','BurgerTime']),('arcade',['Pac-Man','Donkey Kong','Galaga']),('nes',['Super Mario Bros','Mega Man 2']),('segaMS',['Alex Kidd','R-Type']),('c64',['Last Ninja','Turrican']),('amiga',['Shadow of the Beast','Turrican']),('pce',['Bonk','R-Type']),('segaMD',['Sonic the Hedgehog 2','Streets of Rage 2']),('gb',['Super Mario Land','Tetris']),('arcade',['Street Fighter II','Mortal Kombat','Out Run']),('snes',['Super Metroid','Mega Man X']),('segaSaturn',['NiGHTS','Virtua Fighter 2']),('psx',['Crash Bandicoot','Tekken 3']),('n64',['Super Mario 64','Ocarina of Time']),('doom',[]),('quake',[]),('quake2',[]),('scummvm',['Monkey Island','Day of the Tentacle'])]
ALIASES={'segaSaturn':['saturn'],'segaMD':['genesis','megadrive'],'segaMS':['mastersystem'],'arcade':['mame']}
def safe(s):return re.sub(r'[^A-Za-z0-9._-]+','_',s).strip('_')
def dl(url,dest,minimum=20000,timeout=65):
 try:
  dest.parent.mkdir(parents=True,exist_ok=True)
  with requests.get(url,headers=UA,timeout=timeout,stream=True,allow_redirects=True) as r:
   r.raise_for_status(); tmp=dest.with_suffix(dest.suffix+'.part')
   with tmp.open('wb') as f:
    for c in r.iter_content(262144):
     if c:f.write(c)
   if tmp.stat().st_size<minimum:tmp.unlink(missing_ok=True);return False
   tmp.replace(dest);return True
 except Exception:return False
def mp(system):
 for stem in [system,*ALIASES.get(system,[])]:
  p=META/f'{stem}.json'
  if p.exists():return p
 return None
def video_one(arg):
 i,(system,words)=arg;p=mp(system)
 if not p:return {'system':system,'status':'missing'}
 try:d=json.loads(p.read_text())
 except:return {'system':system,'status':'missing'}
 entries=[x for x in d.values() if isinstance(x,dict) and x.get('name') and x.get('vid')]
 chosen=None
 for w in words:
  chosen=next((x for x in entries if re.search(re.escape(w),x['name'],re.I)),None)
  if chosen:break
 if not chosen and entries:chosen=entries[i%len(entries)]
 if not chosen:return {'system':system,'status':'missing'}
 cid=chosen['vid'];name=chosen['name'];dest=OUT/'gameplay'/f'{i:02d}_{safe(system)}_{safe(name)[:60]}.mp4'
 for base in ['https://ipfs.infura.io/ipfs/','https://gateway.ipfs.io/ipfs/','https://nftstorage.link/ipfs/','https://dweb.link/ipfs/']:
  url=base+cid
  if dl(url,dest,25000,70):return {'system':system,'game':name,'cid':cid,'file':str(dest.relative_to(OUT)),'status':'ok','gateway':url,'metadata_file':p.name}
 return {'system':system,'game':name,'cid':cid,'status':'download-failed','metadata_file':p.name}
def main():
 for p in [OUT,THEME,EJS]:
  if p.exists():shutil.rmtree(p)
 OUT.mkdir()
 subprocess.run(['git','clone','--depth','1','https://github.com/RetroPie/es-theme-nbba.git',str(THEME)],check=True)
 subprocess.run(['git','clone','--depth','1','https://github.com/linuxserver/emulatorjs.git',str(EJS)],check=True)
 hardware=[];arcade=[]
 for key,folder in MAP.items():
  src=THEME/folder/'gc.png'
  if not src.exists():continue
  era=ERAS[key];dest=OUT/'hardware'/era/f'{key}.png';dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
  kind='cabinet' if key=='arcade' else ('computer' if key in {'amiga','c64','zxspectrum'} else ('handheld' if key in {'lynx','gb','gbc','segaGG','ngp'} else 'console'))
  rec={'era':era,'key':key,'kind':kind,'status':'ok','file':str(dest.relative_to(OUT)),'source_url':f'https://github.com/RetroPie/es-theme-nbba/tree/master/{folder}','author':'NBBA theme contributors','license':'Repository theme asset','commons_title':'NBBA gc.png'}
  (arcade if key=='arcade' else hardware).append(rec)
 with cf.ThreadPoolExecutor(max_workers=10) as ex:gameplay=list(ex.map(video_one,list(enumerate(VIDEOS))))
 summary={'hardware_ok':len(hardware),'hardware_total':len(hardware),'arcade_ok':len(arcade),'gameplay_ok':sum(r['status']=='ok' for r in gameplay),'gameplay_total':len(gameplay)}
 manifest={'hardware':hardware,'arcade':arcade,'gameplay':gameplay,'summary':summary}
 (OUT/'asset_manifest.json').write_text(json.dumps(manifest,indent=2));(OUT/'README.txt').write_text('Authentic system images from NBBA; gameplay from LinuxServer EmulatorJS IPFS metadata. Missing media omitted.\n')
 print(json.dumps(summary,indent=2))
 shutil.rmtree(THEME);shutil.rmtree(EJS)
if __name__=='__main__':main()
