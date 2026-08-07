"""
把逐字稿 JSON + 音檔打包成一個「自帶音檔」的離線 HTML 播放器。
不需要網路、不需要伺服器,手機用 Safari 打開就能離線聽+看逐字稿。

用法:
    venv\\Scripts\\python.exe export_offline.py transcripts\\你的逐字稿.json
"""

import base64
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
AUDIO_DIR = PROJECT_ROOT / "audio"
OFFLINE_DIR = PROJECT_ROOT / "offline"

MIME_BY_EXT = {
    ".m4a": "audio/mp4",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
}

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 0; padding: 16px; background: #fafafa; color: #111; }}
  h1 {{ font-size: 1.2rem; margin: 0 0 12px; }}
  audio {{ width: 100%; position: sticky; top: 0; z-index: 10; background: #fafafa; padding: 8px 0; }}
  .toggle {{ margin: 12px 0; }}
  .seg {{ display: flex; gap: 10px; padding: 10px 0; border-bottom: 1px solid #eee; }}
  .seg button {{ flex-shrink: 0; height: 34px; min-width: 56px; border: 1px solid #ccc; border-radius: 6px; background: #fff; font-size: 0.85rem; }}
  .seg .en {{ font-weight: 600; line-height: 1.4; }}
  .seg .zh {{ color: #666; margin-top: 4px; line-height: 1.4; }}
  .seg.hidden-zh .zh {{ display: none; }}
</style>
</head>
<body>
<h1>🎧 {title}</h1>
<audio id="player" controls src="{audio_src}"></audio>
<label class="toggle"><input type="checkbox" id="zhToggle" checked> 顯示中文翻譯</label>
<div id="list"></div>
<script>
const segments = {segments_json};
const list = document.getElementById('list');
const player = document.getElementById('player');

segments.forEach(seg => {{
  const div = document.createElement('div');
  div.className = 'seg';
  const mins = Math.floor(seg.start / 60);
  const secs = Math.floor(seg.start % 60).toString().padStart(2, '0');
  div.innerHTML = `
    <button>▶ ${{mins}}:${{secs}}</button>
    <div>
      <div class="en">${{seg.text}}</div>
      <div class="zh">${{seg.zh || ''}}</div>
    </div>
  `;
  div.querySelector('button').addEventListener('click', () => {{
    player.currentTime = seg.start;
    player.play();
  }});
  list.appendChild(div);
}});

document.getElementById('zhToggle').addEventListener('change', (e) => {{
  document.querySelectorAll('.seg').forEach(s => s.classList.toggle('hidden-zh', !e.target.checked));
}});
</script>
</body>
</html>
"""


def main():
    if len(sys.argv) != 2:
        print("用法: python export_offline.py transcripts\\你的逐字稿.json")
        sys.exit(1)

    json_path = Path(sys.argv[1])
    data = json.loads(json_path.read_text(encoding="utf-8"))

    audio_path = AUDIO_DIR / data["audio_file"]
    mime = MIME_BY_EXT.get(audio_path.suffix.lower(), "audio/mpeg")

    print(f"讀取音檔 {audio_path} ({audio_path.stat().st_size / 1_000_000:.1f} MB)...")
    audio_b64 = base64.b64encode(audio_path.read_bytes()).decode("ascii")
    audio_src = f"data:{mime};base64,{audio_b64}"

    html = HTML_TEMPLATE.format(
        title=json_path.stem,
        audio_src=audio_src,
        segments_json=json.dumps(data["segments"], ensure_ascii=False),
    )

    OFFLINE_DIR.mkdir(exist_ok=True)
    out_path = OFFLINE_DIR / f"{json_path.stem}.html"
    out_path.write_text(html, encoding="utf-8")

    size_mb = out_path.stat().st_size / 1_000_000
    print(f"完成!已輸出 {out_path} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
