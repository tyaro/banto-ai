# v0.3 saved-reader の実行時在庫接続と限定実機確認（2026-10-07）

## 範囲と状態

code保存点は `799145aec0d56265e66d4bdec18bae65400c1307`。clean同HEADで既存の架空e04入力を新しいowned saved-readerが読み直した。旧payload由来は `02d567fc23603c661af78329489617916367b155` と別に保持した。生成・50,000 draw再計算は0、登録holdout観測payload読取り0、追加agent0。6評価は旧架空観測からの再導出で、新しい正式評価・正式creditではない。

正式gateは `s4_acceptance_not_frozen`、`formal_permission=false`、正式credit0。source/runtime閉包・memory内code・途中load/unload・外部programの完全認証、正式契約採択、独立S6は未完了。

## 実装

専用 `anomaly-v03-saved-reader-runtime-profile-v1` / `...-observation-v1` を追加。既存childのpayload再読取り・profile/score/ledger再導出を一度だけ実行し、その前後で全stdlib・実loaded import/拡張/DLL/cache候補とsourceを外部pinへ照合する。算術・公開役の既存v1形式は保持する。

任意 `saved_reader_runtime_profile` はcallerのraw bytes/pin、role/root/full revisionを新root作成前に保持する。共有時計内で現tuple・selected Git sourceを照合し、profileをexclusive保存して全invocation pinを両phaseへ結ぶ。親は元Popen handleからのPID/生成時刻/start tokenとchild receiptを、正常終了・回収後に照合する。source・全stdlib・loaded disk bytesのpost-exit確認、行投影後のprofile/invocation/stdout/phase再読取りも同予算内。

共通generation→publication callerへ同引数を伝播した。saved-readerのchecked欠落・pin差替えは外側もfailed、公開後にsaved-reader証跡を再読取りする。今回、共通全7役のnative通しは実施していない。legacy reader routeも未要求のruntime receiptを拒否する。

## 検証結果

焦点5 module・固有60件は **6.191秒、fail0/error0/skip0**。対象10 source/test/scientific pin前後一致、repository safety pass。先行48件はこの60件へ重複するため加算しない。pin/role/revision/selected Git不一致、生成時刻偽装、終了後・投影中のphase変更、未要求receipt、失敗時のbefore/failure保全、outerのchecked/pin拒否を含む。

実機準備は **10.155秒、予算外**。選択source **103 file**をGit tree blobとworking rawへ照合、全stdlib **2,559 file /51,017,552 B**、native候補47、cache候補164を固定した。実childの各phaseは **324 file /212 module /47 native**、途中追加なし。cache候補は実使用の認証ではない。

| 確認項目 | 結果 |
| --- | --- |
| saved-reader PID | 31068 |
| 元handle生成時刻 | 134357785957092477（100ns） |
| start token | `183653839d1d2b5596155fed4dbc1f7aaba7c4babaa2b4a914fa69121ad73acc` |
| child wall / 上限 | 59.090132 /300秒 |
| child peak private / 上限 | 319,332,352 B /1 GiB |
| exit / 回収 | 0 / confirmed、観測error・stopなし |
| 外側呼出wall / root予算 | 77.398825秒 /120秒（最終resource sample 77.338407秒） |
| parent peak / 上限 | 107,823,104 B /512 MiB |
| 監視中最大root | 913,004 B /32 MiB、10 /256 entries |
| commit最低余裕 / RAM最低空き | 4,587,220,992 /8,985,812,992 B |
| disk最低空き | 344,094,281,728 B |
| monitor | 330 samples、joined、stop/errorなし |

child上限は元の `copied.READER_LIMITS`（300秒/1 GiB/log1 MiB）、root上限は元の120秒/32 MiB。変更していない。資源監視はsampling/checkpoint方式。保存元の22 payload /131,144,119 Bを最終再照合し、6評価のreader_resultと行投影116,085 B / `0bf7823d60212f8003976b530392e8c5f39063fe216aa057de35cd5b387c0f6e`は旧e04と一致した。

別stdlib checkerは **41保存raw pin・103 current source raw・旧22 payload raw**、profile/全invocation/両phase/元handle identityの保存binding、exit・予算・旧reader/行投影一致を照合してpass。checker自身はstdlib/DLL raw再hashや数値再実行を行っていない。実機試行中のtracked編集0、native worker・monitor・checker・試験は終了済み。

## 保存証跡

rawは [実機root](../../artifacts/anomaly-v03-preformal-saved-row-reread-20261007-runtime01/) と [準備・試験・checker](../../artifacts/preformal-saved-reader-runtime-20261007-prep/) にignoredのローカル保存。Git pushにはrawを含めない。

| ファイル | bytes | SHA-256 |
| --- | ---: | --- |
| native-summary.json | 2,822 | `18386c89e119cfdb43ff512b101deaffe933033311ba1f7bfcd0c62faa1b383e` |
| saved-check.json | 10,608 | `1440ea9987b44a96262124eb7a2dd17f8c3963d2908cd8d09a73743efe4cc902` |
| result.json | 12,199 | `784495649232d820aa467a91982e2b80f7c0c01808c5d9d61e3f4ab517de74d8` |
| resource-budget.json | 1,703 | `0aac8c11dcd65dca4d74efef09088ad9e6d320af501ef95308f05fac287e0f56` |
| candidate-profile.json | 385,106 | `b9b870e60105509cd5f97f2668b90dd628b12ac21846a885217571458057d3b2` |
| source-manifest.json | 14,570 | `293a547175e1f3c637f4d30d0104195572c3d687db357f21c7d1c7eecd82fbae` |
| focused.json | 10,543 | `b7d8b0efd482fdb2d2cbc61bc21d02050572c20541db3ce12a36d7f26b756bed` |

## CI と次の作業

前保存点 `97370f3a355a60c3e8650325a2c1559a7aff1763` の [CI37485069436](https://github.com/tyaro/banto-ai/actions/runs/37485069436) は全3job成功、両minor各3,039件・fail0/error0/skip237、29 fixture一致・必須28試験pass。10 raw保存、外部HEAD/workflow/run/attempt固定のlocal verifierはremote結果と一致。新saved-reader codeのCIには代用しない。

runner log版はtest2job `20260927.320.1`、compare `20261004.327.1`。旧版固定の集約helper失敗を保全し、別v2で各logの実版を採取した。image digest未取得・正式採択falseを維持する。

残る実行役割は **producer・initial-reader**。次に両役の実境界・caller pin・元handle・共通予算接続を進め、その後に同じrevisionの全7役nativeを確認する。外部program在庫・異常子孫回収、運用契約/runner同定採択、最終Linux/Windows/dev8/smoke2・独立受入、正式同形全容量2倍も残る。S4採択後にS5未使用holdout、S6独立再導出、S7報告へ進む。
