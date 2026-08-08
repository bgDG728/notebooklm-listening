"""
NotebookLM Podcast 聽力練習介面

用法:
    venv\\Scripts\\python.exe -m streamlit run app.py

技術筆記(2026-08-08):
    第一版用 streamlit.components.v1.html 內嵌 iframe,靠 window.parent
    跨框存取外層頁面的 <audio> 元素和 localStorage,桌面 Chromium 測試
    正常但會讓 iPhone Safari 分頁渲染程序重複當機,改成完全不用 iframe
    的原生 Streamlit 元件(功能被迫閹割掉不少)。

    這一版嘗試在「保留功能」跟「手機安全」之間找折衷:仍然用
    components.v1.html,但整個播放器(含 <audio> 元素本身)都自包含在
    同一個 iframe 裡,完全不碰 window.parent。音檔用 base64 內嵌,
    事先用 compress_audio.py 壓成單聲道低位元率版本(web_audio/),
    避免內嵌原始大檔案。

    **這個版本還沒有在真實 iPhone 上驗證過**,只在桌面瀏覽器測試過。
    部署後務必請使用者實測,不能只憑本機/Playwright 測試結果就宣稱修好。
"""

import json
from pathlib import Path

import streamlit as st

import player_component

PROJECT_ROOT = Path(__file__).parent
WEB_AUDIO_DIR = PROJECT_ROOT / "web_audio"
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
web_audio_path = WEB_AUDIO_DIR / data["audio_file"]

if not web_audio_path.exists():
    st.error(
        f"找不到壓縮版音檔:{web_audio_path}\n\n"
        f"請先執行:`venv\\Scripts\\python.exe compress_audio.py audio\\{data['audio_file']}`"
    )
    st.stop()

player_component.render(segments, web_audio_path, episode_title=chosen.stem)
