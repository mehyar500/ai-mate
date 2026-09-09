"""Bounded synthetic comparison of fresh versus persistent Cloudflare HTTPS."""
import http.client
import io
import json
from pathlib import Path
import statistics
import sys
import threading
import time
from unittest.mock import patch
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from local_app.engine import configure_runtime
from local_app.conversation import Conversation
from scripts.benchmark_cloud_comparison import CASES, SNAPSHOT


def main():
    target=ROOT/'generated/local-app/audit/dialogue-connection.json'
    if target.exists():raise ValueError('Existing benchmark evidence is preserved.')
    configure_runtime();auth=Conversation('unused')
    if auth.provider!='cloudflare':raise ValueError('Cloudflare configuration is required.')
    auth.model='@cf/qwen/qwen3-30b-a3b-fp8'
    original=urllib.request.urlopen
    connection=http.client.HTTPSConnection('api.cloudflare.com',timeout=30)
    rows=[]
    try:
        for repeat in range(2):
            for case,prompt in CASES.items():
                for kind in (['fresh','persistent'] if repeat==0 else ['persistent','fresh']):
                    row={'repeat':repeat,'case':case,'kind':kind}
                    def request(req,**kwargs):
                        expected=f'https://api.cloudflare.com/client/v4/accounts/{auth.account}/ai/v1/chat/completions'
                        if req.full_url!=expected or not req.data or len(req.data)>30000:
                            raise ValueError('Unexpected request.')
                        body=json.loads(req.data)
                        if body['max_tokens']>512 or body['model']!=auth.model:raise ValueError('Request exceeds bound.')
                        started=time.perf_counter()
                        if kind=='persistent':
                            row['reused_socket']=connection.sock is not None
                            connection.request('POST',req.selector,body=req.data,headers=dict(req.header_items()))
                            response=connection.getresponse()
                            row['peer_closes_connection']=response.will_close
                            if response.status!=200:raise ValueError('Provider did not accept the benchmark request.')
                        else:
                            response=original(req,timeout=30)
                        with response:
                            first=response.read(1);row['first_byte_s']=time.perf_counter()-started
                            data=first+response.read(1_000_001)
                        row['complete_s']=time.perf_counter()-started
                        if len(data)>1_000_000:raise ValueError('Oversized response.')
                        usage=json.loads(data).get('usage',{})
                        row['usage']={k:usage[k] for k in ['prompt_tokens','completion_tokens'] if k in usage}
                        return io.BytesIO(data)
                    try:
                        with patch('local_app.conversation.urllib.request.urlopen',side_effect=request):
                            plan=auth.plan(SNAPSHOT,prompt,'video','fullbody',['fullbody','garden','mira','cafe'],threading.Event())
                        checks={'action':plan['action']=='none','scene':plan['scene']=='fullbody','mode':plan['presentation']=='video'}
                        if case=='memory':checks['memory']='recital' in plan['reply'].lower()
                        if case=='call_message':checks['message']='good luck at your recital' in plan.get('message','').lower()
                        row['checks']=checks
                    except (OSError,RuntimeError,ValueError,http.client.HTTPException) as error:
                        row['error']=type(error).__name__
                        rows.append(row)
                        raise RuntimeError('Synthetic connection comparison failed; see sanitized evidence.') from None
                    rows.append(row)
    finally:
        connection.close()
        result={'model':auth.model,'scope':'16 sequential synthetic plans; same account/model, alternating methods. No active transport switch, private history or retry.','rows':rows}
        target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    for kind in ['fresh','persistent']:
        selected=[r for r in rows if r['kind']==kind]
        print(json.dumps({'kind':kind,'samples':len(selected),'median_s':statistics.median(r['complete_s'] for r in selected),'max_s':max(r['complete_s'] for r in selected),'failed':sum(not all(r['checks'].values()) for r in selected)}))


if __name__=='__main__':main()
