# v0.3 bounded Git receipt archive部品（2026-10-07）

## 保存点と実装範囲

code `1159b9ace9ea7e213033ecaa0ac0b9ee680f67b8` をoriginへpush済み。[archive](../../src/banto_ai/anomaly_v03_preformal_git_receipt_archive.py)は新しいexclusive `git-blobs.bin` に、verified private Jobのsource blob stdout/stderr/receiptをbounded gzip recordとして追記する。stdout原文の重複は先行record参照に集約し、receiptは各実callについて保存する。同一元process identityの再利用を拒否する。

新部品内の上限はfile512 KiB /record128 KiB /展開JSON1.5 MiB /stdout1 MiB /最大512call。gzipの多重member・trailing data・展開超過、frame gap/重複/欠落、順序・phase・revision/path/pinの差替えを拒否する。receipt rawのgzipにも16 KiBの展開上限を適用する。既存outer1 MiB /32 entry /depth2 /reserve128 KiBを変更していない。

`lookup` は同phaseのrevision/path/raw pinが一致する保持済みbytesだけを返す。phase跨ぎのhitは作らず、postflight後のpreflight読取りを拒否する。cache miss/hitともheld archive bytesとpolicyを再確認し、checkpointの前後stopを伝播する。cache hitについて新しいprocess終了を主張しない。

append/readback/fsync/checkpoint/最終保存検証の失敗はwriterをpoisonし、rawを残して後続append・snapshotを拒否する。fsync失敗時にはindex未確定のtailも削除しない。readerの元handle/未回収Job保全は、実executorの次の接続単位で扱う。

[owned Git](../../src/banto_ai/anomaly_v03_preformal_owned_git.py)のretained receipt検証を共通化し、directory版とarchive raw版に同じargv/env/exe/出力pin・Windows creation identity・Job active0検証を使用する。Job formatは保存先OSにかかわらずWindows identity形式を確認し、既存direct POSIX形式は維持する。

source allowlistは従来srcに加えて、現在の親source在庫で使う次の5 toolだけを明示追加した: `preformal_owned_generated_trial.py`、`preformal_saved_row_reread_trial.py`、`preformal_contiguous_document_budget_trial.py`、`preformal_bound_document_trial.py`、`preformal_bound_slice_trial.py`。他のtools、絶対path、traversal、revision/pin差替えは許可しない。

## 焦点試験と保持した失敗

4 test moduleの54件（archive専用19＋既存35）を15.692306秒で実行し、fail0/error0/skip0。対象source/test/science10 pinは前後不変、safety PASS。既存real Git roundtripを含む回帰試験であり、新たな全工程nativeや専用native試行ではない。

追加19件は原文共有と個別receipt、directory/raw verifier一致、argv/source/Job停止/正式flag差替え、file/frame pin・欠落・参照・gzip bomb、file上限、stop時元exception、readback/fsync失敗raw、call/process identity再利用、phase逆行、cacheのrevision/path/pin、明示5tool allowlist、同phase共有による現在在庫の保存を扱う。

初版の47件passは後続改訂前の履歴。`focused-v2` はsrc限定allowlistでtool sourceを拒否した失敗、v3/v4/archive-only-v5は全218call保存が512 KiBへ達した失敗を保持。重ねた試験数を加算しない。`sizing-cap-stop.json` は170件/523,242 Bで止まった仮receipt診断でありnative failureではない。

## 保存したprotocol fixture

現在の44＋65 source loopを前後phaseで要求すると218読取り。その同phase重複をcacheし、仮の130 receipt、88 hit、unique stdout65へ集約した。保存archiveは472,003 B。先行の一時fixtureは471,876 Bで、root文字列等のfixture差がある。

ここではprocess identity/Job factは明示的に合成し、policy observationはstubである。実Gitを起動しておらず、native peak・実exe証明・formal容量2倍・実経路受入ではない。保存fixtureはnative証拠と区別した専用名とindexで保持する。別の保存照合は130 record/65 source、Git/Job API起動禁止でpass、policy stubのまま。

rawは `artifacts/preformal-git-receipt-archive-20261007-prep/`。

| 保存物 | bytes | SHA-256 |
| --- | ---: | --- |
| focused-final.json | 1,673 | c6afdeb547183074270bbef800b661793798817a350399a096a2294366c0cc55 |
| focused-final.log | 10,429 | d4c4a14a2633d6cb589be637f84c93d07b13cff1aa727764061714c810379e1a |
| sizing-cached.json | 1,194 | 8766132825578f2b565a98b03467c83c58e1db2e7bc8e1052c3d942e20e78e8e |
| synthetic-phase-cached-archive.bin | 472,003 | b90540763c9a792481886140b7aa7165751e07428f1f5f3e20d6e1e8908cbb4f |
| synthetic-fixture-index.json | 53,324 | f288851cc49168864f8b5b4c2fec17fba60838643db3156fd079f6a5f024c510 |
| synthetic-saved-check.json | 654 | de454581092f5eba433e6431131fd121a14c00cb54940e23b281f81779babfb5 |
| code-save-checkpoint.json | 755 | 3d02e4f6ccf09c48c915463e76ced1438555a749ab7ddf3558bdb0d3e7a7c305 |

code-save checkerはclean HEAD=origin1159b9a、3 raw/10 working/Git source/test/science pinを照合した。SOURCE_NAMESの現65 fileはarchive自身をまだ含まない。実接続時にactor/archive/loaderを選択在庫へ加え、期待値を新clean HEADへ固定する。

## 次の接続とCI

production callerはまだarchiveを使わず、blob Jobの元handle/shared stop接続・inflight rawの保存/再検証後整理・実root予算観測は未実装。次は親blob callbackへpolicy/phase cache/元Job handle/shared budgetを結び、成功archiveのraw readback後にその新しいinflight stdout/stderr/receiptだけを個別に整理する小さい単位。失敗・未回収時は元handleとinflight raw/partial archiveを保持し、後続Git/workerを開始しない。旧raw/pin/rootは整理対象外。最終source inventoryと正確なpre/post call inventoryを終了時照合する。

その接続後にclean HEADの限定親Git nativeを行い、outer既存上限内の実peakと全Job終了を確認する。全7役343c863・親4 Job9ddaed7を反復せず、新保証/契約の採択や正式データ経路に読み替えない。

CI37568898031（HEAD9af4a96）は3.14 success・3.12進行中。新CI37570913852（HEAD1159b9a）はin_progress。各完了後にrun/attempt別10 raw・local regression・runner v2を同HEADへ固定して保存する。文書だけの追補はskip ciを使用する。

人の「しばらく自走、止めるとき割り込み」に基づきheartbeat `banto-10` は期限なしACTIVEへ更新済み。追加agent0、次回は本引継ぎから再開し、完成したarchive部品・既存nativeを反復しない。モデル容量エラーまたは停止指示では保存・安全な終端後PAUSED。`s4_acceptance_not_frozen`、formal false、credit0、holdout観測未読と[正式5残件](anomaly-multiseed-v0.3-preformal-evidence-index-2026-10-07.md)を維持する。
