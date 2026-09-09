"""Explicit unreviewed-engine allowance for isolated local benchmark scripts."""
from local_app.trt_decoder import TensorRTDecoder


class ExperimentalDecoder(TensorRTDecoder):
    def __init__(self,torch,folder):
        super().__init__(torch,folder,require_review=False)
