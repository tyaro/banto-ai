# v0.3 全7役の runtime 接続・共通予算限定実機確認（2026-10-07）

## 状態と範囲

clean code `343c8639b0acfb2be535c02b5aaf4288b8f3d43e` で producer → initial-reader → saved-reader → analysis → audit → writer → fresh reader を同じ外側予算で一度通した。全7役の元process handle identity、14前後phase、外部profile/input pin、終了・回収、親post-exit disk照合が成立した。

対象は **架空1区間・22 payload /131,144,118 B** と **479区間の架空metadata**。6評価の実観測再導出と、40 cluster /50,000 draw の架空主算術・別算術監査・全文書・slice・5 payload公開を接続した。登録全480区間の観測確認、正式全工程、完全S6ではない。登録holdout観測未読、正式credit0、`s4_acceptance_not_frozen`、`formal_permission=false` を維持する。追加agent0、長い全工程trial1回。

## 今回の実装

producer/initial-reader に専用 `anomaly-v03-generation-runtime-profile-v1` / `...-observation-v1` を追加。実生成・保存・読戻し、実初期読取り・再導出をそれぞれ一度だけ前後観測で包む。従来の源データ・snapshot・出力pin検証、限界と停止保全を維持する。

任意 `generation_runtime_profiles` は2役のcaller raw/pin・role/root/full revisionを保持し、両候補を起動前に検査する。実共有時計内で各役のselected Git source/runtimeを照合し、exclusive保存したprofileと全invocation pinを実入口へ渡す。親は元handleのPID/生成時刻/start tokenとchild receiptを、exit0/回収後に照合する。両役終了後と全文書公開後にprofile/invocation/stdout/phaseを再読取りする。checked欠落・false・profile pin差替えはouterもfailed。legacy callerは未要求runtime receiptを拒否する。

算術・公開・saved-readerの旧v1形式は保持。両source snapshotは合計58,399 Bで、既存64 KiB上限内。code保存後のnative稼働中にtracked編集は行っていない。

## 試験と準備

焦点9 module・固有 **108件 /14.067秒、fail0/error0/skip1**。skip1は既存の明示実機試験。対象15 source/test/science pin前後一致、repository safety pass。先行12/26件は重複するため加算しない。新試験の初版は模擬payloadを既存saved/run-root在庫の外へ置いたため2 fail/1 error。配置だけを修正し、初回の件数・原因を保存した。製品の在庫検証は変更していない。

期待22出力manifestの独立計算 **223.296秒**、runtime候補準備 **23.737秒** は外側時計外。callerの選択source **103 file**をGit tree blobとworking rawへ照合し、全stdlib **2,559 file /51,017,552 B**、native候補47、cache候補164を固定。同じcaller観測を役割・operation・entry source別の7候補にする。各実childが自分の前後境界で照合し、親観測でchild観測を代用していない。

## 同一revisionの実機結果

| role | PID | wall秒 /上限 | peak private B /上限 | loaded file/module/native（各phase） |
| --- | ---: | ---: | ---: | --- |
| producer | 33992 | 159.150 /360 | 362,385,408 /768 MiB | 318 /209 /47 |
| initial-reader | 2612 | 60.663 /300 | 319,086,592 /1 GiB | 312 /206 /47 |
| saved-reader | 18632 | 63.232 /300 | 319,565,824 /1 GiB | 324 /212 /47 |
| analysis | 41128 | 67.451 /900 | 129,552,384 /1 GiB | 324 /213 /47 |
| audit | 37304 | 131.146 /900 | 41,156,608 /1 GiB | 324 /213 /47 |
| writer | 34960 | 21.642 /60 | 73,441,280 /512 MiB | 332 /217 /47 |
| fresh reader | 17560 | 17.384 /60 | 72,024,064 /512 MiB | 332 /217 /47 |

全7子 exit0・回収、PID/creation tokenは7組で別、stop/観測errorなし。before/after loaded rowsは各役で維持。cache候補の使用、途中load/unload、memory内code、外部Git/helperの完全在庫は認証しない。

