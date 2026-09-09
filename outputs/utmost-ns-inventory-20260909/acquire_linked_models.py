"""Acquire public ephemeris records linked to the downloaded MONSPSR timing data."""
from pathlib import Path
import json, urllib.request, base64, hashlib
ROOT=Path('../Project Recherche Data/utmost-ns-inventory-20260909').resolve()
OUT=ROOT/'authenticated/linked-models';OUT.mkdir(exist_ok=True)
# Prefer the completed per-pulsar snapshots after the broad query timed out.
paths=sorted((ROOT/'authenticated').glob('target-*/page-*.json'))
if not paths:paths=sorted((ROOT/'authenticated/toas-one-channel').glob('page-*.json'))
rows=[e['node'] for p in paths for e in json.loads(p.read_text())['data']['toa']['edges']]
ids=sorted({r['ephemeris']['id'] for r in rows if r['ephemeris']})
remaining=[i for i in ids if not (OUT/(base64.b64decode(i).decode().split(':')[-1]+'.json')).exists()]
for start in range(0,len(remaining),10):
 chunk=remaining[start:start+10]
 query='{'+ ' '.join('m'+str(j)+':node(id:'+json.dumps(i)+'){... on EphemerisNode{id pulsar{name} project{short} ephemerisData ephemerisHash validFrom validTo comment}}' for j,i in enumerate(chunk))+'}'
 req=urllib.request.Request('https://pulsars.org.au/api/graphql/',data=json.dumps({'query':query}).encode(),headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=45) as response:result=json.load(response)
 if result.get('errors'):raise RuntimeError(result['errors'])
 for j,i in enumerate(chunk):
  node=result['data']['m'+str(j)]
  if node is None or node['id']!=i:raise ValueError('Linked model inaccessible or identity mismatch')
  out=OUT/(base64.b64decode(i).decode().split(':')[-1]+'.json')
  with out.open('x') as f:json.dump(node,f,indent=2);f.write('\n')
 print(json.dumps({'models_saved':start+len(chunk),'models_to_acquire':len(remaining)}),flush=True)
print(json.dumps({'complete_for_downloaded_pages':True,'model_ids':len(ids)}),flush=True)
