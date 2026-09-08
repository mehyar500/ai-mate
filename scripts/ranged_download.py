"""Resumable, byte-range-validated public artifact download for large weights."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import re
import time
import urllib.request


def download(url, destination, workers=12):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"Range": "bytes=0-0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        match = re.fullmatch(r"bytes 0-0/(\d+)", response.headers.get("Content-Range", ""))
        if not match:
            raise RuntimeError("Source does not support validated byte ranges.")
        size = int(match[1])
        response.read(1)
    if destination.exists() and destination.stat().st_size == size:
        return
    pieces = destination.parent / (destination.name + ".parts")
    pieces.mkdir(exist_ok=True)
    chunk_size = 16 * 1024 * 1024
    starts = list(range(0, size, chunk_size))

    def fetch(start):
        end = min(size, start+chunk_size)-1
        part = pieces / str(start)
        if part.exists() and part.stat().st_size == end-start+1:
            return part
        for attempt in range(3):
            try:
                request = urllib.request.Request(url, headers={"Range": f"bytes={start}-{end}"})
                with urllib.request.urlopen(request, timeout=90) as response:
                    if response.headers.get("Content-Range") != f"bytes {start}-{end}/{size}":
                        raise RuntimeError("Server returned the wrong byte range.")
                    data = response.read(end-start+2)
                if len(data) != end-start+1:
                    raise RuntimeError("Incomplete download chunk.")
                part.write_bytes(data)
                return part
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(1)
    print(f"Downloading {destination.name}: {size/1e9:.2f} GB in {len(starts)} chunks", flush=True)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        parts = list(executor.map(fetch, starts))
    temporary = destination.with_suffix(destination.suffix + ".partial")
    with temporary.open("wb") as output:
        for part in parts:
            with part.open("rb") as source:
                while block := source.read(4*1024*1024):
                    output.write(block)
    if temporary.stat().st_size != size:
        raise RuntimeError("Assembled download size mismatch.")
    temporary.replace(destination)
    for part in parts:
        part.unlink()
    pieces.rmdir()
    print(f"Ready {destination.name}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    download(args.url, args.destination)
