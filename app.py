"""
NotebookLM Podcast 聽力練習介面

用法:
    venv\\Scripts\\python.exe -m streamlit run app.py

技術筆記(2026-08-08):
    原本的版本用 streamlit.components.v1.html 內嵌一個 iframe,靠
    window.parent 跨框存取外層頁面的 <audio> 元素和 localStorage,
    在桌面 Chromium 測試起來完全正常,但在 iPhone Safari 上會在任何
    文字渲染出來之前就讓分頁的渲染程序重複當機(Safari 顯示「重複發生
    問題」)。桌面瀏覽器測不出這種手機特有的跨框安全模型差異,所以改回
    完全不靠 iframe/跨框存取的原生 Streamlit 元件,犧牲掉自動同步高亮、
    單句循環這些效果,換取手機上的穩定性。之後如果要重新加這些功能,
    要先在真實手機上測過才能上線,不能只靠桌面瀏覽器測試就判斷沒問題。
"""

import json
from pathlib import Path

import streamlit as st

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

if "seek_time" not in st.session_state:
    st.session_state.seek_time = 0.0

audio_format = MIME_BY_EXT.get(audio_path.suffix.lower(), "audio/mpeg")
st.audio(str(audio_path), format=audio_format, start_time=st.session_state.seek_time)

st.divider()

show_zh = st.toggle("顯示中文翻譯", value=True)
search_query = st.text_input("搜尋關鍵字", placeholder="輸入英文或中文關鍵字篩選逐字稿")

for i, seg in enumerate(segments):
    if search_query:
        q = search_query.lower()
        if q not in seg["text"].lower() and q not in (seg.get("zh") or ""):
            continue

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
