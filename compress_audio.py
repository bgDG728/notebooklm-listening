"""
把音檔壓成單聲道低位元率版本,給互動播放器元件 base64 內嵌用。

原始音檔(audio/)保留原始品質給 Whisper 轉錄用;這裡產生的壓縮版
(web_audio/)只給播放器用,人聲 podcast 用低位元率完全足夠聽,
檔案可以縮到約原本的 1/5,大幅降低內嵌進 iframe 元件時的資料量。

用 imageio-ffmpeg 套件(pip install 就能用,不需要另外安裝系統版 ffmpeg)。

用法:
    venv\\Scripts\\python.exe compress_audio.py audio\\你的音檔.m4a
"""

import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg

PROJECT_ROOT = Path(__file__).parent
WEB_AUDIO_DIR = PROJECT_ROOT / "web_audio"

BITRATE = "48k"  # 人聲清晰度足夠,podcast 對話完全聽得清楚


def compress(audio_path: Path) -> Path:
    WEB_AUDIO_DIR.mkdir(exist_ok=True)
    out_path = WEB_AUDIO_DIR / audio_path.name

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    result = subprocess.run(
        [ffmpeg, "-i", str(audio_path), "-ac", "1", "-b:a", BITRATE, "-y", str(out_path)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(result.stderr[-2000:])
        raise RuntimeError(f"ffmpeg 壓縮失敗: {audio_path}")

    before = audio_path.stat().st_size / 1_000_000
    after = out_path.stat().st_size / 1_000_000
    print(f"壓縮完成: {before:.1f} MB -> {after:.1f} MB ({out_path})")
    return out_path


def main():
    if len(sys.argv) != 2:
        print("用法: python compress_audio.py audio\\你的音檔.m4a")
        sys.exit(1)

    audio_path = Path(sys.argv[1])
    if not audio_path.exists():
        print(f"找不到音檔: {audio_path}")
        sys.exit(1)

    compress(audio_path)


if __name__ == "__main__":
    main()
