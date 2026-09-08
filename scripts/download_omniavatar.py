"""Download OmniAvatar 1.3B and its Wan2.1 base into the isolated cache."""
from huggingface_hub import snapshot_download

root = ".cache/local-poc/OmniAvatar/pretrained_models"
snapshot_download(
    repo_id="OmniAvatar/OmniAvatar-1.3B",
    local_dir=f"{root}/OmniAvatar-1.3B",
)
snapshot_download(
    repo_id="Wan-AI/Wan2.1-T2V-1.3B",
    local_dir=f"{root}/Wan2.1-T2V-1.3B",
)
snapshot_download(
    repo_id="facebook/wav2vec2-base-960h",
    local_dir=f"{root}/wav2vec2-base-960h",
)
