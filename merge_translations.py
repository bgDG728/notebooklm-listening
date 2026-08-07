"""
把中文翻譯合併進逐字稿 JSON 的 zh 欄位。

流程:
  1. 執行 transcribe.py 產生 transcripts\\<集數>.json(zh 欄位都是空字串)
  2. 把 transcripts\\<集數>.txt 的內容拿去請 Claude 逐句翻譯成中文,
     請它輸出一個 JSON 陣列(字串陣列),數量要跟逐字稿句數一致,
     存成 transcripts\\<集數>_zh.json
  3. 執行本腳本合併:

    venv\\Scripts\\python.exe merge_translations.py transcripts\\<集數>.json transcripts\\<集數>_zh.json
"""

import json
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 3:
        print("用法: python merge_translations.py transcripts\\<集數>.json transcripts\\<集數>_zh.json")
        sys.exit(1)

    transcript_path = Path(sys.argv[1])
    zh_path = Path(sys.argv[2])

    data = json.loads(transcript_path.read_text(encoding="utf-8"))
    zh_list = json.loads(zh_path.read_text(encoding="utf-8"))

    segments = data["segments"]
    if len(zh_list) != len(segments):
        print(
            f"數量不一致:逐字稿有 {len(segments)} 句,翻譯檔有 {len(zh_list)} 句。"
            "請確認翻譯是逐句對應、沒有漏掉或多出來的句子。"
        )
        sys.exit(1)

    for seg, zh in zip(segments, zh_list):
        seg["zh"] = zh

    transcript_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"完成!已將 {len(zh_list)} 句翻譯合併進 {transcript_path}")


if __name__ == "__main__":
    main()
