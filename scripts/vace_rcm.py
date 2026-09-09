"""Experimental rCM generator transfer into original VACE pose conditioning.

The sampling equations follow NVlabs/rcm, Apache-2.0, revision
ed3cb14dd936f92cdc9f9381af7369991509b41f,
rcm/inference/wan2pt1_t2v_rcm_infer.py.
Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
Licensed under Apache-2.0: https://www.apache.org/licenses/LICENSE-2.0
Provided AS IS, without warranties or conditions of any kind.
Full license: config/third-party/rcm-LICENSE.txt. Changes in this adapter:
VACE conditioning and strict checkpoint transfer.

This transfer has no upstream VACE quality guarantee. Only the base generator
is replaced; the VACE control weights are retained, without distillation.
"""
import math
import time


def body_control_bounds(points, scores, size):
    """Rectangle covering all reliable commanded joints, with a 6% margin."""
    import numpy as np
    if points.ndim != 3 or points.shape[1:] != (134, 2) or scores.shape != (134,):
        raise ValueError('Expected full DWPose trajectories and confidence scores.')
    selected = points[:, scores >= .3]
    if selected.shape[1] < 8 or not np.isfinite(selected).all():
        raise ValueError('Insufficient finite body controls.')
    low = np.floor((selected.min(axis=(0, 1)) - .06) * size).astype(int).clip(0, size)
    high = np.ceil((selected.max(axis=(0, 1)) + .06) * size).astype(int).clip(0, size)
    if (high <= low).any():
        raise ValueError('Empty editable body region.')
    return int(low[0]), int(low[1]), int(high[0]), int(high[1])


def transfer_generator(base, accelerated):
    """Validate every generator tensor before returning a complete VACE state."""
    import torch
    expected = {k for k in base if not k.startswith('vace_')}
    incoming, counters, seen = {}, [], set()
    metadata = {'accum_video_sample_counter', 'accum_image_sample_counter',
                'accum_iteration', 'accum_train_in_hours'}
    for key, value in accelerated.items():
        name = key.removeprefix('net.')
        if name in seen or not isinstance(value, torch.Tensor):
            raise ValueError('Unexpected or duplicate rCM tensor: ' + name)
        seen.add(name)
        if name in metadata:
            # Released files contain uninitialized/signed counter values.
            # These four scalars are training metadata, never model weights.
            if value.ndim != 0 or not torch.isfinite(value):
                raise ValueError('Invalid rCM training counter: ' + name)
            counters.append(name)
            continue
        if name not in expected:
            raise ValueError('Unexpected rCM tensor: ' + name)
        target = base[name]
        if name == 'patch_embedding.weight' and value.ndim == 2 and target.ndim == 5:
            if value.shape != (target.shape[0], math.prod(target.shape[1:])):
                raise ValueError('Incompatible rCM patch embedding layout.')
            value = value.reshape(target.shape)
        if value.shape != target.shape or not value.is_floating_point() or not torch.isfinite(value).all():
            raise ValueError('Incompatible or nonfinite rCM tensor: ' + name)
        incoming[name] = value
    if set(incoming) != expected:
        raise ValueError('Incomplete rCM generator; refusing a partial transfer.')
    return {**base, **incoming}, {'replaced_base_tensors': len(incoming),
                                 'retained_control_tensors': len(base) - len(incoming),
                                 'discarded_training_counters': sorted(counters),
                                 'control_distilled': False, 'transfer_validated_visually': False}


def schedule(steps, device):
    import torch
    if steps not in (1, 2, 4):
        raise ValueError('This rCM experiment supports 1, 2 or 4 steps.')
    angles = torch.tensor([math.atan(80), *[1.5, 1.4, 1.0][:steps - 1], 0.],
                          dtype=torch.float64, device=device)
    return torch.sin(angles) / (torch.cos(angles) + torch.sin(angles))


def sample(pipe, prompt, frames, mask, reference, args, record):
    import torch
    timings = {}
    started = time.perf_counter()
    refs = [[reference]]
    z0 = pipe.vace_encode_frames([frames], refs, masks=[mask])
    m0 = pipe.vace_encode_masks([mask], refs)
    control = pipe.vace_latent(z0, m0)
    context = pipe.text_encoder([prompt], pipe.device)
    torch.cuda.synchronize()
    timings['control_encode_s'] = time.perf_counter() - started
    shape = (z0[0].shape[0] // 2, *z0[0].shape[1:])
    seq_len = math.prod(shape[1:]) // math.prod(pipe.patch_size)
    generator = torch.Generator(device=pipe.device).manual_seed(args.seed)
    times = schedule(args.steps, pipe.device)
    x = torch.randn(shape, dtype=torch.float32, device=pipe.device, generator=generator).double() * times[0]
    timings['denoising_steps_s'] = []
    with torch.no_grad(), torch.autocast('cuda', dtype=pipe.param_dtype):
        for current, following in zip(times[:-1], times[1:]):
            started = time.perf_counter()
            velocity = pipe.model([x.to(pipe.param_dtype)], t=(current.float() * 1000).reshape(1).to(pipe.param_dtype),
                                  context=context, seq_len=seq_len, vace_context=control,
                                  vace_context_scale=args.context_scale)[0].double()
            noise = torch.randn(shape, dtype=torch.float32, device=pipe.device, generator=generator)
            x = (1 - following) * (x - current * velocity) + following * noise
            torch.cuda.synchronize()
            timings['denoising_steps_s'].append(time.perf_counter() - started)
            print('rCM completed step ' + str(len(timings['denoising_steps_s'])), flush=True)
        started = time.perf_counter()
        video = pipe.decode_latent([x.float()], refs)[0]
        torch.cuda.synchronize()
        timings['decode_s'] = time.perf_counter() - started
    record['rcm_timing'] = timings
    record['rcm_sampling'] = {'steps': args.steps, 'sigma_max': 80, 'guidance': 'single conditional pass; distilled CFG',
                              'rectified_flow_times': times.cpu().tolist(), 'streaming': False}
    return video
