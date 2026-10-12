# 結果報告の索引を更新するhelper

[文書の入口](../../README.md) · [実行・保存の目次](README.md) · [最新の引継ぎ](../../current-handoff.md)

実装は [update_results_index.py](../../../tools/update_results_index.py) です。
報告の件数や前回のリンクを含むPython source文字列を置換せず、現在のMarkdownの対象見出しと項目を読みます。
見出しの件数はリンク数から計算し、リンクは索引の親folderから現在の報告pathへの相対pathで作ります。
空白、日本語、丸括弧を含むpathはURL encodeします。docs内で文書を移した時も、呼出しに現在のpathを渡します。

## 文書用補助scriptから使う

~~~python
from update_results_index import prepare_result_index

report_bytes = "\n".join(report).encode("utf-8")
newindex = prepare_result_index(
    index, p, report[0].removeprefix("# "), pending_report=report_bytes,
)
rawdocs = {
    p: report_bytes,
    hand: (prefix + oldhand).encode("utf-8"),
    index: newindex,
}
# 全doc bytesを既存EvidenceStoreへ保存・容量照合してから、文書の書込みとGit保存へ進む。
~~~

`index`と`p`には現在の配置の絶対path、`report`には新しい報告本文を渡します。
別の索引を使う場合は`section`に件数を含まない見出し名を渡します。
新報告は`pending_report`で検査し、既存報告の上書きを拒否します。
既存報告は`pending_report`を省いて読み取り確認できます。

見出しの不在・重複、壊れた項目、同じ報告の重複、titleの衝突、docs外のpathは書込み前に拒否します。
同じpath/titleが登録済みなら重複追加しません。出力はUTF-8/LFです。
helperは候補bytesを返すだけです。文書の書込み、Git、評価の起動は既存の保存手順で行います。

## 読取りだけの確認

~~~text
python -B tools/update_results_index.py --report docs/results/anomaly-multiseed-v0.3-layout8-c2-quality-evaluation-2026-10-12.md --title "layout8 C2 quality実評価（2026-10-12）" --check
~~~

通常は候補diffを表示します。`--check`は更新不要ならexit0、更新が必要ならexit1、入力検査の失敗ならexit2です。
CLIはfileを書き換えません。

閉鎖済みartifactの補助scriptは当時の原証拠です。修正した共通helperは新しい文書生成から使い、旧scriptを再実行しません。
固定計画のpathやbytes、科学config、実行側の制限、正式gateを変更しません。

原因と新規試験の記録は [2026-10-12の修正報告](../../results/documentation-helper-index-repair-2026-10-12.md) を参照してください。
