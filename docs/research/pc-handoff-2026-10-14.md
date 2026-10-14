# Macへの作業引継ぎ（2026-10-14）

## 最新のファイル整理

[承認済み旧証拠の削除結果と現在の保管範囲](workspace-retention-2026-10-14.md)を優先する。旧異常検知/Windows受入/旧CI/旧C0archiveの指定3.46GBはbackupなしで削除済み。最新需要研究と公開原本は保持し、Macには以下の需要最小セットを移す。旧証拠やWindowsvenvのコピーは不要。未分類/登録保護rootはWindows側で保持する。

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

## データセットの公式ダウンロードURL（2026-10-15追加）

### 現在の需要研究に必要：Store Sales

- [Kaggle Store Sales — Time Series Forecasting：データ取得ページ](https://www.kaggle.com/competitions/store-sales-time-series-forecasting/data)
- [同competitionの利用規約](https://www.kaggle.com/competitions/store-sales-time-series-forecasting/rules)

Macのブラウザでデータ取得ページを開き、必要なKaggleログイン・規約確認を人が行って、全ファイルのZIPを取得する。対象は **Store Sales — Time Series Forecasting**。別competitionの **Corporación Favorita Grocery Sales Forecasting** と取り違えない。認証・同意・Mac上のdownloadは今回代行していない。リンク到達は確認したが、Kaggleの認証後画面とMacでの取得成功は未確認。

必要な構成は `train.csv`、`test.csv`、`holidays_events.csv`、`stores.csv`、`transactions.csv`、`oil.csv`、`sample_submission.csv` の7CSV。[受領済み原本の構成と利用条件](store-sales-source-intake-2026-10-14.md)を参照する。販促計画の履歴はこのデータから追加取得できず、将来の販促実施値を過去時点の既知計画にしない。

既存のWindows受領ZIPとの照合値：

- ファイル名：`store-sales-time-series-forecasting.zip`
- サイズ：**22,416,355 bytes**
- SHA-256：`12e9c1dc4833cc804b3ff1515bd7b688f45fd8216fb2b340525036b006d625be`

新downloadは新しい一時取得directoryへ保存し、既存の閉鎖原本rootを上書きしない。Macでの照合例（取得先directoryで実行）：

```bash
wc -c < store-sales-time-series-forecasting.zip
shasum -a 256 store-sales-time-series-forecasting.zip
```

このSHAは受領済みZIPの実測値で、配布元が保証した期待hashではない。再取得ZIPが異なる場合は新原本として別に保持し、ZIP内memberを元source manifestと照合してから利用を判断する。過去入力のhashを新ZIPのhashへ置換しない。大きいCSVは既存のstream読取り・分割保存を使い、全CSVを一括展開して既存のsingle-file上限を超えない。

**公開原本の再downloadで戻るのは配布データだけ。** 元のsource manifest/closure、学習済みweights、入力/profile/予測ledger、最新需要26rootは元PCから別途コピーする。以下の転送範囲と照合方法は引き続き必要。

### 別用途の任意データ

現在の需要研究の再開には追加取得不要。設備研究などを再開するときの公式取得入口として残す。

| データセット | 公式ダウンロード入口 | 用途・現在の扱い |
| --- | --- | --- |
| Online Retail II | [UCI：Download](https://archive.ics.uci.edu/dataset/502/online%2Bretail%2Bii) | 別の需要・取引研究用。現在のStore Sales入力とは別 |
| Condition monitoring of hydraulic systems | [UCI：Download](https://archive.ics.uci.edu/dataset/447/condition%2Bmonitoring%2Bof%2Bhydraulic%2Bsystems) | 油圧試験装置の部品状態・多要素センサー。自然な寿命履歴とは区別 |
| MetroPT-3 | [UCI：Download](https://archive.ics.uci.edu/dataset/791/metropt%2B3%2Bdataset) | 実運用の空気圧縮機の予防保全研究用 |
| CARE to Compare | [Zenodo：Files（record 15846963 / v6）](https://zenodo.org/records/15846963) | 風車SCADAの早期故障検知。人の手動download待ちを維持。自動取得・進捗確認はしない |
| XJTU-SY | [公開者GitHub READMEの取得案内](https://github.com/WangBiaoXJTU/xjtu-sy-bearing-datasets) | 軸受の寿命・振動研究用。リンク先配布条件・再配布条件は利用前に確認 |

UCIの3件は各ページのDownloadから取得でき、各ページにCC BY 4.0が表示されている。CARE/XJTU-SYにはその条件を流用しない。任意データの原本pin・既存保存状況は[公開データ調査](public-dataset-survey.md)など各取得記録を参照し、新取得で閉鎖rootを変更しない。今回はリンク掲載だけでデータ本文のdownloadは0。

## 別途コピーするもの

元PCの `D:/develop/banto-ai` から、選んだ媒体で必要なdirectoryを同じrepository相対位置へコピーする。現在の研究の原証拠は元PCに残す。宛先に同名rootがあればmerge/上書きせず衝突を確認する。

|範囲|Macへの優先度|
|---|---|
|`data/public/store-sales-user-provided-20261014/`|需要研究の主入力。manifest/parts/closureを一緒にコピー|
|以下の最新需要artifact26root|約8.66MB。入力/モデル/結果/失敗対応をwhole rootでコピー|
|その他の公開原本、未分類/登録保護artifact|Windows側に保持。今回の需要最小移行から外す|

最新需要研究だけの小さな引継ぎでは、少なくとも以下の**全root**が必要。ファイルだけを抜いてclosureのあるrootを未完成にしない。この小範囲では他の過去研究の証拠一式を移したことにはならない。

- `artifacts/representative-demand-training-adequacy-20261014/` — 今回再利用した2013–14 snapshot/入力/尺度等。
- `artifacts/representative-demand-selected-series-20261014/` — 2015保存入力/profile/基準/旧予測/尺度等。
- `artifacts/representative-demand-group-selection-20261014/` — 最新一軌跡のinitial/best2/final/curve/journal/予測等。
- `artifacts/representative-demand-group-selection-*` の関連prep/records — 初launch failed、確認6件、continuation、文書照合、Git保存を含む。
- `artifacts/representative-demand-correction-decomposition-*` と `artifacts/representative-demand-astra-methodology-review-*` — 直前診断・失敗・レビューの記録とprep。

コピー後は元root-closedのfile集合・bytes/SHA256、EvidenceStoreは `tools/check_verification_record.py` による読取り照合を行う。これは転送整合性の確認であり、完成した学習/評価/確認/CIの再実行ではない。保存pathに元PCの絶対pathがあっても履歴を置換しない。新実行のpathだけ新契約で指定し、hash/seedを無限定に置換しない。

本作業でコピー先への転送やアーカイブ作成は行っていない。別PCの受領・hash一致もまだ確認していない。

## Macでの準備順序

1. **clone・原本取得・証拠コピー**。branchの最新を取得し、主入力は元原本rootのコピーを優先する。再downloadする場合は上記公式URLから新取得directoryへ保存して照合する。最新需要artifactsは別途相対位置ごとコピー。Macで受領したfileのbytes/SHAを元closureへ照合する。原model/評価は再実行しない。
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
