"""
自訂 JS 聽力練習播放器元件。

用 streamlit.components.v1.html 內嵌一個逐字稿清單元件。它不自己放音檔,
而是透過 window.parent.document 抓取 st.audio() 產生的原生 <audio> 元素
(components.v1.html 的 iframe 跟主頁面同源,可以直接互相存取 DOM)。

好處:
  - 音檔播放本身沿用 Streamlit 官方、經過驗證可靠的 st.audio() 機制
  - 播放時自動高亮當前句子並自動捲動到該句
  - 點擊任一句直接跳轉播放,不需要整頁重新渲染(不會 st.rerun)
  - 可調整播放速度、關鍵字搜尋跳轉
"""

import json

import streamlit.components.v1 as components

_TEMPLATE = """
<div id="app">
  <style>
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
    .controls-row {{
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }}
    .controls-row label {{ font-size: 0.85rem; color: #555; }}
    .speed-btn, .zh-toggle-btn {{
      border: 1px solid #ccc;
      background: #fff;
      border-radius: 6px;
      padding: 4px 10px;
      font-size: 0.82rem;
      cursor: pointer;
    }}
    .speed-btn.active {{ background: #ff4b4b; color: #fff; border-color: #ff4b4b; }}
    .search-box {{
      flex: 1;
      min-width: 120px;
      padding: 5px 8px;
      border: 1px solid #ccc;
      border-radius: 6px;
      font-size: 0.85rem;
    }}
    #status {{ font-size: 0.78rem; color: #b00; margin-top: 6px; }}
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
    .seg.dimmed {{ display: none; }}
    .seg .ts {{
      flex-shrink: 0;
      width: 46px;
      color: #888;
      font-size: 0.78rem;
      padding-top: 2px;
    }}
    .seg .en {{ font-weight: 600; line-height: 1.45; font-size: 0.95rem; }}
    .seg .zh {{ color: #666; margin-top: 4px; line-height: 1.45; font-size: 0.88rem; }}
    .seg.hide-zh .zh {{ display: none; }}
    mark {{ background: #ffe08a; padding: 0 1px; }}
  </style>

  <div class="toolbar">
    <div class="controls-row">
      <label>速度:</label>
      <button class="speed-btn" data-speed="0.75">0.75x</button>
      <button class="speed-btn active" data-speed="1">1x</button>
      <button class="speed-btn" data-speed="1.25">1.25x</button>
      <button class="speed-btn" data-speed="1.5">1.5x</button>
      <button class="zh-toggle-btn" id="zhToggle">隱藏中文</button>
      <input class="search-box" id="search" type="text" placeholder="搜尋關鍵字...">
    </div>
    <div id="status"></div>
  </div>

  <div id="list"></div>
</div>

<script>
(function() {{
  const segments = {segments_json};
  const list = document.getElementById('list');
  const zhToggle = document.getElementById('zhToggle');
  const search = document.getElementById('search');
  const statusEl = document.getElementById('status');
  let zhVisible = true;
  let activeIndex = -1;

  function getPlayer() {{
    try {{
      return window.parent.document.querySelector('audio');
    }} catch (e) {{
      return null;
    }}
  }}

  function fmt(t) {{
    const m = Math.floor(t / 60);
    const s = Math.floor(t % 60).toString().padStart(2, '0');
    return m + ':' + s;
  }}

  function highlightMatch(text, query) {{
    if (!query) return text;
    const idx = text.toLowerCase().indexOf(query.toLowerCase());
    if (idx === -1) return text;
    return text.slice(0, idx) + '<mark>' + text.slice(idx, idx + query.length) + '</mark>' + text.slice(idx + query.length);
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
    div.addEventListener('click', () => {{
      const player = getPlayer();
      if (!player) {{
        statusEl.textContent = '找不到播放器,請確認上方已載入音檔。';
        return;
      }}
      player.currentTime = seg.start;
      player.play();
    }});
    list.appendChild(div);
    return div;
  }});

  function renderText(query) {{
    segments.forEach((seg, i) => {{
      rows[i].querySelector('.en').innerHTML = highlightMatch(seg.text, query);
      rows[i].querySelector('.zh').innerHTML = highlightMatch(seg.zh || '', query);
    }});
  }}
  renderText('');

  function onTimeUpdate() {{
    const player = getPlayer();
    if (!player) return;
    const t = player.currentTime;
    let idx = segments.findIndex((seg, i) => {{
      const next = segments[i + 1];
      return t >= seg.start && (!next || t < next.start);
    }});
    if (idx !== -1 && idx !== activeIndex) {{
      if (activeIndex !== -1) rows[activeIndex].classList.remove('active');
      rows[idx].classList.add('active');
      rows[idx].scrollIntoView({{ block: 'center', behavior: 'smooth' }});
      activeIndex = idx;
    }}
  }}

  document.querySelectorAll('.speed-btn').forEach(btn => {{
    btn.addEventListener('click', () => {{
      const player = getPlayer();
      if (!player) {{
        statusEl.textContent = '找不到播放器,請確認上方已載入音檔。';
        return;
      }}
      document.querySelectorAll('.speed-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      player.playbackRate = parseFloat(btn.dataset.speed);
    }});
  }});

  zhToggle.addEventListener('click', () => {{
    zhVisible = !zhVisible;
    zhToggle.textContent = zhVisible ? '隱藏中文' : '顯示中文';
    rows.forEach(r => r.classList.toggle('hide-zh', !zhVisible));
  }});

  search.addEventListener('input', () => {{
    const q = search.value.trim();
    renderText(q);
    rows.forEach((row, i) => {{
      const seg = segments[i];
      const matches = !q || seg.text.toLowerCase().includes(q.toLowerCase()) || (seg.zh || '').includes(q);
      row.classList.toggle('dimmed', !matches);
    }});
  }});

  // 綁定播放進度事件。因為 iframe 跟主頁面同源,可以直接掛 listener。
  // Streamlit 有時會重新渲染 <audio>,所以用輪詢方式確保綁定到目前存在的元素。
  let boundPlayer = null;
  setInterval(() => {{
    const player = getPlayer();
    if (player && player !== boundPlayer) {{
      if (boundPlayer) boundPlayer.removeEventListener('timeupdate', onTimeUpdate);
      player.addEventListener('timeupdate', onTimeUpdate);
      boundPlayer = player;
      statusEl.textContent = '';
    }} else if (!player) {{
      statusEl.textContent = '找不到播放器,請確認上方已載入音檔。';
    }}
  }}, 1000);
}})();
</script>
"""


def render(segments: list[dict], height: int = 700):
    html = _TEMPLATE.format(segments_json=json.dumps(segments, ensure_ascii=False))
    components.html(html, height=height, scrolling=True)
