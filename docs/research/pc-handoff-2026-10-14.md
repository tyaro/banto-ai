# Macへの作業引継ぎ（2026-10-14）

人の「別のPCで作業を継続します」「マックで作業をする予定」に従い、Macへ引き継ぐ。このWindows PCでは研究を停止する。direct/automationはPAUSED。`banto-10` の保存設定もPAUSEDであることを確認した。別PCの人の再開指示まで新実験を開始しない。

## 最初に読むもの

1. [current-handoff最上段](../current-handoff.md)。下段の古いACTIVEは現在の指示ではない。
2. [研究roadmap](research-roadmap.md)、[Astraの評価方法レビュー](demand-evaluation-methodology-astra-review-2026-10-14.md)。
3. [保存補正の誤差分解](../results/demand-correction-decomposition-2026-10-14.md)。
4. [最新の一軌跡・二選択点の結果](../results/demand-group-selection-2026-10-14.md)と[その契約](demand-group-selection-design-2026-10-14.md)。

最新の研究は一候補・一split・一seedで完了。店舗移行validationで選んだ3072更新は同店時間validationの3328更新よりjointが1.712943%良いが、mean28比0.597425%悪化。日次・総量も悪化し、暫定2%改善条件は未達。製品採用0。旧15店fitとの差には学習店舗数の違いがあり、選択方法だけの効果ではない。次は既存店舗の将来予測と未学習店舗への移行のどちらが実用途の主問か、mean28へ追加したい能力を整理する。seed/split/LR/幅/gridを自動追加しない。

## Gitから取得するもの

- Repository: `https://github.com/tyaro/banto-ai.git`
- Branch: `codex/preformal-acceptance-scope`
- この引継ぎ直前の最新研究保存HEAD: `87013829f99a435a6a56bfb366d66dc5b14f4a13`。本引継ぎの保存はその後の文書変更だけなので、別PCでは同branchの最新を取得する。

新規cloneの例（既存checkoutがある場合は、その作業差分を保全してから同branchを更新する）：

```bash
git clone --branch codex/preformal-acceptance-scope https://github.com/tyaro/banto-ai.git
```

コード、架空fixture、設計、集約結果、依存lockはGitから取得できる。原データ・profile・尺度・入力/予測ledger・weightsはGitへ送信していないため、cloneだけではローカルの研究証拠は揃わない。

## 別途コピーするもの

元PCの `D:/develop/banto-ai` から、選んだ媒体で次のdirectoryを同じrepository相対位置へコピーする。移動・削除は行わず、元PCの原証拠を残す。宛先に同名rootが既にある場合はmerge/上書きせず、既存状態を保全して衝突を確認する。

|範囲|内容と扱い|
|---|---|
|`data/`|公開原本、Store Salesの原本manifest/parts、旧C0/C1/C2を保全する圧縮archive。manifestとclosureも一緒にコピーする|
|`artifacts/`|学習結果・入力対応・原失敗・全ログ・過去の証拠。全履歴を継続する場合はdirectory全体をコピーする|

最新需要研究だけの小さな引継ぎでは、少なくとも以下の**全root**が必要。ファイルだけを抜いてclosureのあるrootを未完成にしない。この小範囲では他の過去研究の証拠一式を移したことにはならない。

- `artifacts/representative-demand-training-adequacy-20261014/` — 今回再利用した2013–14 snapshot/入力/尺度等。
- `artifacts/representative-demand-selected-series-20261014/` — 2015保存入力/profile/基準/旧予測/尺度等。
- `artifacts/representative-demand-group-selection-20261014/` — 最新一軌跡のinitial/best2/final/curve/journal/予測等。
- `artifacts/representative-demand-group-selection-*` の関連prep/records — 初launch failed、確認6件、continuation、文書照合、Git保存を含む。
- `artifacts/representative-demand-correction-decomposition-*` と `artifacts/representative-demand-astra-methodology-review-*` — 直前診断・失敗・レビューの記録とprep。

