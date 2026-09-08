"""Download the bounded LongCat full-body avatar checkpoint."""
from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="meituan-longcat/LongCat-Video-Avatar-1.5",
    local_dir=".cache/local-poc/longcat-avatar",
    allow_patterns=["base_model_int8/*", "*.json", "whisper-large-v3/*"],
)
