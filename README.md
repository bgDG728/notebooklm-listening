# NotebookLM 聽力練習

把 NotebookLM 產生的 Audio Overview(podcast)轉成「英文逐字稿 + 中文翻譯 +
點擊跳轉 + 播放時自動高亮」的聽力練習介面。因為 NotebookLM 本身不提供逐字稿
匯出功能,這個專案用本機 Whisper 語音辨識來補上這一塊。

## 線上使用

部署在 Streamlit Community Cloud,手機/電腦瀏覽器打開網址即可使用,不需要
跟電腦同一個 Wi-Fi:

https://notebooklm-listening-btbg6pib3yktmnc2cyxjsj.streamlit.app

## 專案結構

```
notebooklm_listening/
├── audio/                  音檔(.m4a/.mp3/.wav)
├── transcripts/            逐字稿 JSON(含中文翻譯)+ 純文字版
├── app.py                  Streamlit 主程式
├── player_component.py     自訂播放器元件(同步高亮/搜尋/調速)
├── transcribe.py           語音辨識腳本(本機執行,需要 faster-whisper)
├── merge_translations.py   把中文翻譯合併進逐字稿 JSON
├── export_offline.py       匯出「音檔內嵌」的離線 HTML(不需連網)
├── requirements.txt        Streamlit Cloud 部署用(只需要 streamlit)
└── requirements-transcribe.txt   本機轉錄用(faster-whisper)
```

## 新增一集 podcast 的完整流程

### 1. 從 NotebookLM 下載音檔

打開 notebook → 找到 Audio Overview 卡片 → 「⋮」→ 下載,存成 audio 資料夾:

```
notebooklm_listening\audio\你的檔名.m4a
```

### 2. 本機跑語音辨識(產生英文逐字稿)

第一次使用需要先建立虛擬環境並安裝套件:

```
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-transcribe.txt
```

轉錄:

```
venv\Scripts\python.exe transcribe.py audio\你的檔名.m4a
```

會輸出:
- `transcripts\你的檔名.json`(給 app.py 用,zh 欄位是空的)
- `transcripts\你的檔名.txt`(純文字逐字稿,方便丟給 Claude 翻譯)

### 3. 請 Claude 補上中文翻譯

把 `transcripts\你的檔名.txt` 的內容貼給 Claude,請它逐句翻譯成自然的中文,
輸出一個 JSON 字串陣列(順序、句數要跟逐字稿完全一致),存成:

```
transcripts\你的檔名_zh.json
```

然後合併進逐字稿:

```
venv\Scripts\python.exe merge_translations.py transcripts\你的檔名.json transcripts\你的檔名_zh.json
```

### 4. 本機測試

```
venv\Scripts\python.exe -m streamlit run app.py
```

打開 http://localhost:8501,下拉選單選新的一集確認正常。

### 5. 部署更新(推上 GitHub 即自動重新部署)

```
git add audio transcripts
git commit -m "Add new episode: 你的檔名"
git push
```

Streamlit Community Cloud 會偵測到 GitHub 有新的 commit 自動重新部署,
大約 1-2 分鐘後線上版就會出現新的一集。

## 離線版(不需要網路)

如果想要完全離線使用(例如出國、飛機上),可以匯出一個音檔內嵌的獨立 HTML:

```
venv\Scripts\python.exe export_offline.py transcripts\你的檔名.json
```

會輸出 `offline\你的檔名.html`(檔案會比較大,因為音檔用 base64 包在裡面),
用任何裝置的瀏覽器打開就能離線播放+看逐字稿,不需要伺服器。

## 技術筆記

- `st.audio()` 如果不指定 `format` 參數,預設會標記成 `audio/wav`,
  m4a 檔案會因為 MIME type 不符而完全沒聲音(進度條正常跑但無聲音)。
  `app.py` 裡已經根據副檔名自動帶入正確的 `format`。
- 播放器的同步高亮/搜尋/調速是透過 `streamlit.components.v1.html`
  內嵌一個 iframe 元件,因為這個 iframe 跟主頁面同源,JS 可以直接用
  `window.parent.document` 抓到 `st.audio()` 產生的原生 `<audio>` 元素,
  藉此監聽播放進度、控制播放速度,不需要 `st.rerun()`。
- 曾經嘗試用 Streamlit 的 `enableStaticServing` 功能把音檔直接放在
  `static/` 資料夾讓元件自己內嵌播放,但這個功能在目前環境下對
  `/app/static/*` 的請求會靜默 fallback 回前端 SPA 頁面(回傳
  200 但內容是錯的),所以放棄這條路,改用上面同源 iframe 的做法。
