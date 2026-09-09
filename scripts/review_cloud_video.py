"""Download one completed synthetic trial for local decoding/quality inspection.

Never forwards Cloudflare headers. The media host is restricted to the HTTPS
Google Storage host actually returned by the LTX benchmark; redirects fail.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.check_cloud_gateway import NoRedirect


def main():
    from local_app.engine import configure_runtime
    configure_runtime()
    import cv2
    import numpy as np
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case',choices=['ltx-review'])
    args=parser.parse_args()
    folder=ROOT/'generated/local-app/audit/cloud-video'/args.case
    trial=json.loads((folder/'result.json').read_text())
    if trial.get('state')!='Completed':
        raise ValueError('Only a completed known synthetic trial can be reviewed.')
    url=urllib.parse.urlsplit(trial['video_url'])
    if url.scheme!='https' or url.hostname!='storage.googleapis.com' or url.port not in (None,443) or url.username or url.password:
        raise ValueError('Unreviewed media destination; inspect it before adding support.')
    video=folder/'output.mp4'
    downloaded=False
    started=time.perf_counter()
    if not video.exists():
        opener=urllib.request.build_opener(NoRedirect)
        with opener.open(trial['video_url'],timeout=45) as response:
            content_type=response.headers.get('Content-Type','').split(';')[0]
            if content_type not in ('video/mp4','application/octet-stream'):
                raise ValueError('Unexpected media type.')
            raw=response.read(25_000_001)
        if len(raw)>25_000_000:
            raise ValueError('Remote clip exceeded the 25MB review bound.')
        video.write_bytes(raw)
        downloaded=True
    download_s=round(time.perf_counter()-started,3) if downloaded else None
    flags=getattr(subprocess,'CREATE_NO_WINDOW',0)
    result=subprocess.run(['ffprobe','-v','error','-show_entries',
        'format=duration:stream=codec_type,codec_name,width,height,r_frame_rate',
        '-of','json',str(video)],check=True,capture_output=True,timeout=20,creationflags=flags)
    media=json.loads(result.stdout)
    sheet=np.full((2*474,3*252,3),24,np.uint8)
    capture=cv2.VideoCapture(str(video))
    try:
        for i,seconds in enumerate([0,.75,1.5,2.5,3.5,4.5]):
            capture.set(cv2.CAP_PROP_POS_MSEC,seconds*1000)
            ok,frame=capture.read()
            if not ok: raise ValueError('Missing review frame.')
            frame=cv2.resize(frame,(252,448),interpolation=cv2.INTER_AREA)
            row,col=divmod(i,3)
            sheet[row*474+26:(row+1)*474,col*252:(col+1)*252]=frame
            cv2.putText(sheet,f'{seconds:.2f}s',(col*252+8,row*474+19),cv2.FONT_HERSHEY_SIMPLEX,.5,(245,245,245),1)
    finally:
        capture.release()
    cv2.imwrite(str(folder/'contact.jpg'),sheet)
    decoded=subprocess.run(['ffmpeg','-v','error','-i',str(video),'-vn','-ac','1','-ar','16000','-f','f32le','pipe:1'],
                           check=True,capture_output=True,timeout=20,creationflags=flags)
    samples=np.frombuffer(decoded.stdout,dtype=np.float32)
    audio={'samples':len(samples),'rms':float(np.sqrt(np.mean(samples*samples))) if len(samples) else 0,
           'peak':float(np.max(np.abs(samples))) if len(samples) else 0}
    review={'case':args.case,'sha256':hashlib.sha256(video.read_bytes()).hexdigest(),
            'bytes':video.stat().st_size,'download_s':download_s,'media':media,'audio':audio,
            'limitations':'Contact-sheet review and decoded audio signal only; not physical speaker or lip-sync qualification.'}
    (folder/'review.json').write_text(json.dumps(review,indent=2)+'\n')
    print(json.dumps(review))


if __name__=='__main__':
    main()