外側 **690.575556 /1,800秒**（helper呼出690.898674秒）、内側 **352.930751 /1,200秒**。外側3,527 sample・内側2,262 sample、sampler/monitor joined。親peak **288,358,400 B /512 MiB**、4 root最大 **146,895,582 B /321 MiB**・125 /672 entries・depth10 /12。最低commit余裕9,475,207,168 B、RAM空き9,471,283,200 B、disk空き313,311,404,032 B。既存cap/floorを変更していない。監視はsampling/checkpoint方式で、正式同形容量2倍の受入ではない。

公開後に外部control4,800 fileとindex、生成元22 payload、subset control、7役profile/phase、source/runtimeを外側時計内で再照合した。公開・行投影・slice/countの整合が成立し、4組のruntime checked（generation/saved-reader/arithmetic/publication）はすべてtrue。ただしformal/source/runtime閉包・独立S6のflagsはfalse。

## 保存再検証

別stdlib runtime checkerは **57 raw pin・103 working/Git source・7元handle identity・14phase**、caller profile/input/stdout、stdlib概要とloaded file metadata、終了・共有予算を照合してpass。別集計checkerは **4,974 raw pin・60 selected source**、全count/histogram/slice、全文書・5公開payload/marker、control・元22 payload、全7子終了と予算を検証してpass。両checkerのrawは重複し、件数を合算しない。

checker自身はstdlib/DLL raw再hashやprofile/score/bootstrapの再実行をしていない。集計checker初版は旧e04 root名の残存で停止した。原scriptと失敗を保全し、別v2でroot名を修正して保存証跡だけを再検証した。nativeを再試行していない。

rawは [準備・実行・checker](../../artifacts/preformal-generation-runtime-20261007-prep/)、[outer](../../artifacts/anomaly-v03-preformal-generation-publication-20261007-r7/)、[producer](../../artifacts/anomaly-v03-preformal-registered-attempt-r7/)、[saved-reader](../../artifacts/anomaly-v03-preformal-saved-row-reread-20261007-r7/)、[publication](../../artifacts/anomaly-v03-preformal-saved-row-document-budget/trial-20261007-r7/) にローカル保存。

| 証跡 | bytes | SHA-256 |
| --- | ---: | --- |
| outer result.json | 25,932 | `2a6c73b5fb74021567dd5c764bc431ab359bfe7e5e92fcaa38cb82ced19e4e9f` |
| publication result.json | 42,059 | `c954a5f484b8e7c73ec8dc74ef437309b289a6a7751e6410d4b9488c47df7032` |
| execution.json | 877 | `32b6e6dc4e5d377824a852e4218d32c78a1a472ff21d59224547b22f2e9396a0` |
| runtime-check.json | 13,424 | `bc9efceef3c8c106b092a043426fa7e4566364b3310518b3e1adb231c9ce9231` |
| postcheck.json | 869,054 | `38fda67061dee5090960bdec9aa72ad7329b68a31e6e99c0d69cc7a91d950289` |
| focused.json | 18,438 | `9630fabc9a984c455c4c3de6d9ede1d93f5e0c778cb9f87fa410fe4d44fb8cd4` |

## CI・runner・残件

先行saved-reader保存点 `3d2ebfb` の [CI37498814612](https://github.com/tyaro/banto-ai/actions/runs/37498814612) は全3job成功、両minor各3,051件・fail0/error0/skip237、共有29 fixture・必須28試験pass、10 raw保存/local verifierとremote結果一致。新343c863のCIへ代用しない。

直近CIで実際に現れた Ubuntu image版20260927.320.1 /20261004.327.1の公式releaseと同tag READMEを外部raw pinで保存し、版一致を確認した。稼働VMのdigest取得・代替規則の採択・独立受入ではない。

実行時在庫の接続は全7役まで進んだ。残るのは、実使用の外部program在庫・異常時子孫回収、26H2/保証A/runner代替同定を含む版付き契約採択、登録予定全inventoryを扱う正式入力/consumer経路の受入、最終revisionのLinux/Windows・正式dev8/smoke2・独立受入、analysis/追加audit/staging/診断を含む全容量2倍。S4採択後にS5未使用holdout40 seed、S6独立再導出、S7報告へ進む。
