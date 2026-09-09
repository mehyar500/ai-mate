"""Startup configuration boundaries; all fixtures are synthetic and offline."""
from pathlib import Path
import tempfile
import unittest
import threading
from unittest.mock import Mock

from local_app.engine import CompanionEngine, configure_runtime


class RuntimeSettingsTests(unittest.TestCase):
    def test_priming_uses_only_verified_sources_and_deduplicates(self):
        with tempfile.TemporaryDirectory() as folder:
            app=CompanionEngine(folder)
            renderer=Mock()
            event=threading.Event()
            app.prime_reviewed_visual(renderer,event)
            renderer.prime_motion.assert_not_called()
            app.idle_video=Path(folder)/'idle.mp4'
            app.near_idle_video=Path(folder)/'near.mp4'
            app.performance={('base','closer'):{'path':Path(folder)/'closer.mp4'},
                             ('near','farther'):{'path':Path(folder)/'idle.mp4'}}
            renderer.prime_motion.return_value={'sources':3,'seconds':1.0}
            app.prime_reviewed_visual(renderer,event)
            renderer.prime_motion.assert_called_once_with([app.idle_video,app.near_idle_video,Path(folder)/'closer.mp4'],event)
            self.assertEqual(app.visual_warmup,{'sources':3,'seconds':1.0})

    def test_priming_failure_is_not_reported_as_ready_cache(self):
        with tempfile.TemporaryDirectory() as folder:
            app=CompanionEngine(folder)
            app.idle_video=Path(folder)/'idle.mp4'
            renderer=Mock();renderer.prime_motion.side_effect=RuntimeError('Synthetic failure')
            with self.assertRaises(RuntimeError):
                app.prime_reviewed_visual(renderer,threading.Event())
            self.assertIsNone(app.visual_warmup)

    def test_only_nonsecret_choices_are_loaded_and_process_values_win(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / '.env'
            path.write_text('AI_MATE_LLM_PROVIDER=cloudflare\n'
                            'AI_MATE_LLM_MODEL="example-model"\n'
                            'AI_MATE_ENV_FILE=credentials.env\n'
                            'AI_MATE_VISUAL_DECODER=tensorrt\n'
                            'CLOUDFLARE_API_KEY=synthetic-secret\n'
                            'PATH=untrusted\n', encoding='utf-8')
            env = {'AI_MATE_LLM_PROVIDER': 'ollama'}
            configure_runtime(path, env)
            self.assertEqual(env, {
                'AI_MATE_LLM_PROVIDER': 'ollama',
                'AI_MATE_LLM_MODEL': 'example-model',
                'AI_MATE_ENV_FILE': str(Path(folder) / 'credentials.env'),
                'AI_MATE_VISUAL_DECODER': 'tensorrt',
            })

    def test_missing_empty_and_comments_do_not_override_defaults(self):
        with tempfile.TemporaryDirectory() as folder:
            env = {}
            path = Path(folder) / '.env'
            configure_runtime(path, env)
            path.write_text('# AI_MATE_LLM_PROVIDER=bad\nAI_MATE_LLM_MODEL=\n', encoding='utf-8')
            configure_runtime(path, env)
            self.assertEqual(env, {})


if __name__ == '__main__':
    unittest.main()
