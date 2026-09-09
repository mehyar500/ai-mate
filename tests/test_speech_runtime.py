"""Optional speech acceleration must fail explicitly and preserve CPU recovery."""
from pathlib import Path
import tempfile
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch

from local_app.engine import configure_runtime
from local_app.speech_runtime import speech_device,validate_cuda_runtime,require_provider,load_runtime,ShrinkingSpeechSession


class SpeechRuntimeTests(unittest.TestCase):
    def test_cpu_recovery_overrides_local_gpu_choice_without_loading_runtime(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'.env';path.write_text('AI_MATE_TTS_DEVICE=cuda\nUNRELATED_SECRET=ignored\n')
            state={};configure_runtime(path,state);self.assertEqual(state,{'AI_MATE_TTS_DEVICE':'cuda'})
            state={'AI_MATE_TTS_DEVICE':'cpu'};configure_runtime(path,state);self.assertEqual(speech_device(state),'cpu')
        for value in ['auto','','remote','CUDA']:
            with self.assertRaises(ValueError):speech_device({'AI_MATE_TTS_DEVICE':value})
        with patch('local_app.speech_runtime.importlib.import_module') as importer:
            self.assertIs(load_runtime('cpu'),importer.return_value)
            importer.assert_called_once_with('onnxruntime')

    def test_wrong_binary_version_location_or_provider_cannot_be_selected(self):
        root=Path('synthetic-runtime')
        good={'__version__':'1.26.0','__file__':str(root/'onnxruntime/__init__.py'),
              'get_available_providers':lambda:['CPUExecutionProvider','CUDAExecutionProvider']}
        validate_cuda_runtime(SimpleNamespace(**good),root)
        for change in [{'__version__':'1.29.0'},{'__file__':str(Path('other-runtime')/'onnxruntime/__init__.py')},
                       {'get_available_providers':lambda:['CPUExecutionProvider']}]:
            with self.assertRaises(RuntimeError):validate_cuda_runtime(SimpleNamespace(**(good|change)),root)

    def test_missing_installation_and_loaded_cpu_module_fail_without_replacement(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with patch('local_app.speech_runtime.GPU_RUNTIME',root),patch('local_app.speech_runtime.importlib.import_module') as importer:
                with self.assertRaises(RuntimeError):load_runtime('cuda')
                importer.assert_not_called()
                (root/'onnxruntime').mkdir();(root/'onnxruntime/__init__.py').touch()
                existing=SimpleNamespace(__version__='1.29.0',__file__=str(root/'onnxruntime/__init__.py'))
                with patch.dict(sys.modules,{'onnxruntime':existing}):
                    with self.assertRaises(RuntimeError):load_runtime('cuda')
                importer.assert_not_called()

    def test_runtime_fallback_to_cpu_is_not_reported_as_gpu_execution(self):
        for providers in [[],['CPUExecutionProvider'],['CPUExecutionProvider','CUDAExecutionProvider']]:
            session=SimpleNamespace(get_providers=lambda:providers)
            with self.assertRaises(RuntimeError):require_provider(session,'cuda')
        require_provider(SimpleNamespace(get_providers=lambda:['CUDAExecutionProvider','CPUExecutionProvider']),'cuda')

    def test_arena_cleanup_preserves_outputs_metadata_and_errors(self):
        # Kokoro reads these session attributes before calling run. The adapter
        # must not rebuild a session, discard generated audio or retry a failure.
        runtime=Mock();session=Mock();session._model_path='synthetic.onnx'
        session.get_outputs.return_value=['waveform']
        adapter=ShrinkingSpeechSession(session,runtime)
        feed={'tokens':object()}
        self.assertEqual(adapter._model_path,'synthetic.onnx')
        self.assertEqual(adapter.get_outputs(),['waveform'])
        self.assertIs(adapter.run(None,feed),session.run.return_value)
        runtime.RunOptions.return_value.add_run_config_entry.assert_called_once_with(
            'memory.enable_memory_arena_shrinkage','gpu:0')
        session.run.assert_called_once_with(None,feed,run_options=runtime.RunOptions.return_value)
        session.run.side_effect=RuntimeError('allocation failed')
        with self.assertRaisesRegex(RuntimeError,'allocation failed'):adapter.run(None,feed)
        self.assertEqual(session.run.call_count,2)


if __name__=='__main__':unittest.main()
