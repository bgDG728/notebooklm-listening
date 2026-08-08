# NotebookLM 聽力練習

把 NotebookLM 產生的 Audio Overview(podcast)轉成英文逐字稿 + 中文翻譯的
聽力練習工具。因為 NotebookLM 本身不提供逐字稿匯出功能,這個專案用本機
Whisper 語音辨識來補上這一塊。

## 功能

- **同步逐字稿**:英文原文 + 中文翻譯逐句對照,播放到哪句自動高亮+捲動到該句
- **點擊跳轉**:點任一句直接跳去該句播放
- **單句循環播放**:跟讀/精聽某一句時,反覆播放到你按掉為止
- **聽寫模式**:文字預設模糊看不清楚,播放中的句子才會顯示原文
- **生字本**:點英文單字直接存進生字本(含出處例句+中文翻譯),可一鍵複製匯出
- **關鍵字搜尋**、**調整播放速度**(0.75x/1x/1.25x/1.5x)

> **⚠️ 這個版本(2026-08-08 第二次改版)還沒有在真實 iPhone 上驗證過**,
> 只在桌面瀏覽器測試過。之前一版功能相同但架構不同,結果在 iPhone Safari
> 上會讓分頁渲染程序重複當機,細節見下方「技術筆記」。**部署後請務必在
> 手機上實際測試過,不要只憑這份文件或桌面測試結果就當作已修好。**

## 線上使用

部署在 Streamlit Community Cloud,手機/電腦瀏覽器打開網址即可使用,不需要
跟電腦同一個 Wi-Fi。實際網址請見 Streamlit Cloud 後台(share.streamlit.io)
底下 `bgDG728/notebooklm-listening` 這個 app 的 URL。

免費方案的 app 閒置一段時間會「睡著」,重新打開需要等 10-20 秒喚醒,這段
時間畫面看起來會像空白/卡住,是正常現象,不是壞掉。

## 專案結構

