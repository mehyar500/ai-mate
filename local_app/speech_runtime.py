"""Explicit optional CUDA speech runtime; CPU remains the portable default."""
import importlib
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
GPU_RUNTIME=ROOT/'.cache/ort-gpu-deps'
CUDA_OPTIONS={'gpu_mem_limit':2*1024**3,'arena_extend_strategy':'kSameAsRequested',
              'cudnn_conv_algo_search':'HEURISTIC','cudnn_conv_use_max_workspace':0,'use_tf32':0}


def speech_device(environ=None):
    device=(os.environ if environ is None else environ).get('AI_MATE_TTS_DEVICE','cpu')
    if device not in {'cpu','cuda'}:raise ValueError('AI_MATE_TTS_DEVICE must be cpu or cuda.')
    return device


def validate_cuda_runtime(module, root=GPU_RUNTIME):
    if (getattr(module,'__version__',None)!='1.26.0'
            or Path(getattr(module,'__file__','')).resolve()!=root.resolve()/'onnxruntime/__init__.py'
            or 'CUDAExecutionProvider' not in module.get_available_providers()):
        raise RuntimeError('Install the pinned isolated CUDA speech runtime and restart, or set AI_MATE_TTS_DEVICE=cpu.')


def load_runtime(device):
    if device=='cpu':return importlib.import_module('onnxruntime')
    if device!='cuda':raise ValueError('Unsupported speech device.')
    if not (GPU_RUNTIME/'onnxruntime/__init__.py').is_file():
        raise RuntimeError('Install config/speech-gpu-benchmark-requirements.txt into .cache/ort-gpu-deps first, or select CPU speech.')
    loaded=sys.modules.get('onnxruntime')
    if loaded is not None:
        validate_cuda_runtime(loaded)
        return loaded
    sys.path.insert(0,str(GPU_RUNTIME))
    try:
        module=importlib.import_module('onnxruntime')
    finally:
        sys.path.remove(str(GPU_RUNTIME))
    validate_cuda_runtime(module)
    return module


def require_provider(session,device):
    wanted='CUDAExecutionProvider' if device=='cuda' else 'CPUExecutionProvider'
    if not session.get_providers() or session.get_providers()[0]!=wanted:
        raise RuntimeError('Selected speech execution provider failed; restart with AI_MATE_TTS_DEVICE=cpu to recover.')


class ShrinkingSpeechSession:
    """Release unused CUDA arena regions after each variable-length inference."""
    def __init__(self, session, runtime):
        self._session=session
        self._run_options=runtime.RunOptions()
        self._run_options.add_run_config_entry('memory.enable_memory_arena_shrinkage','gpu:0')

    def __getattr__(self,name):
        return getattr(self._session,name)

    def run(self,output_names,input_feed):
        return self._session.run(output_names,input_feed,run_options=self._run_options)


def create_speech(device, *, shrink_gpu_arena=True):
    """Return preset speech and metadata. No silent fallback or model download."""
    if device=='cuda':
        import torch
        dll=os.add_dll_directory(str(Path(torch.__file__).parent/'lib')) if os.name=='nt' else None
    else:dll=None
    ort=load_runtime(device)
    if device=='cuda':ort.preload_dlls(directory=str(Path(torch.__file__).parent/'lib'))
    from kokoro_onnx import Kokoro
    options=ort.SessionOptions();options.intra_op_num_threads=8;options.inter_op_num_threads=1
    options.log_severity_level=3
    providers=[('CUDAExecutionProvider',CUDA_OPTIONS),'CPUExecutionProvider'] if device=='cuda' else ['CPUExecutionProvider']
    session=ort.InferenceSession(str(ROOT/'.cache/local-poc/kokoro-v1.0.onnx'),sess_options=options,providers=providers)
    require_provider(session,device)
    if shrink_gpu_arena and device=='cuda':session=ShrinkingSpeechSession(session,ort)
    # Keep Windows' DLL directory handle alive for lazy library loads.
    voice=Kokoro.from_session(session,str(ROOT/'.cache/local-poc/voices-v1.0.bin'))
    return voice,{'device':device,'runtime':ort.__version__,'providers':session.get_providers(),'cpu_threads':8,
                  'arena_shrink_after_run':bool(shrink_gpu_arena and device=='cuda')},dll
