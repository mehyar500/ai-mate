"""Prevent repeated punctuation from appearing as a clean recognition result."""
import unittest
from experiments.benchmark_asr_window import artifact_flags
from experiments.benchmark_call_asr import word_errors


class ASRBenchmarkScoringTests(unittest.TestCase):
    def test_word_score_alone_misses_the_observed_tail(self):
        text='Stay there. // // // //'
        self.assertEqual(word_errors('Stay there.',text),0)
        self.assertEqual(artifact_flags(text),['repeated_punctuation'])

    def test_repeated_dots_are_also_reported(self):
        self.assertEqual(artifact_flags('Do not move. . . . . . . . . .'),['repeated_punctuation'])

    def test_ordinary_punctuation_is_retained_without_flagging(self):
        for text in ['', 'No!', 'Wait... please.', 'Come closer. Actually, stay there.']:
            self.assertEqual(artifact_flags(text),[])


if __name__=='__main__':unittest.main()
