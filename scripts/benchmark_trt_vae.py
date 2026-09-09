"""Build and compare a local TensorRT VAE decoder; never selects it in the app.

Use pinned optional dependencies in .cache/tensorrt-deps. Only locally built
engines in this experiment directory may be loaded. All probes are synthetic.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import statistics
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'.cache/tensorrt-deps'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label',required=True)
    parser.add_argument('--resume',action='store_true')
    args=parser.parse_args()
    if not re.fullmatch(r'[a-z0-9-]{1,32}',args.label):
        parser.error('Use a short lowercase label.')
    folder=ROOT/'generated/local-app/audit'/('visual-trt-'+args.label)
    folder.mkdir(exist_ok=args.resume)
    import torch
    import tensorrt as trt
    from local_app.visual import PortraitRenderer
    from local_app.trt_decoder import vae_source_hashes, verified_engine_bytes
    renderer=PortraitRenderer()
    renderer.prepare('fullbody',reference_path=ROOT/'generated/local-app/performance-near.png')
    class Decoder(torch.nn.Module):
        def __init__(self,vae):
            super().__init__(); self.vae=vae
        def forward(self,latent):
            return self.vae.decode(latent/self.vae.config.scaling_factor,return_dict=False)[0]
    decoder=Decoder(renderer.vae).eval()
    model_path=folder/'decoder.onnx'; engine_path=folder/'decoder.engine'; metadata_path=folder/'build.json'
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    with torch.inference_mode():
        latent=renderer.latent.expand(8,-1,-1,-1).clone().contiguous(memory_format=torch.channels_last)
        generator=torch.Generator(device='cuda').manual_seed(731)
        conditions=[torch.randn((8,50,384),device='cuda',dtype=renderer.dtype,generator=generator)*.2+renderer.pe for _ in range(12)]
        timestep=torch.tensor(0,device='cuda')
        probes=[renderer.unet(latent,timestep,encoder_hidden_states=c).sample.contiguous() for c in conditions]
        if not model_path.exists():
            started=time.perf_counter()
            torch.onnx.export(decoder,(probes[0],),str(model_path),input_names=['latent'],output_names=['pixels'],
                              opset_version=17,dynamo=False)
            print(json.dumps({'stage':'exported','seconds':time.perf_counter()-started,'bytes':model_path.stat().st_size}),flush=True)
        logger=trt.Logger(trt.Logger.WARNING)
        if not engine_path.exists():
            builder=trt.Builder(logger); network=builder.create_network(0)
            onnx_parser=trt.OnnxParser(network,logger)
            if not onnx_parser.parse_from_file(str(model_path)):
                raise RuntimeError('ONNX parse failed: '+'; '.join(str(onnx_parser.get_error(i)) for i in range(onnx_parser.num_errors)))
            config=builder.create_builder_config()
            config.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE,2<<30)
            config.builder_optimization_level=3
            print(json.dumps({'stage':'building','tensorrt':trt.__version__,'workspace_gib':2}),flush=True)
            started=time.perf_counter()
            serialized=builder.build_serialized_network(network,config)
            if serialized is None:
                raise RuntimeError('TensorRT did not build an engine.')
            engine_path.write_bytes(serialized)
            build={'tensorrt':trt.__version__,'gpu':torch.cuda.get_device_name(),'torch':torch.__version__,
                   'model_sha256':sha(model_path),'engine_sha256':sha(engine_path),'source_vae_sha256':vae_source_hashes(),
                   'reviewed':False,'build_s':time.perf_counter()-started,
                   'scope':'Locally exported FP16 decoder, fixed batch8, no change to selected app models.'}
            metadata_path.write_text(json.dumps(build,indent=2)+'\n')
            print(json.dumps({'stage':'built',**build}),flush=True)
            del serialized,onnx_parser,network,config,builder
        build=json.loads(metadata_path.read_text())
        if build['model_sha256']!=sha(model_path):
            raise ValueError('ONNX provenance does not match this local build.')
        versions={'tensorrt':trt.__version__,'gpu':torch.cuda.get_device_name(),'torch':torch.__version__}
        payload=verified_engine_bytes(folder,versions,vae_source_hashes(),require_review=False)
        runtime=trt.Runtime(logger); engine=runtime.deserialize_cuda_engine(payload)
        if engine is None:
            raise RuntimeError('Engine could not be loaded.')
        context=engine.create_execution_context()
        if tuple(engine.get_tensor_shape('latent'))!=(8,4,32,32) or tuple(engine.get_tensor_shape('pixels'))!=(8,3,256,256):
            raise ValueError('Unexpected decoder shapes.')
        if engine.get_tensor_dtype('latent')!=trt.float16 or engine.get_tensor_dtype('pixels')!=trt.float16:
            raise ValueError('Unexpected decoder precision.')
        output=torch.empty((8,3,256,256),device='cuda',dtype=torch.float16)
        def run(value):
            context.set_tensor_address('latent',value.data_ptr())
            context.set_tensor_address('pixels',output.data_ptr())
            if not context.execute_async_v3(torch.cuda.current_stream().cuda_stream):
                raise RuntimeError('TensorRT execution failed.')
            return output
        for _ in range(3):
            decoder(probes[0]); run(probes[0])
        torch.cuda.synchronize(); rows=[]
        pixels=lambda value:((value.float()/2+.5).clamp(0,1)*255).round()
        for i,value in enumerate(probes):
            timings={}
            # Alternate order to reduce fixed-order thermal/cache bias.
            for name in (['eager','trt'] if i%2==0 else ['trt','eager']):
                start=time.perf_counter(); result=decoder(value) if name=='eager' else run(value)
                torch.cuda.synchronize(); timings[name+'_s']=time.perf_counter()-start
                if name=='eager':expected=result
            valid=bool(torch.isfinite(output).all().item())
            difference=(pixels(expected)-pixels(output)).abs()
            rows.append({'index':i,**timings,'finite':valid,'pixel_mae_255':difference.mean().item(),'pixel_max_255':difference.max().item()})
        result={'build':build,'rows':rows,'median_s':{name:statistics.median(r[name+'_s'] for r in rows) for name in ['eager','trt']},
                'scope':'Synthetic conditioning, fixed batch8 VAE decoder only. Runtime tensor timing excludes the call and does not certify perceptual speech/video quality.'}
        (folder/'results.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result),flush=True)
        if not all(r['finite'] for r in rows):
            raise RuntimeError('Decoder produced non-finite pixels; rejected.')


if __name__=='__main__':
    main()
