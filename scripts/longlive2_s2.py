"""CPU unpacking of the pinned S2 checkpoint for an isolated BF16 experiment.

Calls the original FourOverSix PyTorch dequantizer in the verified LongLive
checkout; does not copy its implementation or import Blackwell extensions.
This is weight dequantization, not native NVFP4 inference: activations remain
BF16, so published NVFP4 quality/performance claims do not apply.
"""
import importlib
import sys
import time
import types


def load_dequantizer(code):
    """Load only the three pure-Python upstream modules, then restore imports."""
    source = code / 'fouroversix/src/fouroversix'
    if any(name == 'fouroversix' or name.startswith('fouroversix.') for name in sys.modules):
        raise RuntimeError('Use an isolated process without FourOverSix already imported.')
    try:
        for name, path in [('fouroversix', source), ('fouroversix.quantize', source / 'quantize')]:
            package = types.ModuleType(name)
            package.__path__ = [str(path)]
            sys.modules[name] = package
        return importlib.import_module('fouroversix.quantize.quantized_tensor').QuantizedTensor
    finally:
        for name in list(sys.modules):
            if name == 'fouroversix' or name.startswith('fouroversix.'):
                del sys.modules[name]


def verify_numeric_fixture(quantized_tensor):
    """Check every FP4 code, sign, nibble order, global scale and shape crop."""
    import torch
    # Both nibbles traverse all 16 codes in different orders. Build block
    # locations by explicit row/column indices, independently of the upstream
    # reshape implementation (128-row tiles, four scale columns per tile).
    packed = torch.arange(256, dtype=torch.uint8).repeat(64).reshape(128, 128)
    scale = torch.empty(128 * 16, dtype=torch.float32)
    matrix = torch.empty((128, 16), dtype=torch.bfloat16)
    for row in range(128):
        for column in range(16):
            value = 2. ** ((row + column) % 7 - 2)
            matrix[row, column] = value
            offset = (column // 4) * 512 + (row % 32) * 16 + (row // 32) * 4 + column % 4
            scale[offset] = value
    scale = scale.to(torch.float8_e4m3fn)
    result = quantized_tensor(packed, scale, torch.tensor([768.]), 'nvfp4',
                              (127, 251), 'mse', (128, 256)).dequantize()
    codes = [0., .5, 1., 1.5, 2., 3., 4., 6., -0., -.5, -1., -1.5, -2., -3., -4., -6.]
    expected = torch.tensor([[codes[int(byte) % 16], codes[int(byte) // 16]]
                             for byte in packed.flatten()], dtype=torch.bfloat16)
    expected = (expected.reshape(128, 256) * matrix.repeat_interleave(16, dim=1) * .5)[:127, :251]
    if not torch.equal(result, expected) or not torch.equal(torch.signbit(result), torch.signbit(expected)):
        raise ValueError('Upstream FP4 numeric fixture failed.')
    return {'all_16_codes': True, 'nibble_order': True, 'signed_zero': True,
            'global_scale': True, 'shape_crop': True, 'blocked_scale_layout': True}


def unpack_checkpoint(checkpoint, code):
    """Return a strict-loadable BF16 state and conversion evidence."""
    import torch
    started = time.perf_counter()
    if (checkpoint.get('checkpoint_format') != 'longlive_generator_nvfp4'
            or checkpoint.get('checkpoint_version') != 1 or checkpoint.get('merged_lora') is not True
            or checkpoint.get('model_name') != 'Wan2.2-TI2V-5B'):
        raise ValueError('Unsupported S2 checkpoint metadata.')
    quant = checkpoint.get('quantization', {})
    expected = {'format': 'nvfp4', 'backend': 'fouroversix', 'materialized': True,
                'dtype': 'bfloat16', 'weight_scale_rule': 'mse'}
    if any(quant.get(k) != v for k, v in expected.items()):
        raise ValueError('Unsupported S2 quantization settings.')
    tensor_class = load_dequantizer(code)
    fixture = verify_numeric_fixture(tensor_class)
    state = dict(checkpoint['generator'])
    prefixes = [k.removesuffix('quantized_weight_values') for k in state if k.endswith('quantized_weight_values')]
    if len(prefixes) != 300:
        raise ValueError('Expected exactly 300 materialized S2 linear layers.')
    for prefix in prefixes:
        names = [prefix + 'quantized_weight_' + suffix for suffix in ('values', 'scale_factors', 'amax', 'metadata')]
        if prefix + 'weight' in state or not all(n in state for n in names):
            raise ValueError('Incomplete or conflicting quantized weights: ' + prefix)
        values, scales, amax, metadata = [state[n] for n in names]
        if metadata.dtype != torch.int32 or tuple(metadata.shape) != (4,):
            raise ValueError('Invalid quantized shape metadata: ' + prefix)
        rows, cols, padded_rows, padded_cols = metadata.tolist()
        if (rows <= 0 or cols <= 0 or padded_rows < rows or padded_cols < cols
                or padded_rows % 128 or padded_cols % 64
                or values.dtype != torch.uint8 or tuple(values.shape) != (padded_rows, padded_cols // 2)
                or scales.dtype != torch.float8_e4m3fn or scales.ndim != 1
                or scales.numel() != padded_rows * padded_cols // 16
                or amax.dtype != torch.float32 or amax.numel() != 1
                or not torch.isfinite(amax).all() or amax.item() < 0):
            raise ValueError('Invalid quantized tensor layout: ' + prefix)
        weight = tensor_class(values, scales, amax, 'nvfp4', (rows, cols),
                              'mse', (padded_rows, padded_cols)).dequantize()
        if tuple(weight.shape) != (rows, cols) or not torch.isfinite(weight).all():
            raise ValueError('Invalid dequantized weights: ' + prefix)
        state[prefix + 'weight'] = weight.contiguous()
        for name in names:
            del state[name]
    if any('quantized_weight_' in name for name in state):
        raise ValueError('Unexpected quantized buffers remain.')
    return state, {'converted_linear_layers': len(prefixes), 'conversion_s': time.perf_counter() - started,
                   'numeric_fixture': fixture, 'compute_dtype': 'bfloat16', 'native_nvfp4': False,
                   'activation_quantization': False, 'merged_lora': True,
                   'method': 'pinned upstream QuantizedTensor.dequantize on CPU'}
