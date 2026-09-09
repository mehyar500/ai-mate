"""Isolated CUDA-graph trial using reviewed imagery and synthetic conditioning only."""
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from local_app.visual import PortraitRenderer


def main():
    folder = ROOT/'generated/local-app/audit/visual-graph'
    folder.mkdir(parents=True, exist_ok=True)
    renderer = PortraitRenderer()
    torch = renderer.torch
    renderer.prepare('fullbody', reference_path=ROOT/'generated/local-app/performance-near.png')
    with torch.inference_mode():
        latent = renderer.latent.expand(8, -1, -1, -1).clone().contiguous(memory_format=torch.channels_last)
        # Deterministic bounded probes test input replacement, not speech quality.
        generator = torch.Generator(device='cuda').manual_seed(731)
        conditions = [torch.randn((8,50,384), device='cuda', dtype=renderer.dtype, generator=generator)*.2+renderer.pe for _ in range(8)]
        timestep = torch.tensor(0, device='cuda')
        def run(a, b):
            predicted = renderer.unet(a, timestep, encoder_hidden_states=b).sample
            decoded = renderer.vae.decode(predicted/renderer.vae.config.scaling_factor).sample
            return ((decoded/2+.5).clamp(0,1).permute(0,2,3,1).float()*255).round().to(torch.uint8)
        stream = torch.cuda.Stream()
        stream.wait_stream(torch.cuda.current_stream())
        with torch.cuda.stream(stream):
            for _ in range(3):
                run(latent, conditions[0])
        torch.cuda.current_stream().wait_stream(stream)
        torch.cuda.synchronize()
        static_latent, static_condition = latent.clone(), conditions[0].clone()
        graph = torch.cuda.CUDAGraph()
        started = time.perf_counter()
        with torch.cuda.graph(graph):
            static_output = run(static_latent, static_condition)
        torch.cuda.synchronize()
        capture_s = time.perf_counter()-started
        rows = []
        for index, condition in enumerate(conditions):
            started = time.perf_counter()
            expected = run(latent, condition)
            torch.cuda.synchronize()
            eager_s = time.perf_counter()-started
            started = time.perf_counter()
            static_latent.copy_(latent); static_condition.copy_(condition)
            graph.replay()
            torch.cuda.synchronize()
            replay_s = time.perf_counter()-started
            difference = (expected.float()-static_output.float()).abs()
            rows.append({'index':index, 'eager_s':eager_s, 'replay_s':replay_s,
                         'pixel_mae':difference.mean().item(), 'pixel_max':difference.max().item()})
        result = {'torch':torch.__version__, 'capture_s':capture_s, 'rows':rows,
            'eager_median_s':statistics.median(r['eager_s'] for r in rows),
            'replay_median_s':statistics.median(r['replay_s'] for r in rows),
            'allocated_mib':torch.cuda.memory_allocated()/1048576,
            'reserved_mib':torch.cuda.memory_reserved()/1048576,
            'peak_allocated_mib':torch.cuda.max_memory_allocated()/1048576,
            'limits':'Single batch 8 neural-path experiment; synthetic conditioning; excludes speech, video tracking, browser and actual speech-quality validation.'}
        (folder/'results.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result),flush=True)
        if any(row['pixel_max']>1 for row in rows):
            raise RuntimeError('Graph output diverged from eager output.')


if __name__ == '__main__':
    main()
