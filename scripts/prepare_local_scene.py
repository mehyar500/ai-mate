"""Create one non-explicit fictional portrait locally; unload scene model on exit."""
import argparse
import json
import os
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", choices=["mira", "garden", "cafe", "fullbody"], default="mira")
    parser.add_argument("--candidate", action="store_true", help="Save separately for image review before changing an active scene.")
    parser.add_argument("--pose", choices=["neutral","closer","farther"], default="neutral")
    args = parser.parse_args()
    if args.pose != "neutral" and (args.scene != "fullbody" or not args.candidate):
        parser.error("Pose experiments require --scene fullbody --candidate.")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    import torch
    from diffusers import Flux2KleinPipeline
    start = time.perf_counter()
    pipe = Flux2KleinPipeline.from_pretrained(str(ROOT / ".cache/local-poc/klein"), torch_dtype=torch.bfloat16, local_files_only=True)
    pipe.enable_model_cpu_offload()
    locations = {"mira": "a cozy bright living room with plants", "garden": "a leafy garden patio", "cafe": "a quiet sunlit cafe", "fullbody":"a leafy garden patio"}
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
    if args.scene == "fullbody":
        kwargs.update(height=1152, width=768)
        kwargs["prompt"] = (
            "Create a full-length candid photograph of the EXACT same adult woman in the reference image. "
            "Preserve her specific face, dark eyebrows, brown eyes, nose, lips, skin tone and shoulder-length "
            "dark brown hair. Move the camera back to show her whole body, wearing the same cream knit sweater "
            "with blue jeans and white sneakers, standing on a quiet garden patio. Both arms hang naturally "
            "at her sides with all fingers visible. Her entire head and both shoes are inside the image. "
            "Leave generous empty space above her head, below her feet and beside both hands. "
            "Her body occupies only the middle seventy percent of the image height. A relaxed closed-mouth "
            "smile, natural skin pores, soft overcast daylight, ordinary smartphone photograph, subtle colors, "
            "real anatomy, no beauty retouching, no text, no other people."
        )
    if args.pose != "neutral":
        from PIL import Image
        kwargs["image"] = Image.open(output / "fullbody-candidate.png").convert("RGB")
        change = ("Make the woman MUCH LARGER in the photograph: a waist-up view. Her head is near the "
                  "top edge and her waist reaches the bottom edge. Only her head and torso fit in the "
                  "image; all legs and shoes are outside the image. She is standing very close to the camera. " if args.pose == "closer" else
                  "She has walked two meters farther from the stationary camera into the garden. Her "
                  "whole body is smaller, occupying the middle fifty percent of the image height. "
                  "Both shoes are visible on the more distant patio. ")
        kwargs["prompt"] = (
            "Edit this photograph, changing only the physical position of the same adult woman. " + change +
            "The camera is locked in exactly the same place with exactly the same lens and field of view. "
            "Preserve the garden, trees, paving stones and horizon at exactly their original image positions; "
            "do not zoom, crop or move the camera. The same woman faces the camera with her arms naturally "
            "at her sides, the exact same face, hair, cream sweater, jeans and white shoes. "
            "Natural overcast daylight, realistic anatomy and texture. No other people."
        )
    result = pipe(**kwargs).images[0]
    name = args.scene + ("-candidate" if args.candidate else "")
    if args.pose != "neutral":
        name += "-" + args.pose
    result.save(output / (name + ".png"))
    record = {"model": "FLUX.2-klein-4B", "seed": 217, "prompt": kwargs["prompt"],
              "elapsed_with_load_s": time.perf_counter()-start, "scene": args.scene, "synthetic": True,
              "pose":args.pose, "resolution":[kwargs["width"],kwargs["height"]]}
    (output / (name + ".json")).write_text(json.dumps(record, indent=2))
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
