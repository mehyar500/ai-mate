"""Check whether the pinned causal rCM checkpoint can be a VACE drop-in.

This is a CPU compatibility audit. Matching tensors do not prove causal VACE
quality: the released causal backbone and the VACE backbone expose different
forward interfaces, so the result must not select a runtime model by itself.
"""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def class_signature(path, class_name, method_name):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == method_name:
                    return [arg.arg for arg in child.args.args]
    raise ValueError(f'Missing {class_name}.{method_name} in {path.name}.')


def main():
    import torch
    from safetensors.torch import load_file
    from scripts.vace_rcm import transfer_generator

    manifest = json.loads((ROOT / 'config/vace-benchmark.json').read_text(encoding='utf-8'))
    spec = manifest['causal_rcm_experiment']
    for row in spec['source_files']:
        path = ROOT / row['path']
        if path.stat().st_size != row['size'] or sha256(path) != row['sha256']:
            raise ValueError('Unverified causal source asset: ' + path.name)
    model_row = spec['files'][0]
    candidate = ROOT / '.cache/local-poc/vace-models/rcm-Wan' / model_row['filename']
    if candidate.stat().st_size != model_row['size'] or sha256(candidate) != model_row['sha256']:
        raise ValueError('Unverified causal checkpoint.')
    base_path = ROOT / '.cache/local-poc/vace-models/Wan2.1-VACE-1.3B/diffusion_pytorch_model.safetensors'
    base = load_file(str(base_path))
    candidate_state = torch.load(candidate, weights_only=True, mmap=True, map_location='cpu')
    transferred, evidence = transfer_generator(base, candidate_state)
    del transferred, base, candidate_state

    causal_forward = class_signature(ROOT / '.cache/local-poc/rcm-source/rcm/networks/wan2pt1.py', 'WanModel', 'forward')
    vace_forward = class_signature(ROOT / '.cache/local-poc/Wan2.1/wan/modules/vace_model.py', 'VaceWanModel', 'forward')
    causal_has_cache = {'inference_state', 'attn_meta'}.issubset(causal_forward)
    causal_has_vace = 'vace_context' in causal_forward
    vace_has_control = 'vace_context' in vace_forward
    record = {
        'complete': True,
        'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'scope': 'CPU checkpoint/interface compatibility only; no generation, speech, streaming or app selection',
        'candidate': model_row['filename'],
        'candidate_sha256': model_row['sha256'],
        'base_generator_keys': 825,
        'retained_vace_control_keys': evidence['retained_control_tensors'],
        'transferred_generator_keys': evidence['replaced_base_tensors'],
        'causal_forward_args': causal_forward,
        'vace_forward_args': vace_forward,
        'causal_kv_cache_interface': causal_has_cache,
        'causal_vace_context_interface': causal_has_vace,
        'vace_control_interface': vace_has_control,
        'drop_in_live_vace': False,
        'decision': 'Reject as a runtime drop-in until a causal VACE adapter is implemented and visually qualified.',
        'reason': 'The checkpoint tensors transfer exactly, but causal KV-cache input and VACE control input are not exposed by the same forward interface.',
        'api_cost_usd': 0,
    }
    if not causal_has_cache or causal_has_vace or not vace_has_control:
        raise ValueError('Unexpected pinned interface evidence: ' + json.dumps(record))
    output = ROOT / 'generated/local-app/audit/causal-vace-compatibility.json'
    output.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(record))


if __name__ == '__main__':
    main()
