# NotebookLM 聽力練習

把 NotebookLM 產生的 Audio Overview(podcast)轉成英文逐字稿 + 中文翻譯的
聽力練習工具。因為 NotebookLM 本身不提供逐字稿匯出功能,這個專案用本機
Whisper 語音辨識來補上這一塊。

## 功能

- **逐字稿對照**:英文原文 + 中文翻譯逐句對照
- **點擊跳轉**:點任一句直接跳去該句播放
- **關鍵字搜尋**:快速找到提到某個字/句的地方
- **中文翻譯顯示開關**

> 目前版本刻意做得很簡單(純原生 Streamlit 元件,沒有自訂 JS/iframe),
> 原因見下方「技術筆記」——之前加的同步高亮、單句循環、生字本、跟讀錄音
> 這些功能,都是靠一個自訂 iframe 元件實作,結果在 iPhone Safari 上會讓
> 分頁渲染程序重複當機,所以整組拿掉了。

## 線上使用

部署在 Streamlit Community Cloud,手機/電腦瀏覽器打開網址即可使用,不需要
跟電腦同一個 Wi-Fi。實際網址請見 Streamlit Cloud 後台(share.streamlit.io)
底下 `bgDG728/notebooklm-listening` 這個 app 的 URL。

免費方案的 app 閒置一段時間會「睡著」,重新打開需要等 10-20 秒喚醒,這段
時間畫面看起來會像空白/卡住,是正常現象,不是壞掉。

## 專案結構

```
notebooklm_listening/
├── audio/                  音檔(.m4a/.mp3/.wav)
├── transcripts/            逐字稿 JSON(含中文翻譯)+ 純文字版
├── app.py                  Streamlit 主程式(純原生元件,見下方技術筆記)
├── player_component.py     舊版自訂播放器元件,目前沒有被使用(保留供參考)
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

打開 http://localhost:8501,下拉選單選新的一集確認正常。**本機測試只能
驗證桌面瀏覽器行為,不能證明手機上沒問題**(見技術筆記)。

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
- 本機開發時如果改了 `app.py` 卻沒生效,先確認是不是有多個 `streamlit run`
  進程占用同個 port 沒關掉(`Get-NetTCPConnection -LocalPort 8501` 可以查
  PID,再用 `Get-CimInstance Win32_Process -Filter "ProcessId=<PID>"` 看
  完整指令),而不是先懷疑程式碼寫錯——`streamlit run` 內部會另外產生一個
  用系統 Python 執行的子行程實際 serve 網頁,只關掉/重啟 venv 父行程,
  子行程可能變成孤兒繼續跑舊程式碼。

### 為什麼拿掉了同步高亮/循環/生字本/跟讀錄音(2026-08-08)

舊版用 `streamlit.components.v1.html` 內嵌一個 iframe 元件,靠 JS 的
`window.parent.document` / `window.parent.localStorage` 跨框存取外層頁面
的 `<audio>` 元素,藉此不用 `st.rerun()` 就能監聽播放進度、控制音量/生字本
等等。**這個做法在桌面 Chromium(包括 Playwright 自動化測試)完全正常**,
但實際在 iPhone Safari 上使用時,會在任何逐字稿文字渲染出來之前就讓分頁
的渲染程序重複當機(Safari 顯示原生的「重複發生問題」錯誤頁,這個訊息
專門代表「這個網址的渲染程序連續當機好幾次」,不是網路慢或單純載入卡住)。

這是一個很重要的教訓:**桌面瀏覽器自動化測試測不出 Safari 特有的跨框
安全模型差異**,不能因為 Playwright/Chromium 測試都過就認定手機上沒問題。
之後如果要重新加類似跨框存取的功能,必須先在真實 iPhone/Safari 上實測過
才能上線,純本機測試不足以驗證。

`player_component.py` 保留在專案裡供參考,但 `app.py` 已經不再 import
它,改成完全用原生 Streamlit 元件(`st.audio` + `st.button` 迴圈觸發
`st.rerun()`)重新實作核心功能。
