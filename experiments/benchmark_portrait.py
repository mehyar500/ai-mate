"""Measure the local portrait renderer and save a frame contact sheet for review."""
import argparse
import json
from pathlib import Path
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", default="mira")
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--runs", type=int, default=2)
    parser.add_argument("--upstream-research-fixture", action="store_true")
    args = parser.parse_args()
    from local_app.visual import PortraitRenderer
    from PIL import Image, ImageDraw
    import cv2
    output = ROOT/"generated/local-app"
    if args.upstream_research_fixture:
        # Upstream example media is for private non-commercial research only.
        # Never expose it as the product character or put it in a funding demo.
        fixture=Image.open(ROOT/".cache/local-poc/MuseTalk/assets/demo/man/man.png").convert("RGB")
        fixture.thumbnail((512,768))
        fixture.save(output/"fixture.png")
        args.scene="fixture"
    started = time.perf_counter()
    renderer = PortraitRenderer()
    renderer.prepare(args.scene)
    load = time.perf_counter()-started
    rows=[]
    audio=ROOT/"generated/local-speech/sample-3.wav"
    for i in range(args.runs):
        dest=output/f"portrait-b{args.batch}-{i}.mp4"
        row=renderer.render(audio,dest,threading.Event(),scene=args.scene,batch_size=args.batch)
        row["file"]=dest.name
        rows.append(row)
        print(json.dumps(row),flush=True)
    video=cv2.VideoCapture(str(dest)); count=int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    sheet=Image.new("RGB",(4*256,2*344),"#f7f4ee")
    draw=ImageDraw.Draw(sheet)
    for i in range(8):
        frame_index=round((count-1)*i/7)
        video.set(cv2.CAP_PROP_POS_FRAMES,frame_index)
        ok,frame=video.read()
        if not ok:raise RuntimeError("Could not decode generated video.")
        image=Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)); image.thumbnail((256,320))
        x,y=(i%4)*256,(i//4)*344
        sheet.paste(image,(x,y)); draw.text((x+8,y+324),f"Frame {frame_index}",fill="black")
    video.release()
    sheet.save(output/f"portrait-b{args.batch}-review.jpg")
    (output/f"portrait-b{args.batch}-metrics.json").write_text(json.dumps({"load_s":load,"scene":args.scene,"runs":rows},indent=2))


if __name__=="__main__":main()
