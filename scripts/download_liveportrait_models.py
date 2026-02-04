"""Download LivePortrait pretrained models from HuggingFace."""

from huggingface_hub import snapshot_download
import os

print("Downloading LivePortrait models from HuggingFace...")
print("This will download ~200MB of pretrained weights")
print()

# Download to LivePortrait directory
download_path = r"F:\Projects\LLM\LivePortrait\pretrained_weights"

try:
    snapshot_download(
        repo_id="KlingTeam/LivePortrait",
        local_dir=download_path,
        ignore_patterns=["*.git*", "README.md", "docs/*"],
    )
    print(f"\n✅ Models downloaded successfully to: {download_path}")
    
    # List downloaded files
    print("\nDownloaded files:")
    for root, dirs, files in os.walk(download_path):
        level = root.replace(download_path, '').count(os.sep)
        indent = ' ' * 2 * level
        print(f'{indent}{os.path.basename(root)}/')
        subindent = ' ' * 2 * (level + 1)
        for file in files[:10]:  # Show first 10 files per directory
            print(f'{subindent}{file}')
        if len(files) > 10:
            print(f'{subindent}... and {len(files) - 10} more files')
            
except Exception as e:
    print(f"\n❌ Error downloading models: {e}")
    print("\nYou can also download manually from:")
    print("https://huggingface.co/KlingTeam/LivePortrait")
