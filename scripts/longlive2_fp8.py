"""Experimental native FP8 linear layer for isolated LongLive comparisons only."""
import torch


class FP8Linear(torch.nn.Module):
    def __init__(self, source, scaling='tensor'):
        super().__init__()
        if scaling not in {'tensor', 'row'}:
            raise ValueError('Unknown FP8 scaling.')
        self.scaling = scaling
        self.in_features, self.out_features = source.in_features, source.out_features
        weight = source.weight.detach().to(device='cuda', dtype=torch.bfloat16)
        scale = (weight.float().abs().amax(dim=1, keepdim=True) if scaling == 'row'
                 else weight.float().abs().amax()).clamp_min(1e-12) / 448
        self.register_buffer('quantized_weight', (weight / scale).clamp(-448, 448).to(torch.float8_e4m3fn))
        self.register_buffer('weight_scale', scale.t().contiguous() if scaling == 'row' else scale)
        self.register_buffer('bias', None if source.bias is None else source.bias.detach().to('cuda', dtype=torch.bfloat16))

    def forward(self, value):
        shape = value.shape
        value = value.reshape(-1, self.in_features)
        scale = (value.float().abs().amax(dim=1, keepdim=True) if self.scaling == 'row'
                 else value.float().abs().amax()).clamp_min(1e-12) / 448
        quantized = (value / scale).clamp(-448, 448).to(torch.float8_e4m3fn)
        result = torch._scaled_mm(quantized, self.quantized_weight.t(), scale_a=scale,
                                  scale_b=self.weight_scale, out_dtype=torch.bfloat16)
        if self.bias is not None:
            result = result + self.bias
        return result.to(value.dtype).reshape(*shape[:-1], self.out_features)


def quantize_blocks(model, scaling='tensor', skip_ffn_output=False):
    """Only block linears; optionally retain the measured slower FFN output in BF16."""
    count = 0
    for name, child in list(model.named_modules()):
        if isinstance(child, torch.nn.Linear) and name.startswith('blocks.'):
            if skip_ffn_output and name.endswith('.ffn.2'):
                continue
            parent_name, _, leaf = name.rpartition('.')
            parent = model.get_submodule(parent_name)
            setattr(parent, leaf, FP8Linear(child, scaling))
            count += 1
    return count
