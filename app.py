"""
NotebookLM Podcast 聽力練習介面

用法:
    venv\\Scripts\\python.exe -m streamlit run app.py
"""

import json
from pathlib import Path

import streamlit as st

import player_component

MIME_BY_EXT = {
    ".m4a": "audio/mp4",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
}

PROJECT_ROOT = Path(__file__).parent
AUDIO_DIR = PROJECT_ROOT / "audio"
TRANSCRIPTS_DIR = PROJECT_ROOT / "transcripts"

st.set_page_config(page_title="英文聽力練習", layout="wide")
st.title("🎧 NotebookLM 聽力練習")

transcript_files = sorted(TRANSCRIPTS_DIR.glob("*.json"))

if not transcript_files:
    st.warning(
        "還沒有任何逐字稿。請先執行:\n\n"
        "`venv\\Scripts\\python.exe transcribe.py audio\\你的音檔.mp3`"
    )
    st.stop()

chosen = st.selectbox(
    "選擇要練習的 podcast",
    transcript_files,
    format_func=lambda p: p.stem,
)

data = json.loads(chosen.read_text(encoding="utf-8"))
segments = data["segments"]
audio_path = AUDIO_DIR / data["audio_file"]

if not audio_path.exists():
    st.error(f"找不到對應音檔:{audio_path}")
    st.stop()

audio_format = MIME_BY_EXT.get(audio_path.suffix.lower(), "audio/mpeg")
st.audio(str(audio_path), format=audio_format)

player_component.render(segments, episode_title=chosen.stem)
