"""Create one non-explicit fictional portrait locally; unload scene model on exit."""
import argparse
import json
import os
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", choices=["mira", "garden", "cafe"], default="mira")
    args = parser.parse_args()
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    import torch
    from diffusers import Flux2KleinPipeline
    start = time.perf_counter()
    pipe = Flux2KleinPipeline.from_pretrained(str(ROOT / ".cache/local-poc/klein"), torch_dtype=torch.bfloat16, local_files_only=True)
    pipe.enable_model_cpu_offload()
    locations = {"mira": "a cozy bright living room with plants", "garden": "a leafy garden patio", "cafe": "a quiet sunlit cafe"}
    prompt = ("Natural candid webcam photograph of a fictional 30-year-old woman, friendly relaxed expression, "
              "closed lips, brown eyes, shoulder-length dark brown hair tucked away from both cheeks, "
              "wearing a modest cream crew-neck sweater, sitting in " + locations[args.scene] + ". "
              "Frontal head and shoulders, entire head visible, eyes looking directly at camera, symmetrical frontal face, "
              "soft daylight, realistic skin texture, no writing, no watermark, no other people, portrait photography.")
    output = ROOT / "generated/local-app"
    output.mkdir(parents=True, exist_ok=True)
    kwargs = dict(prompt=prompt, height=640, width=512, guidance_scale=1.0, num_inference_steps=4,
                  generator=torch.Generator(device="cuda").manual_seed(217))
    if args.scene != "mira":
        from PIL import Image
        kwargs["image"] = Image.open(output / "mira.png").convert("RGB")
        kwargs["prompt"] += " Preserve the exact identity of the person in the reference image."
    if args.scene == "cafe":
        kwargs["prompt"] = (
            "Edit the provided photograph: replace the entire living-room background with a coffee shop. "
            "Behind the woman show a cafe counter, an espresso machine, warm wooden tables and pendant lights. "
            "Remove the couch and living-room plants. Keep the exact same adult woman's face, hair, cream "
            "sweater, frontal pose and framing. Natural realistic photography, no writing, no other people."
        )
    result = pipe(**kwargs).images[0]
    result.save(output / (args.scene + ".png"))
    record = {"model": "FLUX.2-klein-4B", "seed": 217, "prompt": kwargs["prompt"],
              "elapsed_with_load_s": time.perf_counter()-start, "scene": args.scene, "synthetic": True}
    (output / (args.scene + ".json")).write_text(json.dumps(record, indent=2))
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
