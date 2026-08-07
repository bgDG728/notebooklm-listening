"""
NotebookLM Podcast 聽力練習介面

用法:
    venv\\Scripts\\python.exe -m streamlit run app.py
"""

import json
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).parent
AUDIO_DIR = PROJECT_ROOT / "audio"
TRANSCRIPTS_DIR = PROJECT_ROOT / "transcripts"

MIME_BY_EXT = {
    ".m4a": "audio/mp4",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
}

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

if "seek_time" not in st.session_state:
    st.session_state.seek_time = 0.0

if not audio_path.exists():
    st.error(f"找不到對應音檔:{audio_path}")
    st.stop()

audio_format = MIME_BY_EXT.get(audio_path.suffix.lower(), "audio/mpeg")
st.audio(str(audio_path), format=audio_format, start_time=st.session_state.seek_time)

st.divider()

show_zh = st.toggle("顯示中文翻譯/解說", value=True)

for i, seg in enumerate(segments):
    mins, secs = divmod(int(seg["start"]), 60)
    col_btn, col_text = st.columns([1, 12])

    with col_btn:
        if st.button(f"▶ {mins}:{secs:02d}", key=f"jump_{i}"):
            st.session_state.seek_time = seg["start"]
            st.rerun()

    with col_text:
        st.markdown(f"**{seg['text']}**")
        if show_zh:
            if seg.get("zh"):
                st.caption(seg["zh"])
            else:
                st.caption("_(尚未加上中文解說)_")