コピー後は元root-closedのfile集合・bytes/SHA256、EvidenceStoreは `tools/check_verification_record.py` による読取り照合を行う。これは転送整合性の確認であり、完成した学習/評価/確認/CIの再実行ではない。保存pathに元PCの絶対pathがあっても履歴を置換しない。新実行のpathだけ新契約で指定し、hash/seedを無限定に置換しない。

本作業でコピー先への転送やアーカイブ作成は行っていない。別PCの受領・hash一致もまだ確認していない。

## Macでの準備順序

1. **cloneと証拠コピー**。branchの最新を取得し、上記data/artifactsを相対位置ごとコピー。Macで受領したfileのbytes/SHAを元closureへ照合する。原model/評価は再実行しない。
2. **環境記録**。Apple Silicon/Intel、macOS、Python、利用するTorchのversion/build/architectureを新記録へ残す。
3. **Mac専用venv**。Windowsの `.venv` と `requirements-windows-cpu-py314.lock` をMacの完成環境として流用しない。通常のCPython3.14でMacのarchitectureに合うwheelを解決し、新exact-versionの依存記録を作る。
4. **Windows固有箇所の移植**。需要runnerが呼ぶ `tools/store_sales_final.py` の `private_memory()` はWindowsのWinDLL/GetProcessMemoryInfoを使い、非Windowsでは明示拒否する。旧artifactのlauncherも `C:/Python314/python.exe` や `.venv/Scripts/python.exe` を保存している。旧scriptを書き換えて再実行せず、新しいMac用launcher/資源計測を別unitで用意する。MacのRSS/footprintをWindows private bytesと同一の指標に見せず、計測の定義と上限対応を記録する。
5. **新環境の接続確認だけ**。依存import、CPU tensor、保存stateの読み方、メモリ/時間の計測を少量の新確認で検証。まずCPU/float32を維持し、MPSへの変更と新しい研究仮説を同時に混ぜない。新environmentの確認は完成した研究評価の再実行とは分ける。
6. **研究を再開**。実用途の主問を決め、次の未完成unitを新契約・fresh rootで進める。最新学習結果の全再学習/再評価は移行の必須工程ではない。

Macでの環境metadata確認例（このWindows PCでは実行していない）：

```bash
uname -m
sw_vers
python3.14 --version
python3.14 -m venv environments/demand-macos/.venv
```

[Python公式macOS説明](https://docs.python.org/3.14/using/mac.html)はApple Silicon/Intel向けのuniversal2 installerと、通常build/free-threaded buildの区別を説明している。[PyTorch公式macOS導入説明](https://pytorch.org/get-started/locally/)ではmacOSとPython3.10–3.14への案内を確認した。これはこのMacに対する特定wheel/lockの導入成功の証明ではない。旧Windows環境のlockには `torch==2.14.0`（実buildは2.14.0+cpu）があり、Macでの同version/buildの利用可能性はまだ固定・検証していない。compatible wheelがない場合は記録して止め、Python/Torchを無断で変更して旧条件と同一にしない。

現在の小型独自モデルはTorchを使うが公式TimesFM weightsは使わない。需要研究の再開にTimesFM本体や公式checkpointの再downloadは不要。元環境名 `timesfm3` の来歴は[環境説明](../../environments/timesfm3/README.md)に残す。Macへのruntime移植・依存解決・資源計測・model接続確認は今回まだ実施していない。

## 再開時の境界

人のGit送信承認は同送信先の独自source・架空fixture・集約報告の範囲で保持。原データ/予測/weights等を送信しない。新PCでの認証・permissionはそこで確認する。

実行900秒/private2GiB/output1GiB/single32MiB/32files、記録16MiB512files/part256KiB/reserve2MiB16files、prep128KiB16files、Git各512KiB16path/累積30秒を維持。閉鎖root追記・原helper反復・追加agent0。formal_permission=false/credit0/native7役禁止/登録holdout未読/正式受入未完了。2017/予約31–54を移転しただけで読取り許可にしない。CAREは手動download待ちで自動確認しない。
