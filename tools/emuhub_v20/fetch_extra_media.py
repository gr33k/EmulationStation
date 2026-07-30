#!/usr/bin/env python3
from __future__ import annotations
import json, re, time
from pathlib import Path
import requests

OUT=Path('v20_extra_media'); OUT.mkdir(exist_ok=True)
S=requests.Session(); S.headers['User-Agent']='EmuHub-V20-Media-Collector/1.0'

SYSTEMS={
 'dreamcast':{
   'hardware':['https://upload.wikimedia.org/wikipedia/commons/thumb/0/07/Dreamcast-Console-Set.png/1280px-Dreamcast-Console-Set.png'],
   'games':['Crazy Taxi','Sonic Adventure','Soulcalibur']},
 'gamecube':{
   'hardware':['https://upload.wikimedia.org/wikipedia/commons/thumb/2/2b/GameCube-Console-Set.png/1280px-GameCube-Console-Set.png'],
   'metadata':['gamecube','gc'],
   'games':['Metroid Prime','Super Mario Sunshine','Mario Kart - Double Dash','Super Smash Bros. Melee']},
 'psp':{
   'hardware':['https://upload.wikimedia.org/wikipedia/commons/thumb/5/5d/Sony-PSP-1000-Body.png/1280px-Sony-PSP-1000-Body.png'],
   'games':['God of War - Chains of Olympus','Ridge Racer','Lumines']},
 'wii':{
   'hardware':['https://upload.wikimedia.org/wikipedia/commons/thumb/f/f3/Wii-Console.png/1280px-Wii-Console.png'],
   'games':['Super Mario Galaxy','Mario Kart Wii','New Super Mario Bros. Wii']},
}
GATEWAYS=['https://ipfs.infura.io/ipfs/','https://nftstorage.link/ipfs/','https://gateway.ipfs.io/ipfs/']

def download(url: str, dest: Path, min_bytes=10000) -> bool:
    for attempt in range(3):
        try:
            r=S.get(url,timeout=60,stream=True,allow_redirects=True); r.raise_for_status()
            tmp=dest.with_suffix(dest.suffix+'.part')
            with tmp.open('wb') as f:
                for chunk in r.iter_content(256*1024):
                    if chunk: f.write(chunk)
            if tmp.stat().st_size < min_bytes: raise RuntimeError('short file')
            tmp.replace(dest); return True
        except Exception as e:
            print('retry',url,e); time.sleep(2+attempt*2)
    return False

def safe(s): return re.sub(r'[^A-Za-z0-9._-]+','_',s).strip('_')

def load_metadata(keys):
    for key in keys:
        url=f'https://raw.githubusercontent.com/gr33k/emulatorjs/master/metadata/{key}.json'
        try:
            r=S.get(url,timeout=60); r.raise_for_status(); return key,r.json()
        except Exception as e: print('metadata miss',key,e)
    return None,{}

manifest=[]
for system,cfg in SYSTEMS.items():
    hw=OUT/f'{system}.png'
    ok=any(download(url,hw) for url in cfg['hardware'])
    manifest.append({'system':system,'kind':'hardware','status':'ok' if ok else 'missing','file':hw.name if ok else None,'source':cfg['hardware'][0]})
    metadata_keys=cfg.get('metadata',[system])
    meta_key,data=load_metadata(metadata_keys)
    choice=None
    for wanted in cfg['games']:
        for sha,rec in data.items():
            name=str(rec.get('name',''))
            if wanted.lower() in name.lower() and rec.get('vid'):
                choice=(name,rec['vid']); break
        if choice: break
    if not choice:
        for sha,rec in data.items():
            if rec.get('vid'):
                choice=(str(rec.get('name','gameplay')),rec['vid']); break
    if choice:
        name,cid=choice; dest=OUT/f'{system}_{safe(name)}.mp4'
        vid_ok=any(download(g+cid,dest,50000) for g in GATEWAYS)
        manifest.append({'system':system,'kind':'gameplay','status':'ok' if vid_ok else 'missing','file':dest.name if vid_ok else None,'game':name,'cid':cid,'metadata':meta_key})
    else:
        manifest.append({'system':system,'kind':'gameplay','status':'missing','file':None,'metadata':meta_key})

(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps(manifest,indent=2))
