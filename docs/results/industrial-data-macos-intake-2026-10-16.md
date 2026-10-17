# 産業用3データセットのMac新規取得と入力準備（2026-10-16）

人の「Windowsからコピーせず公式配布元からMacへ取得して準備」に対応。[事前の取得範囲](../research/industrial-data-macos-intake-contract-2026-10-16.md)に従い、**MetroPT-3・油圧・XJTU-SYの原本を新規取得し、Macで入力準備と保存値の読戻しを完了した。** モデル学習・予測・性能採点は行っていない。

## 取得した原本

| データ | 公式入口・取得先 | 原本の容量と確認 |
| --- | --- | --- |
| MetroPT-3 | [UCI 791](https://archive.ics.uci.edu/dataset/791/metropt%2B3%2Bdataset)のDownload | 218,381,995 B。既存原本pinと一致、ZIP全2memberのCRC/bytes/SHA確認 |
| Condition monitoring of hydraulic systems | [UCI 447](https://archive.ics.uci.edu/dataset/447/condition%2Bmonitoring%2Bof%2Bhydraulic%2Bsystems)のDownload | 76,601,704 B。既存原本pinと一致、ZIP全20memberのCRC/bytes/SHA確認 |
| XJTU-SY | [公開者のGitHub案内](https://github.com/WangBiaoXJTU/xjtu-sy-bearing-datasets)および[公開者サイト](https://biaowang.tech/xjtu-sy-bearing-datasets/)が指定するGoogle Drive | 6分割RAR、計4,444,600,440 B。全6partのSHA保存、7-Zipで全9,217file/19folder・6volumeのCRC検査exit0 |

原本合計4,739,584,139 B。repository外の同workspace `outputs/industrial-source-cache-20261016/` に保存した。原本cacheは新しい実験結果artifactと区別する。約111GiBの空きを確認して開始。既存の7KBのMetroPT同名ZIPは研究原本に使わず、上書きもしていない。

[原本index・全hash](../../datasets/manifests/industrial-macos-source-index-20261016.json)。UCIの2件は公式ページのCC BY 4.0と帰属を記録。XJTUは公開者の予後アルゴリズム検証への利用・論文引用案内に基づく研究取得であり、CC BYや商用・再配布条件を推定していない。XJTUのhashはローカル受領原本の識別で、配布者署名・公開された期待digestと同じものではない。

## 準備した入力

| データ | 保存先 | 確認した範囲 |
| --- | --- | --- |
| MetroPT-3 | [dataset manifest](../../artifacts/public-datasets/metropt3-public-2020-02-21/dataset-manifest.json) | 既読探索日2020-02-21、1設備・60秒間隔・14信号・1,440点。既存のmean/last集約、補間なし、864/288/288 split |
| 油圧 | [dataset.json](../../artifacts/public-datasets/hydraulic-macos-20261016/dataset.json) | 全2,205cycle。PS1/PS2圧力とEPS1電力を100Hzから10サンプル平均で10Hzへ。各cycle600点、3本のfloat32 little-endianファイル |
| XJTU-SY | [dataset.json](../../artifacts/public-datasets/xjtu-sy-macos-20261016-7zip/dataset.json) | 原本は全15軸受・9,216波形を保持。全member一覧と、事前に選んだBearing1_1/2_1/3_1の完全寿命系列の8特徴量を準備 |

生成rootはMetroPT 9file/1,515,357 B、油圧9file/16,023,212 B、XJTU成功13file/10,510,649 B。各file32MiB、normal24file/768MiB等の既存上限内。原本cacheはこれらの生成物へ大量複製していない。

### MetroPT-3

既存の標準化変換をMacで適用し、dataset fingerprintは保存済みの `e6210e4e48e05c025fc8895ddeddf0c53a49dc53fd1c2f49e8c3272a3c7b37b0` と一致した。原本は全期間を取得したが、今回の数値変換はこの既読探索日だけ。元のtimezone不明・研究上UTCの仮定とmode unknownを維持し、故障報告を既知将来入力へ入れていない。

既存 `models/mini-transformer/data.py::load_fixed_day` へ接続し、context [1,3,128]、future target [1,3,32]を確認。利用可能originはtrain705/validation9/test9。train-only尺度の入力準備までで、モデル・optimizerは起動していない。この単日を新しい未知性能評価へ読み替えない。

### 油圧

原本20memberを保持し、モデル入力の初期版にはPS1/PS2/EPS1だけを使った。他のセンサーは捨てず原本内に残る。平均化は高周波を保持する変換ではないため、振動・高速過渡を検証する時は原rateの別契約が必要。

`condition-labels.json` にcooler/valve/pump leakage/accumulator/unstable flagの5列を別保存。入力側にこのprofileを含めない。splitはcycle番号の固定ブロックtrain[0,1323)、validation[1323,1764)、test[1764,2205)。同じ試験装置内の探索分割であり、独立設備の検証や自然な寿命履歴ではない。

[industrial_data.hydraulic_window](../../tools/public-data/industrial_data.py)がcycleを跨がないcontext/futureを返す。3splitの実データ窓、cycle境界・split違反の3拒否、3センサー先頭binの独立原本照合を確認した。C128/H32の場合は入力12.8秒・予測3.2秒であり、MetroPTの128分/32分とは別の時間幅。元SmallForecasterの旧重み・旧target契約を流用した性能確認ではない。

### XJTU-SY

公式説明は、各波形が2振動軸・25.6kHz・32,768点（1.28秒）、取得間隔が1分。file間を連続25.6kHz波形へ結合しない。全15軸受のfile番号が1から欠番・重複なく連続することを確認した。

各運転条件の軸受ordinal1を観測読取り前に固定し、Bearing1_1は123、Bearing2_1は491、Bearing3_1は2,538波形を数値検査。両軸のmean/RMS/std/peak-to-peakを1波形1行へ保存した。全3,152波形について2列・32,768行・有限値を確認し、部分寿命へ切り取っていない。元の振動単位は公開者ページから推定せず、原単位のまま扱う。

残る12軸受も原本から読み出せるが、今回その特徴量はまだ生成していない。初期の分割案は各条件のordinal1–3をtrain、4をvalidation、5をtestとする軸受単位で、random window混合をしない。これは今後の開発案であり、既存の正式holdoutとは別物。RUL・故障型labelを作っておらず、総file数・最終寿命をモデル入力にも入れていない。8特徴量を既存V3モデルへ無条件で直結することもしていない。予測・異常予兆・寿命推定のどれを問うかに合わせ、入力/出力と評価を次に固定する。

## 失敗と警告

- 最初のネットワーク確認はsandboxのDNS制限でcurl exit6。本体取得前のtool観測であり、保存済みデータの品質失敗としない。ユーザー承認でsessionのネットワーク権限を得た後、HTTPS/TLS検証を維持して取得した。
- Mac標準libarchiveはXJTU RAR5読取り中に `Unsupported block header size (was 5, max is 2)` でexit1。235.65秒・約68.6MB peakRSS。失敗root [原記録](../../artifacts/macos-industrial-prepare-xjtu-20261016-records/root-closed.json)と[failed dataset root](../../artifacts/public-datasets/xjtu-sy-macos-20261016/root-closed.json)を保持した。完成へ書き換えていない。
- [7-Zip公式Mac配布](https://www.7-zip.org/download.html)の26.04をworkspace内だけに追加し、別の新rootで続行。Python依存・既存lock・システム設定を変更していない。配布archive/binary/Licenseのhash・原文をcacheへ保存した。
- 7-Zipの全体検査はexit0/Everything is Ok。ただし `There are data after the end of archive` の警告がある。宣言Physical Size合計と原本長との差33,662 Bを切り落とさず保持し、解釈対象を列挙されたmemberに限定。CRC合格を「警告なし」「末尾全bytesの意味を認証」とは呼ばない。[全検査stdio/exit](../../artifacts/macos-industrial-xjtu-7zip-test-20261016-records/root-closed.json)。
- 既存Torchを使うMetro入力の読戻しでNumPy未導入warningが出た。tensor専用経路でexit0、stderrを保存した。追加installで既存環境を変えていない。

## 独立した読戻しと資源

[読戻し結果](../../artifacts/macos-industrial-readback-20261016/summary.json)は28root・164fileのbytes/hash/closureを確認し、成功と旧失敗のstatusを保持。原本全6RARのhash、生成入力、全stdio/exit/sourceの保存記録を検査した。Metroの既存入力adapter、油圧の形状/label分離、XJTUの3完全系列と8特徴量/有限性/時間順がpass。

Metro変換7.91秒、油圧5.62秒、7-Zip全体CRC26.90秒、XJTU fallback準備127.26秒、独立読戻し7.76秒。各親900/子870秒内。読戻しの親監視によるchild peak RSSは231,325,696 B、sampled footprint188,613,424 B。自己計測との差を混ぜず保存した。各工程の採取値は2GiB未満だが、checkpointはOS hard capや全process同時容量証明ではなく、Windows private bytesとも同じ指標ではない。

## 再利用する入口と現在状態

- [原本source index](../../datasets/manifests/industrial-macos-source-index-20261016.json)から公式URL・各原本hash・cache位置を確認できる。
- Metroは既存 `load_fixed_day`、油圧は新 `hydraulic_window`、XJTUは3本の `Bearing*-features.jsonl` と全RAR member一覧から研究入力を作れる。
- 再取得・再変換をこのclosed rootへ実行しない。新たな対象・変換が必要な場合は別rootと契約で行う。XJTUは互換性失敗を記録したlibarchive版ではなく [7-Zip fallback](../../tools/public-data/macos_xjtu_7zip_prepare.py)を参照する。
- 今回の共通データ準備・入力境界・保存値の確認はMac/Python3.14.8で成功。Windows固有/native受入・OS依存包括suite・クラウド固定file一覧の修正は未実施。
- モデル学習・新予測・精度/異常検知/RUL評価・2015再評価は0。需要の2014以前調整/非悪化条件/同休業mean28/観測と休業相当欠測0仮定の分離、正式holdout/native境界とheartbeat PAUSEDを維持。原本・生特徴量・重みのGit送信、Git push、追加agent、本番採用はない。
