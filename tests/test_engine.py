"""Startup configuration boundaries; all fixtures are synthetic and offline."""
from pathlib import Path
import tempfile
import unittest

from local_app.engine import configure_runtime


class RuntimeSettingsTests(unittest.TestCase):
    def test_only_nonsecret_choices_are_loaded_and_process_values_win(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / '.env'
            path.write_text('AI_MATE_LLM_PROVIDER=cloudflare\n'
                            'AI_MATE_LLM_MODEL="example-model"\n'
                            'AI_MATE_ENV_FILE=credentials.env\n'
                            'CLOUDFLARE_API_KEY=synthetic-secret\n'
                            'PATH=untrusted\n', encoding='utf-8')
            env = {'AI_MATE_LLM_PROVIDER': 'ollama'}
            configure_runtime(path, env)
            self.assertEqual(env, {
                'AI_MATE_LLM_PROVIDER': 'ollama',
                'AI_MATE_LLM_MODEL': 'example-model',
                'AI_MATE_ENV_FILE': str(Path(folder) / 'credentials.env'),
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
