"""Read-only portal intake. Token exists only in process memory; responses are external."""
import sys, json, pathlib, urllib.request, hashlib, time
ROOT=pathlib.Path('../Project Recherche Data/utmost-ns-inventory-20260909/authenticated').resolve()
ROOT.mkdir(exist_ok=True)
# Use a hidden terminal prompt for later operator-authorized intakes.
import getpass
token=getpass.getpass('Temporary Pulsar Portal API token: ').strip()
if not token or any(c.isspace() for c in token):raise SystemExit('Invalid token format')
print('Credential loaded into process memory; awaiting read-only query commands.',flush=True)
def request(query, variables):
    for attempt in range(3):
        try:
            req=urllib.request.Request('https://pulsars.org.au/api/graphql/',data=json.dumps({'query':query,'variables':variables}).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+token})
            with urllib.request.urlopen(req,timeout=90) as response: data=response.read()
            result=json.loads(data)
            if result.get('errors'): raise RuntimeError(json.dumps(result['errors']))
            return data,result
        except (TimeoutError,urllib.error.URLError) as exc:
            if attempt==2: raise
            time.sleep(2*(attempt+1))
def save(path,data):
    if path.exists(): raise RuntimeError('Refusing to overwrite '+str(path))
    path.write_bytes(data)
    return {'file':str(path.relative_to(ROOT)),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
for line in sys.stdin:
    try:
        cmd=json.loads(line)
        if cmd.get('op')=='exit':break
        if 'mutation' in cmd['query'].lower():raise ValueError('Only read-only queries allowed')
        name=cmd['name']; dest=ROOT/name
        if '/' in name or '..' in name:raise ValueError('Invalid output name')
        if cmd.get('op')=='pages':
            dest.mkdir(exist_ok=False);variables=dict(cmd.get('variables',{}));n=0;receipts=[];cursors=set()
            while True:
                data,result=request(cmd['query'],variables)
                entry=save(dest/f'page-{len(receipts):05d}.json',data);receipts.append(entry)
                connection=result['data'][cmd['connection']];n+=len(connection['edges']);info=connection['pageInfo']
                if len(receipts)%10==0:print(json.dumps({'name':name,'pages':len(receipts),'rows':n}),flush=True)
                if not info['hasNextPage']:break
                cursor=info['endCursor']
                if not cursor or cursor in cursors:raise RuntimeError('Nonadvancing pagination')
                cursors.add(cursor);variables['after']=cursor
            save(dest/'receipt.json',json.dumps({'query':cmd['query'],'initial_variables':cmd.get('variables',{}),'rows':n,'pages':receipts},indent=2).encode())
            print(json.dumps({'name':name,'complete':True,'pages':len(receipts),'rows':n}),flush=True)
        else:
            data,result=request(cmd['query'],cmd.get('variables',{}));receipt=save(dest.with_suffix('.json'),data)
            print(json.dumps({'name':name,'complete':True,**receipt}),flush=True)
    except Exception as exc:
        print(json.dumps({'error_type':type(exc).__name__,'error':str(exc).replace(token,'[REDACTED]')}),flush=True)
token=None
print('Intake process closed; credential discarded.',flush=True)
