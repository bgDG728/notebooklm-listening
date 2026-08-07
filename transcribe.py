"""
把 audio/ 資料夾裡的 podcast 音檔轉成帶時間戳的逐字稿 JSON。

用法:
    venv\\Scripts\\python.exe transcribe.py audio\\your_podcast.mp3

輸出:
    transcripts\\<檔名>.json   ← 給 app.py 讀取用
    transcripts\\<檔名>.txt    ← 純文字逐字稿,方便直接閱讀
"""

import json
import sys
from pathlib import Path

from faster_whisper import WhisperModel

MODEL_SIZE = "small"  # tiny/base/small/medium/large-v3,越大越準但越慢
PROJECT_ROOT = Path(__file__).parent
TRANSCRIPTS_DIR = PROJECT_ROOT / "transcripts"


def transcribe(audio_path: Path) -> list[dict]:
    model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    segments, info = model.transcribe(str(audio_path), language="en", vad_filter=True)

    print(f"偵測語言: {info.language} (信心度 {info.language_probability:.2f})")

    results = []
    for seg in segments:
        results.append({
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "text": seg.text.strip(),
            "zh": "",  # 中文翻譯/解說先留空,之後由 Claude 逐句補上
        })
        print(f"[{seg.start:7.2f} -> {seg.end:7.2f}] {seg.text.strip()}")

    return results


def main():
    if len(sys.argv) != 2:
        print("用法: python transcribe.py audio\\your_podcast.mp3")
        sys.exit(1)

    audio_path = Path(sys.argv[1])
    if not audio_path.exists():
        print(f"找不到音檔: {audio_path}")
        sys.exit(1)

    TRANSCRIPTS_DIR.mkdir(exist_ok=True)
    stem = audio_path.stem

    segments = transcribe(audio_path)

    json_path = TRANSCRIPTS_DIR / f"{stem}.json"
    json_path.write_text(
        json.dumps({"audio_file": audio_path.name, "segments": segments}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    txt_path = TRANSCRIPTS_DIR / f"{stem}.txt"
    txt_path.write_text(
        "\n".join(s["text"] for s in segments),
        encoding="utf-8",
    )

    print(f"\n完成!已輸出:\n  {json_path}\n  {txt_path}")
    print("接下來把這份逐字稿貼給 Claude,請它幫每句補上中文翻譯/解說,寫回 JSON 的 zh 欄位。")


if __name__ == "__main__":
    main()