```
notebooklm_listening/
├── audio/                  原始音檔(.m4a/.mp3/.wav),給 Whisper 轉錄用
├── web_audio/               壓縮過的版本(單聲道低位元率),給播放器 base64 內嵌用
├── transcripts/            逐字稿 JSON(含中文翻譯)+ 純文字版
├── app.py                  Streamlit 主程式
├── player_component.py     自訂播放器元件(自包含 iframe,見技術筆記)
├── transcribe.py           語音辨識腳本(本機執行,需要 faster-whisper)
├── compress_audio.py       壓縮音檔給播放器用(需要 imageio-ffmpeg)
├── merge_translations.py   把中文翻譯合併進逐字稿 JSON
├── export_offline.py       匯出「音檔內嵌」的離線 HTML(不需連網)
├── requirements.txt        Streamlit Cloud 部署用(只需要 streamlit)
└── requirements-transcribe.txt   本機轉錄/壓縮用(faster-whisper, imageio-ffmpeg)
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

### 4. 壓縮音檔給播放器用

```
venv\Scripts\python.exe compress_audio.py audio\你的檔名.m4a
```

會輸出 `web_audio\你的檔名.m4a`(單聲道 48kbps,約原始檔案的 1/5 大小)。
**這個檔案要一起 commit 進 git**,app.py 是讀這個壓縮版而不是原始檔案。

### 5. 本機測試

```
venv\Scripts\python.exe -m streamlit run app.py
```

打開 http://localhost:8501,下拉選單選新的一集確認正常。**本機測試只能
驗證桌面瀏覽器行為,不能證明手機上沒問題**(見技術筆記)。

### 6. 部署更新(推上 GitHub 即自動重新部署)

```
git add audio web_audio transcripts
git commit -m "Add new episode: 你的檔名"
git push
```

Streamlit Community Cloud 會偵測到 GitHub 有新的 commit 自動重新部署,
大約 1-2 分鐘後線上版就會出現新的一集。**部署後在手機上實際打開測試過**
才算真的完成。

## 離線版(不需要網路)

如果想要完全離線使用(例如出國、飛機上),可以匯出一個音檔內嵌的獨立 HTML:

```
venv\Scripts\python.exe export_offline.py transcripts\你的檔名.json
```

會輸出 `offline\你的檔名.html`(檔案會比較大,因為音檔用 base64 包在裡面),
用任何裝置的瀏覽器打開就能離線播放+看逐字稿,不需要伺服器。

## 技術筆記

- `st.audio()` / `<audio>` 如果不指定正確的 MIME type,m4a 檔案會因為
  格式標記不符而完全沒聲音(進度條正常跑但無聲音)。
- 本機開發時如果改了 `app.py` 或 `player_component.py` 卻沒生效,先確認
  是不是有多個 `streamlit run` 進程占用同個 port 沒關掉(`Get-NetTCPConnection
  -LocalPort 8501` 查 PID,再用 `Get-CimInstance Win32_Process -Filter
  "ProcessId=<PID>"` 看完整指令),而不是先懷疑程式碼寫錯——`streamlit run`
  內部會另外產生一個用系統 Python 執行的子行程實際 serve 網頁,只關掉/
  重啟 venv 父行程,子行程可能變成孤兒繼續跑舊程式碼。

### 播放器架構的兩次嘗試(2026-08-08)

**第一版**用 `streamlit.components.v1.html` 內嵌一個 iframe,靠 JS 的
`window.parent.document` / `window.parent.localStorage` **跨框存取外層
頁面**的 `<audio>` 元素(由 `st.audio()` 產生),藉此監聽播放進度、控制
生字本等等,音檔本身走 Streamlit 官方的 `/media/` 串流端點。**這個做法
在桌面 Chromium(包括 Playwright 自動化測試)完全正常**,但實際在 iPhone
Safari 上使用時,會在任何逐字稿文字渲染出來之前就讓分頁的渲染程序重複
當機(Safari 顯示原生的「重複發生問題」錯誤頁,這個訊息專門代表「這個
網址的渲染程序連續當機好幾次」,不是網路慢或單純載入卡住)。

這是一個很重要的教訓:**桌面瀏覽器自動化測試測不出 Safari 特有的跨框
安全模型差異**,不能因為 Playwright/Chromium 測試都過就認定手機上沒問題。

**第二版(目前版本)**改成完全不碰 `window.parent` ——整個播放器,包括
`<audio>` 元素本身,都自包含在同一個 iframe 裡:
- 音檔用 base64 `data:` URI 直接內嵌進 iframe 的 HTML,不靠外部 `<audio>`
  元素或 Streamlit 的媒體端點
- 事先用 `compress_audio.py`(靠 `imageio-ffmpeg`,免安裝系統版 ffmpeg)
  把音檔壓成單聲道 48kbps,原始 36MB 壓到約 7MB 再內嵌,避免內嵌原始大檔案
- 生字本用 iframe **自己的** `localStorage`(不是 `window.parent.localStorage`)
  —— 因為 `components.v1.html` 的 iframe 本來就跟主頁面同源,瀏覽器會
  自動把它們視為同一個儲存空間,不需要特地跨框存取

理論上這樣完全避開了「跨框存取」這個最可疑的風險點,但**大檔案 base64
內嵌本身是另一種記憶體壓力**(整個音檔要先完整下載+解碼才能開始播放,
不像原生 `<audio src="檔案URL">` 可以用 HTTP range request 邊下載邊播),
所以這不是穩賺不賠的修法,一樣需要真人在真手機上測試才能下結論。

跟讀錄音(MediaRecorder + getUserMedia)這次刻意沒有放回來——麥克風權限
在 iframe 裡是另一個獨立的風險項目(iframe 的 `allow` 屬性、Safari 對
getUserMedia 在 iframe 裡的處理方式),要先確認這次的自包含架構本身在
手機上安全,才適合再疊加這個功能,避免一次改太多東西、出問題不知道是
哪個環節造成的。

`player_component.py` 目前就是這個自包含版本;第一版(跨框存取)的程式碼
留在 git 歷史紀錄裡(`git log -- player_component.py`),沒有另外保留檔案。
