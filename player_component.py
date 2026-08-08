"""
自訂 JS 聽力練習播放器元件(自包含版,2026-08-08 重寫)。

舊版讓 iframe 裡的 JS 伸手跨框存取外層頁面(window.parent.document /
window.parent.localStorage)去控制 st.audio() 產生的原生 <audio> 元素,
桌面 Chromium 測試都正常,但會讓 iPhone Safari 的分頁渲染程序重複當機
(見 git log)。這一版整個播放器(含 <audio> 元素本身)都自包含在同一個
iframe 裡,完全不碰 window.parent,音檔用 base64 內嵌(先用
compress_audio.py 壓過,不會塞進原始大檔案)。

生字本用 iframe 自己的 localStorage 存 —— 因為 components.v1.html 的
iframe 跟主頁面同源,瀏覽器本來就會把它們視為同一個儲存空間,不需要
特地去跨框存取 window.parent.localStorage 才能共用。

功能:
  - 播放時自動高亮當前句子並自動捲動到該句
  - 點擊任一句直接跳轉播放
  - 可調整播放速度、關鍵字搜尋跳轉
  - 單句循環播放(跟讀/精聽練習)
  - 聽寫模式:文字預設模糊,點句子播放時才顯示
  - 點英文單字加入生字本(存在瀏覽器 localStorage,可複製匯出)

跟讀錄音(MediaRecorder)這次先不放進來,麥克風權限在 iframe 裡是另一個
獨立的風險項目,要先確認這個自包含架構本身在手機上安全,再單獨處理。
"""

import base64
import json
from pathlib import Path

import streamlit.components.v1 as components

MIME_BY_EXT = {
    ".m4a": "audio/mp4",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
}

