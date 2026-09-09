"""An endpoint constraint must reach sampling and be removed before decoding."""
import unittest
from experiments.benchmark_ltx23 import workflow


class LTXEndpointTests(unittest.TestCase):
    def test_distinct_endpoint_reaches_sampler_and_both_decoders(self):
        graph=workflow('start.png',action='closer',end_reference='end.png',compare_decode=True)
        self.assertEqual(graph['27']['inputs']['image'],'end.png')
        self.assertEqual(graph['22']['inputs']['image'],['28',0])
        self.assertEqual(graph['22']['inputs']['frame_idx'],-1)
        self.assertEqual(graph['11']['inputs']['video_latent'],['22',2])
        self.assertEqual(graph['13']['inputs']['positive'],['22',0])
        self.assertEqual(graph['13']['inputs']['negative'],['22',1])
        for decoder in ['18','24']:
            self.assertEqual(graph[decoder]['inputs']['samples'],['23',2])

    def test_return_loop_keeps_original_reference(self):
        graph=workflow('start.png',return_to_reference=True)
        self.assertEqual(graph['22']['inputs']['image'],['7',0])
        self.assertNotIn('27',graph)

    def test_conflicting_endpoints_fail_before_inference(self):
        with self.assertRaises(ValueError):
            workflow('start.png',return_to_reference=True,end_reference='end.png')


if __name__=='__main__':unittest.main()
