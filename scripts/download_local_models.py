"""Download pinned public weights. No inference, credentials or purchases."""
import concurrent.futures
import argparse
import hashlib
import json
from pathlib import Path
import time
import urllib.request
from ranged_download import download

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache/local-poc"


def fetch(job):
    name, spec, filename = job
    destination = CACHE / name / filename
    destination.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://huggingface.co/{spec['repo']}/resolve/{spec['revision']}/{filename}"
    if not destination.exists():
        if filename.endswith((".safetensors", ".pth", ".bin")):
            download(url, destination, workers=8)
    if not destination.exists():
        temporary = destination.with_suffix(destination.suffix + ".partial")
        print(f"Downloading {name}/{filename}", flush=True)
        for attempt in range(3):
            try:
                with urllib.request.urlopen(url, timeout=120) as response, temporary.open("wb") as out:
                    while chunk := response.read(4 * 1024 * 1024):
                        out.write(chunk)
                temporary.replace(destination)
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(2)
    with destination.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    expected = spec.get("hashes", {}).get(filename)
    if expected and digest != expected:
        raise RuntimeError(f"SHA-256 mismatch for {name}/{filename}; do not load this file.")
    print(f"Ready {name}/{filename} ({destination.stat().st_size} bytes)", flush=True)
    return dict(model=name, file=filename, revision=spec["revision"], url=url,
                bytes=destination.stat().st_size, sha256=digest)


if __name__ == "__main__":
    specs = json.loads((ROOT / "config/local-models.json").read_text())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", nargs="+", choices=list(specs))
    parser.add_argument("--assets-only", action="store_true")
    args = parser.parse_args()
    if not args.models or args.assets_only:
        assets=json.loads((ROOT/"config/local-assets.json").read_text())
        for filename, asset in assets.items():
            target=CACHE/filename
            if not target.exists():
                if filename == "kokoro-v1.0.onnx":
                    download(asset["url"],target)
                else:
                    temporary=target.with_suffix(target.suffix+".partial")
                    with urllib.request.urlopen(asset["url"],timeout=120) as response, temporary.open("wb") as out:
                        while chunk:=response.read(1024*1024):out.write(chunk)
                    temporary.replace(target)
            with target.open("rb") as source:
                digest=hashlib.file_digest(source,"sha256").hexdigest()
            if digest != asset["sha256"]:raise RuntimeError(f"SHA-256 mismatch: {filename}")
            print(f"Verified {filename}",flush=True)
        if args.assets_only:
            raise SystemExit(0)
    if args.models:
        specs = {name: specs[name] for name in args.models}
    for name, spec in specs.items():
        metadata_url = f"https://huggingface.co/api/models/{spec['repo']}/revision/{spec['revision']}?blobs=true"
        with urllib.request.urlopen(metadata_url, timeout=60) as response:
            metadata = json.load(response)
        spec["hashes"] = {item["rfilename"]: item["lfs"]["sha256"] for item in metadata["siblings"] if "lfs" in item}
    jobs = [(name, spec, filename) for name, spec in specs.items() for filename in spec["files"]]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        rows = list(executor.map(fetch, jobs))
    manifest = "model-downloads.json" if not args.models else "model-downloads-" + "-".join(args.models) + ".json"
    (CACHE / manifest).write_text(json.dumps(rows, indent=2))
