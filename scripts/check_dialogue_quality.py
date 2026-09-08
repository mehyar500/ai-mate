"""Small local identity/memory regression set, preserving full neutral replies."""
import argparse
import json
from pathlib import Path
import sys
import threading
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model",default="qwen3.5:9b-q4_K_M")
    parser.add_argument("--presence-penalty", type=float)
    args=parser.parse_args()
    from local_app import models
    from local_app.core import messages_for
    models.LLM=args.model
    model=models.Models.__new__(models.Models)
    snapshot={"memory":"My name is Alex. My piano lesson is Friday. I like gardening and cooking. My dog is named Maple.","turns":[]}
    prompts=["What is my dog's name?","What name should you call me?","What is your name?","Have you ever seen my dog?","What are my hobbies?","When is my piano lesson?","What is my sister's name?","Let's have a quiet conversation.","What name should you call me?","Have you visited my garden?","What is your name and what is mine?","What should I name a new houseplant?"]
    prompts += ["Suggest one inexpensive thing I could try in my garden.", "Have I told you I saved any seeds?", "Did I tell you I bought that houseplant?"]
    prompts += ["I planted tomatoes today. Ask me one short question about them.", "My lesson moved from Friday to Tuesday. What day is it now?", "What day is my piano lesson now?"]
    prompts += ["What do you call me?", "Do you remember my name?", "Who am I?", "What should I call you?"]
    rows=[]
    for prompt in prompts:
        start=time.perf_counter()
        options = {"presence_penalty":args.presence_penalty} if args.presence_penalty is not None else None
        text=" ".join(model.stream_reply(messages_for(snapshot,prompt),threading.Event(), options=options))
        row={"prompt":prompt,"reply":text,"seconds":time.perf_counter()-start}
        rows.append(row);print(json.dumps(row),flush=True)
        snapshot["turns"].append({"user":prompt,"assistant":text})
    suffix = f"-presence-{args.presence_penalty:g}" if args.presence_penalty is not None else ""
    path=ROOT/"generated/local-app"/("dialogue-"+args.model.replace(":","-")+suffix+".json")
    path.write_text(json.dumps({"model":args.model,"options_override":options,"scope":"Small synthetic role/memory regression; review replies, not only timing", "rows":rows},indent=2))


if __name__=="__main__":main()
