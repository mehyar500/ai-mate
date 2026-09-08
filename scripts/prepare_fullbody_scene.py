"""Prepare a full-body fictional companion reference for avatar experiments."""
import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main():
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    import torch
    from diffusers import Flux2KleinPipeline
    start = time.perf_counter()
    pipe = Flux2KleinPipeline.from_pretrained(str(ROOT / ".cache/local-poc/klein"), torch_dtype=torch.bfloat16, local_files_only=True)
    pipe.enable_model_cpu_offload()
    prompt = ("Realistic full-body photograph of a fictional adult woman standing naturally and looking at the camera, "
              "head to toe visible, relaxed friendly expression, shoulder-length dark brown hair, modest cream sweater, "
              "blue jeans and white sneakers, both arms and hands fully visible, in a bright leafy garden patio, "
              "natural daylight, realistic skin and clothing, no text, no watermark, no other people, portrait photography.")
    output = ROOT / "generated/local-app"
    output.mkdir(parents=True, exist_ok=True)
    image = pipe(prompt=prompt, height=768, width=512, guidance_scale=1.0, num_inference_steps=4,
                  generator=torch.Generator(device="cuda").manual_seed(921)).images[0]
    image.save(output / "fullbody.png")
    (output / "fullbody.json").write_text(json.dumps({"model":"FLUX.2-klein-4B","prompt":prompt,"elapsed_s":time.perf_counter()-start}, indent=2), encoding="utf-8")
    print(json.dumps({"output":str(output / "fullbody.png"),"elapsed_s":time.perf_counter()-start}))

if __name__ == "__main__":
    main()
