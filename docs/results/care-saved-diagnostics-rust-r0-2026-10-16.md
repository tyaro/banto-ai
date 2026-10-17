# CARE保存予測の未検知分析とRust R0

配置の追補（人の訂正）: AI本体のRustクレートはbanto-ai側、banto-industrialは利用・接続先。以下の「移植先」は接続先を指す。[現行R0契約](../research/rust-small-forecaster-r0-2026-10-16.md)を優先する。CARE結果・数値条件は不変。

状態: 保存値分析・公式source/接続先確認・R0契約固定まで完了。新しい学習/forward、Rust compile/統合は未実施。2026-10-16 JST。

[計画](../research/timesfm-inspired-practical-evaluation-plan-2026-10-16.md)に従い、[前回のCARE r1結果](care-macos-learning-evaluation-2026-10-16.md)を固定したまま、全12異常区間・10正常fileを分析した。[R0詳細](../research/rust-small-forecaster-r0-2026-10-16.md)と[機械契約](../../examples/configs/rust-small-forecaster-r0-20261016.json)を保存した。

## 未検知9件の機械的な内訳

分析前に「支持なし/超過なし/3連続に届かない/区間前から警報active/要追加確認」を固定し、保存した元score・閾値・警報・truth区間で区分した。

| event | asset | 元の検知 | 閾値超過点 | 最長連続 | 最大score/閾値 |
| --- | --- | --- | --- | --- | --- |
| 68 | A:11 | 未検知 | 4 | 1 | 1.37026 |
| 22 | A:21 | 未検知 | 0 | 0 | 0.95000 |
| 72 | A:21 | 未検知 | 2 | 1 | 1.06869 |
| 73 | A:0 | 検知 | 7 | 5 | 1.88408 |
| 0 | A:0 | 検知 | 14 | 6 | 1.35616 |
| 26 | A:0 | 未検知 | 4 | 2 | 1.45194 |
| 40 | A:10 | 検知 | 15 | 6 | 1.73400 |
| 42 | A:10 | 未検知 | 3 | 1 | 1.14454 |
| 10 | A:10 | 未検知 | 3 | 1 | 1.18810 |
| 45 | A:13 | 未検知 | 2 | 1 | 1.09445 |
| 84 | A:13 | 未検知 | 2 | 1 | 1.32173 |
| 51 | A:21 | 未検知 | 2 | 1 | 1.06869 |

**8件は超過が3連続にならず、1件(event22)はcommon支持で超過しない。** 元の3/12検知は変わらず、今回の集計で「支持なし」や未説明分類へ落ちた異常区間は0。これは固定警報機構のどこでOPENに至らなかったかの説明であり、物理的な故障原因やモデルの未検知原因を特定したものではない。既読testに合わせて連続回数/閾値を緩める根拠にはしない。

## 正常誤警報とasset差

NN正常falseは元どおり3回。A:21のevent13に2回（ordinal50715/51451、3,000/2,400秒）、A:11のevent92に1回（53514、3,000秒）。A:21は同じ正常fileでcommon/native baseline各1回に対しNN2回という悪化を保持する。

各NN OPEN時のNN score/閾値は1.13414/1.17314/1.09487、baselineは0.86207/0.79310/0.60714で、その時点のbaseline警報はinactiveだった。3時点ともNNの温度絶対誤差はbaselineより小さい。それでもmethod別の校正閾値が違うため警報差が生じる。予測絶対誤差だけで誤警報の良否を説明しない。閾値校正の挙動は次の未知データ設計で検討する仮説として残し、現testで再校正しない。

各異常区間の温度誤差・NNとbaselineの予測差・片方だけ超過した点数も保存した。A:0/10以外の3assetは検知0であり、pooled平均の改善を全assetへ一般化しない。

## nativeだけがevent22を検知した意味

native baselineのOPEN ordinal52632/52659はいずれもflags12で、NN発行/common支持なし。過去128点内にgap52619がある。したがってcommonに限定した比較ではnative側のこの利点が消える。

ただしevent22の**common支持内でもNN最大scoreは閾値の0.95倍**だった。可用性差だけでこの未検知全体を説明し切らない。native支持50,560点/common47,834点の元報告を保持し、支持床・欠測処理・評価母集団を変更しない。

