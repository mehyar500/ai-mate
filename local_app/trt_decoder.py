"""Optional locally built TensorRT decoder; model rights remain unchanged."""
import hashlib
import json
from pathlib import Path
import sys

from .models import CACHE, ROOT


def vae_source_hashes():
    return {name:hashlib.sha256((CACHE/'sd-vae'/name).read_bytes()).hexdigest()
            for name in ['config.json','diffusion_pytorch_model.safetensors']}


def verified_engine_bytes(folder, versions, source_hashes, *, require_review=True):
    """Validate provenance before loading the executable engine artifact."""
    folder=Path(folder).resolve()
    record=folder/'build.json'; path=folder/'decoder.engine'
    if path.resolve().parent!=folder or record.resolve().parent!=folder:
        raise ValueError('Decoder files must stay in their local artifact directory.')
    if not 0<record.stat().st_size<=16384:
        raise ValueError('Invalid decoder manifest size.')
    metadata=json.loads(record.read_text(encoding='utf-8'))
    if not isinstance(metadata,dict) or (require_review and metadata.get('reviewed') is not True):
        raise ValueError('The decoder requires an explicit local review.')
    if any(metadata.get(key)!=value for key,value in versions.items()) or metadata.get('source_vae_sha256')!=source_hashes:
        raise ValueError('Decoder source, runtime or GPU does not match the local build.')
    if not 0<path.stat().st_size<=150_000_000:
        raise ValueError('Invalid decoder engine size.')
    payload=path.read_bytes()
    if hashlib.sha256(payload).hexdigest()!=metadata.get('engine_sha256'):
        raise ValueError('Decoder engine hash does not match the local build.')
    return payload


class TensorRTDecoder:
    def __init__(self,torch,folder=None,*,require_review=True):
        folder=Path(folder or CACHE/'musetalk-vae-trt').resolve()
        if require_review and folder!=(CACHE/'musetalk-vae-trt').resolve():
            raise ValueError('Use the reviewed local decoder directory.')
        if not require_review and (folder.parent!=(ROOT/'generated/local-app/audit').resolve() or not folder.name.startswith('visual-trt-')):
            raise ValueError('Use an isolated decoder benchmark directory.')
        sys.path.insert(0,str(ROOT/'.cache/tensorrt-deps'))
        import tensorrt as trt
        versions={'tensorrt':trt.__version__,'gpu':torch.cuda.get_device_name(),'torch':torch.__version__}
        payload=verified_engine_bytes(folder,versions,vae_source_hashes(),require_review=require_review)
        self.logger=trt.Logger(trt.Logger.WARNING)
        self.runtime=trt.Runtime(self.logger)
        self.engine=self.runtime.deserialize_cuda_engine(payload)
        if self.engine is None:
            raise RuntimeError('The decoder could not be loaded.')
        if (tuple(self.engine.get_tensor_shape('latent'))!=(8,4,32,32)
                or tuple(self.engine.get_tensor_shape('pixels'))!=(8,3,256,256)
                or self.engine.get_tensor_dtype('latent')!=trt.float16
                or self.engine.get_tensor_dtype('pixels')!=trt.float16):
            raise ValueError('Unexpected decoder shape or precision.')
        self.context=self.engine.create_execution_context()
        if self.context is None:
            raise RuntimeError('The decoder could not create an execution context.')
        self.torch=torch; self.stream=torch.cuda.Stream()
        self.output=torch.empty((8,3,256,256),device='cuda',dtype=torch.float16)

    def __call__(self,prediction):
        torch=self.torch; count=prediction.shape[0]
        if (not 1<=count<=8 or tuple(prediction.shape[1:])!=(4,32,32)
                or prediction.dtype!=torch.float16 or prediction.device.type!='cuda'):
            raise ValueError('The decoder supports one to eight FP16 GPU latents.')
        current=torch.cuda.current_stream()
        self.stream.wait_stream(current)
        with torch.cuda.stream(self.stream):
            value=prediction.contiguous()
            if count<8:
                value=torch.cat((value,torch.zeros((8-count,4,32,32),device=prediction.device,dtype=prediction.dtype)))
            value.record_stream(self.stream)
            self.context.set_tensor_address('latent',value.data_ptr())
            self.context.set_tensor_address('pixels',self.output.data_ptr())
            if not self.context.execute_async_v3(self.stream.cuda_stream):
                raise RuntimeError('Decoder execution failed.')
        current.wait_stream(self.stream)
        # The next invocation waits for the consumer's current stream before
        # reusing this buffer. The caller must consume it before another decode.
        return self.output[:count]