_TEMPLATE = """
<div id="app">
  <style>
    html, body {{
      height: 100%;
      margin: 0;
    }}
    #app {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: #111;
      display: flex;
      flex-direction: column;
      height: 100%;
      box-sizing: border-box;
    }}
    #app * {{ box-sizing: border-box; }}
    .toolbar {{
      flex-shrink: 0;
      background: #fff;
      padding: 4px 4px 10px;
      border-bottom: 1px solid #eee;
    }}
    audio {{ width: 100%; margin-bottom: 8px; }}
    .controls-row {{
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      margin-bottom: 6px;
    }}
    .controls-row label {{ font-size: 0.85rem; color: #555; }}
    .btn {{
      border: 1px solid #ccc;
      background: #fff;
      border-radius: 6px;
      padding: 4px 10px;
      font-size: 0.82rem;
      cursor: pointer;
      white-space: nowrap;
    }}
    .btn.active {{ background: #ff4b4b; color: #fff; border-color: #ff4b4b; }}
    .btn.on {{ background: #0d6efd; color: #fff; border-color: #0d6efd; }}
    .speed-display {{
      display: inline-block;
      min-width: 54px;
      text-align: center;
      font-size: 0.85rem;
      font-weight: 600;
      font-variant-numeric: tabular-nums;
    }}
    .search-box {{
      flex: 1;
      min-width: 120px;
      padding: 5px 8px;
      border: 1px solid #ccc;
      border-radius: 6px;
      font-size: 0.85rem;
    }}
    #status {{ font-size: 0.78rem; color: #b00; margin-top: 2px; }}

    #vocabPanel {{
      display: none;
      border: 1px solid #eee;
      border-radius: 8px;
      padding: 8px;
      margin-top: 4px;
      max-height: 220px;
      overflow-y: auto;
      background: #fafafa;
    }}
    #vocabPanel.open {{ display: block; }}
    .vocab-item {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 8px;
      padding: 6px 0;
      border-bottom: 1px solid #eee;
      font-size: 0.85rem;
    }}
    .vocab-item .word {{ font-weight: 700; }}
    .vocab-item .ctx {{ color: #777; font-size: 0.78rem; }}
    .vocab-item button {{
      border: none;
      background: none;
      color: #b00;
      cursor: pointer;
      font-size: 0.9rem;
      flex-shrink: 0;
    }}
    .vocab-empty {{ color: #999; font-size: 0.85rem; }}
    .vocab-toolbar {{ display: flex; gap: 8px; margin-bottom: 6px; }}

    #list {{
      overflow-y: auto;
      flex: 1;
      padding: 4px 2px 40px;
    }}
    .seg {{
      display: flex;
      gap: 10px;
      padding: 10px 6px;
      border-bottom: 1px solid #f0f0f0;
      border-radius: 6px;
      cursor: pointer;
    }}
    .seg:hover {{ background: #f7f7f9; }}
    .seg.active {{ background: #fff4e5; }}
    .seg.looping {{ background: #e7f0ff; }}
    .seg.dimmed {{ display: none; }}
    .seg .ts {{
      flex-shrink: 0;
      width: 40px;
      color: #888;
      font-size: 0.78rem;
      padding-top: 2px;
    }}
    .seg .en {{ font-weight: 600; line-height: 1.6; font-size: 0.95rem; }}
    .seg .zh {{ color: #666; margin-top: 4px; line-height: 1.45; font-size: 0.88rem; }}
    .seg.hide-zh .zh {{ display: none; }}

    .word {{
      border-radius: 3px;
      padding: 0 1px;
    }}
    .word:active {{ background: #ffe08a; }}
    .word.saved {{ background: #d7ecff; }}
    .word.search-hit {{ background: #ffe08a; }}

    /* 聽寫模式:文字預設模糊看不清楚,點該句(revealed)才清楚 */
    #app.dictation .seg .en,
    #app.dictation .seg .zh {{
      filter: blur(6px);
      user-select: none;
      transition: filter 0.15s;
    }}
    #app.dictation .seg.revealed .en,
    #app.dictation .seg.revealed .zh {{
      filter: none;
      user-select: text;
    }}
    .dictation-hint {{
      display: none;
      font-size: 0.78rem;
      color: #0d6efd;
      margin-top: 4px;
    }}
    #app.dictation .dictation-hint {{ display: block; }}
  </style>

  <div class="toolbar">
    <audio id="player" controls preload="metadata">
      <source src="{audio_src}" type="{audio_type}">
    </audio>
    <div class="controls-row">
      <label>速度:</label>
      <button class="btn" id="speedDown">－</button>
      <span id="speedDisplay" class="speed-display">1.00x</span>
      <button class="btn" id="speedUp">＋</button>
      <button class="btn" id="speedReset">重設</button>
    </div>
    <div class="controls-row">
      <button class="btn" id="loopToggle">🔁 循環目前句子</button>
      <button class="btn" id="dictationToggle">🙈 聽寫模式</button>
      <button class="btn zh-toggle-btn" id="zhToggle">隱藏中文</button>
      <button class="btn" id="vocabToggle">📖 生字本 (<span id="vocabCount">0</span>)</button>
    </div>
    <div class="controls-row">
      <input class="search-box" id="search" type="text" placeholder="搜尋關鍵字...">
    </div>
    <div class="dictation-hint">聽寫模式已開啟:文字預設模糊,點一句播放時該句會顯示原文,考驗你聽不聽得懂。</div>
    <div id="status"></div>

    <div id="vocabPanel">
      <div class="vocab-toolbar">
        <button class="btn" id="vocabCopy">複製全部</button>
        <button class="btn" id="vocabClear">清空生字本</button>
      </div>
      <div id="vocabList"></div>
    </div>
  </div>

  <div id="list"></div>
</div>

<script>
(function() {{
  const segments = {segments_json};
  const episodeTitle = {episode_title_json};
  const appEl = document.getElementById('app');
  const list = document.getElementById('list');
  const player = document.getElementById('player');
  const zhToggle = document.getElementById('zhToggle');
  const search = document.getElementById('search');
  const statusEl = document.getElementById('status');
  const loopToggle = document.getElementById('loopToggle');
  const dictationToggle = document.getElementById('dictationToggle');
  const vocabToggle = document.getElementById('vocabToggle');
  const vocabPanel = document.getElementById('vocabPanel');
  const vocabList = document.getElementById('vocabList');
  const vocabCount = document.getElementById('vocabCount');
  const vocabCopy = document.getElementById('vocabCopy');
  const vocabClear = document.getElementById('vocabClear');

  let zhVisible = true;
  let activeIndex = -1;
  let loopEnabled = false;
  let loopIndex = -1;
  let dictationMode = false;

  const VOCAB_KEY = 'notebooklm_listening_vocab';

  function loadVocab() {{
    try {{
      return JSON.parse(localStorage.getItem(VOCAB_KEY) || '[]');
    }} catch (e) {{
      return [];
    }}
  }}

  function saveVocab(list) {{
    localStorage.setItem(VOCAB_KEY, JSON.stringify(list));
  }}

  function renderVocab() {{
    const vocab = loadVocab();
    vocabCount.textContent = vocab.length;
    vocabList.innerHTML = '';
    if (vocab.length === 0) {{
      vocabList.innerHTML = '<div class="vocab-empty">點逐字稿裡的英文單字,就會加進這裡。</div>';
      return;
    }}
    vocab.slice().reverse().forEach((item) => {{
      const div = document.createElement('div');
      div.className = 'vocab-item';
      const safeWord = item.word.replace(/</g, '&lt;');
      const safeSentence = item.sentence.replace(/</g, '&lt;');
      div.innerHTML = `
        <div>
          <div class="word">${{safeWord}}</div>
          <div class="ctx">${{safeSentence}}</div>
        </div>
        <button title="移除">✕</button>
      `;
      div.querySelector('button').addEventListener('click', () => {{
        const updated = loadVocab().filter((v) => v.ts !== item.ts);
        saveVocab(updated);
        renderVocab();
        markSavedWords();
      }});
      vocabList.appendChild(div);
    }});
  }}

  function addToVocab(word, sentence, zh) {{
    const vocab = loadVocab();
    const clean = word.replace(/[.,!?;:"'()]/g, '');
    if (!clean) return;
    const exists = vocab.some((v) => v.word.toLowerCase() === clean.toLowerCase());
    if (exists) {{
      statusEl.textContent = `「${{clean}}」已經在生字本裡了。`;
      statusEl.style.color = '#888';
      setTimeout(() => {{ statusEl.textContent = ''; }}, 1500);
      return;
    }}
    vocab.push({{ word: clean, sentence, zh, episode: episodeTitle, ts: Date.now() }});
    saveVocab(vocab);
    renderVocab();
    markSavedWords();
    statusEl.style.color = '#0a0';
    statusEl.textContent = `已加入生字本:${{clean}}`;
    setTimeout(() => {{ statusEl.textContent = ''; }}, 1500);
  }}

  function markSavedWords() {{
    const vocab = loadVocab().map((v) => v.word.toLowerCase());
    document.querySelectorAll('.word').forEach((el) => {{
      const clean = el.textContent.replace(/[.,!?;:"'()]/g, '').toLowerCase();
      el.classList.toggle('saved', vocab.includes(clean));
    }});
  }}

  function fmt(t) {{
    const m = Math.floor(t / 60);
    const s = Math.floor(t % 60).toString().padStart(2, '0');
    return m + ':' + s;
  }}

  // 把一句英文拆成可點擊的單字 span,標點符號留在旁邊不拆開語意。
  function buildWordSpans(text) {{
    const frag = document.createDocumentFragment();
    const tokens = text.split(/(\\s+)/);
    tokens.forEach((tok) => {{
      if (/^\\s+$/.test(tok) || tok === '') {{
        frag.appendChild(document.createTextNode(tok));
        return;
      }}
      const span = document.createElement('span');
      span.className = 'word';
      span.textContent = tok;
      frag.appendChild(span);
    }});
    return frag;
  }}

  const rows = segments.map((seg, i) => {{
    const div = document.createElement('div');
    div.className = 'seg';
    div.dataset.index = i;
    div.innerHTML = `
      <div class="ts">${{fmt(seg.start)}}</div>
      <div style="flex:1">
        <div class="en"></div>
        <div class="zh"></div>
      </div>
    `;
    const enEl = div.querySelector('.en');
    enEl.textContent = seg.text; // 先放純文字,捲動到附近時才拆成可點擊單字(見 hydrateWords)
    enEl.addEventListener('click', (e) => {{
      if (e.target.classList.contains('word')) {{
        e.stopPropagation();
        addToVocab(e.target.textContent, seg.text, seg.zh || '');
      }}
    }});
    div.querySelector('.zh').textContent = seg.zh || '';

    div.addEventListener('click', () => {{
      player.currentTime = seg.start;
      player.play();
      if (loopEnabled) loopIndex = i;
      if (dictationMode) div.classList.add('revealed');
    }});
    list.appendChild(div);
    return div;
  }});

  // 效能優化:353 句一次全部拆成單字 span 會產生數千個 DOM 節點,
  // 手機瀏覽器記憶體吃緊時容易當機。改成捲動到附近才拆字。
  const hydrated = new WeakSet();
  function hydrateWords(row, seg) {{
    if (hydrated.has(row)) return;
    hydrated.add(row);
    const enEl = row.querySelector('.en');
    enEl.textContent = '';
    enEl.appendChild(buildWordSpans(seg.text));
    markSavedWords();
  }}

  if ('IntersectionObserver' in window) {{
    const observer = new IntersectionObserver((entries) => {{
      entries.forEach((entry) => {{
        if (entry.isIntersecting) {{
          const idx = parseInt(entry.target.dataset.index, 10);
          hydrateWords(entry.target, segments[idx]);
          observer.unobserve(entry.target);
        }}
      }});
    }}, {{ root: list, rootMargin: '400px 0px' }});
    rows.forEach((row) => observer.observe(row));
  }} else {{
    rows.forEach((row, i) => hydrateWords(row, segments[i]));
  }}

  renderVocab();
  markSavedWords();

  player.addEventListener('timeupdate', () => {{
    const t = player.currentTime;

    if (loopEnabled && loopIndex !== -1) {{
      const seg = segments[loopIndex];
      const next = segments[loopIndex + 1];
      const segEnd = next ? next.start : (seg.end || player.duration);
      if (t >= segEnd || t < seg.start) {{
        player.currentTime = seg.start;
        return;
      }}
    }}

    let idx = segments.findIndex((seg, i) => {{
      const next = segments[i + 1];
      return t >= seg.start && (!next || t < next.start);
    }});
    if (idx !== -1 && idx !== activeIndex) {{
      if (activeIndex !== -1) rows[activeIndex].classList.remove('active');
      rows[idx].classList.add('active');
      rows[idx].scrollIntoView({{ block: 'center', behavior: 'smooth' }});
      if (dictationMode) rows[idx].classList.add('revealed');
      activeIndex = idx;
    }}
  }});

  // 語速微調:0.05 為單位加減,比固定倍數按鈕更精細。
  const SPEED_MIN = 0.5, SPEED_MAX = 2.0, SPEED_STEP = 0.05;
  let currentSpeed = 1.0;
  const speedDisplay = document.getElementById('speedDisplay');

  function setSpeed(v) {{
    const stepped = Math.round(v / SPEED_STEP) * SPEED_STEP;
    currentSpeed = Math.min(SPEED_MAX, Math.max(SPEED_MIN, stepped));
    player.playbackRate = currentSpeed;
    speedDisplay.textContent = currentSpeed.toFixed(2) + 'x';
  }}

  document.getElementById('speedDown').addEventListener('click', () => setSpeed(currentSpeed - SPEED_STEP));
  document.getElementById('speedUp').addEventListener('click', () => setSpeed(currentSpeed + SPEED_STEP));
  document.getElementById('speedReset').addEventListener('click', () => setSpeed(1.0));
  setSpeed(1.0);

  loopToggle.addEventListener('click', () => {{
    loopEnabled = !loopEnabled;
    loopToggle.classList.toggle('on', loopEnabled);
    if (loopEnabled) {{
      loopIndex = activeIndex !== -1 ? activeIndex : 0;
      rows.forEach(r => r.classList.remove('looping'));
      rows[loopIndex].classList.add('looping');
      statusEl.style.color = '#0d6efd';
      statusEl.textContent = '循環播放已開啟:會一直重複目前這句,點別句可以換循環目標。';
    }} else {{
      rows.forEach(r => r.classList.remove('looping'));
      statusEl.textContent = '';
    }}
  }});

  dictationToggle.addEventListener('click', () => {{
    dictationMode = !dictationMode;
    dictationToggle.classList.toggle('on', dictationMode);
    appEl.classList.toggle('dictation', dictationMode);
    if (!dictationMode) {{
      rows.forEach(r => r.classList.remove('revealed'));
    }}
  }});

  zhToggle.addEventListener('click', () => {{
    zhVisible = !zhVisible;
    zhToggle.textContent = zhVisible ? '隱藏中文' : '顯示中文';
    rows.forEach(r => r.classList.toggle('hide-zh', !zhVisible));
  }});

  vocabToggle.addEventListener('click', () => {{
    vocabPanel.classList.toggle('open');
    if (vocabPanel.classList.contains('open')) renderVocab();
  }});

  vocabCopy.addEventListener('click', () => {{
    const vocab = loadVocab();
    const text = vocab.map(v => `${{v.word}} — ${{v.sentence}}${{v.zh ? ' (' + v.zh + ')' : ''}}`).join('\\n');
    navigator.clipboard.writeText(text).then(() => {{
      statusEl.style.color = '#0a0';
      statusEl.textContent = '生字本已複製到剪貼簿。';
      setTimeout(() => {{ statusEl.textContent = ''; }}, 1500);
    }});
  }});

  vocabClear.addEventListener('click', () => {{
    if (!confirm('確定要清空整個生字本嗎?')) return;
    saveVocab([]);
    renderVocab();
    markSavedWords();
  }});

  search.addEventListener('input', () => {{
    const q = search.value.trim().toLowerCase();
    rows.forEach((row, i) => {{
      const seg = segments[i];
      const matches = !q || seg.text.toLowerCase().includes(q) || (seg.zh || '').includes(q);
      row.classList.toggle('dimmed', !matches);
      row.querySelectorAll('.word').forEach((w) => {{
        const hit = q && w.textContent.toLowerCase().includes(q);
        w.classList.toggle('search-hit', !!hit);
      }});
    }});
  }});
}})();
</script>
"""


def render(segments: list[dict], audio_path: Path, episode_title: str = "", height: int = 760):
    audio_bytes = audio_path.read_bytes()
    audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
    audio_type = MIME_BY_EXT.get(audio_path.suffix.lower(), "audio/mpeg")
    audio_src = f"data:{audio_type};base64,{audio_b64}"

    html = _TEMPLATE.format(
        audio_src=audio_src,
        audio_type=audio_type,
        segments_json=json.dumps(segments, ensure_ascii=False),
        episode_title_json=json.dumps(episode_title, ensure_ascii=False),
    )
    components.html(html, height=height, scrolling=True)