## Rust R0と正しい接続先

人の指定で接続先を[tyaro/banto-industrial](https://github.com/tyaro/banto-industrial)に確定。main commit93d99efa…の19+4 sourceを取得し、全Git blob一致を確認した。ScadaProjectは除外し、対象repositoryには変更していない。

最初のR1候補はBurn=0.22.0/Flex CPU＋autodiff。native Rust1.95.0の直接起動は確認済み、標準Intel rustup shimは起動不可。対象banto-industrialは1.98.1固定なので、研究coreの成立と製品pin上の統合を分ける。Cargo.lock/依存license全件/compile/数値同等性は次工程。

対象の実型はValueEntry/ValuesSnapshot、bindingは外部名。画面履歴のmin/max envelopeを学習値にしない。raw履歴だけでは品質やsource時点/availabilityを復元できず、正常と捏造しない。共通forward/AdamW/中立package/再開/数値許容差と、jobを収集周期から分離する接続条件を[R0詳細](../research/rust-small-forecaster-r0-2026-10-16.md)に固定した。CARE匿名信号の実機対応、Rust移植成功、業務導入を認定するものではない。

## 実行と保存

| unit | exit | 親経過秒 | 子peak RSS B |
| --- | --- | --- | --- |
| 保存予測分析 | 0 | 0.419 | 80,592,896 |
| 公式backend/toolchain監査 | 0 | 4.371 | 31,899,648 |
| banto-industrial 19 source確認 | 0 | 7.885 | 30,113,792 |
| binding/handle/clock/reader 4 source補足 | 0 | 1.658 | 29,753,344 |

各親900/子870秒、self/親sampled physical footprintとpeak RSS各2GiB内（分析self footprint最大68,190,760B）。OSによるhard memory capではなく観測値である。rootごとにsource/phase/stdout/stderr/exit/resource/closureを保存。

- `artifacts/care-saved-diagnostics-20261016` と同 `-records`
- `artifacts/rust-r0-source-audit-20261016` と同 `-records`（旧未確認candidateの記載は履歴、本R0ではScadaProject除外）
- `artifacts/banto-industrial-r0-intake-20261016` と同 `-records`
- `artifacts/banto-industrial-r0-supplement-20261016` と同 `-records`

初回publicationは独立数値検算後、既存文書の `ファイル名:行番号` 付きリンクを検査器が欠落ファイルと誤判定してexit1。学習/forwardは0で、失敗root `care-rust-r0-publication-20261016` と元文書全文を含む `care-rust-r0-final-20261016-evidence` を保持した。検査器を対応させたfresh publication2で元root/参照SHA、別方式の連続超過集計、機械契約の整合性と文書45リンクを検査し、旧文書全文/新source/stdio/exit/状態を `artifacts/care-rust-r0-final2-20261016-evidence` に保存した。そのEvidenceStoreはcompleteだが、直後のreadbackがpartのfieldをnameと誤記しexit1になった。元数値検算や保存内容の失敗ではない。3回目は既知のfailed記録を成功専用validatorへ渡して拒否された。3件のfailureを保持し、fresh publication4で正しいpath fieldから全part/SHA/元rootの不変を検証した。最終状態と文書の前後は artifacts/care-rust-r0-final4-20261016-evidence に保存。旧closed root/失敗を保持し、artifact/EvidenceStore/part/失敗reserve上限を維持した。

Mac共通経路は上記読取り・保存値分析を完了。Windows native、OS依存包括suite、Windows向けtstore clock/サービス/keyring等の受入は未実行。新しいmodel forward/実学習、CARE性能再評価、需要2015、新データ取得、依存install、外部研究data送信、Git push、本番activation、追加agentは0。公開sourceのGETは実施した。需要の調整2014以前・同休業mean28・四季平均の過小/過大非増加・観測/欠測0評価分離とheartbeat PAUSEDを維持する。

次はR1の孤立Rust coreと固定参照による数値比較。履歴の品質・時点不足を解消する製品adapterは別の受入工程とする。
