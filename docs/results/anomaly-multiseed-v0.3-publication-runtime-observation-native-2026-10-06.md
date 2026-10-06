# v0.3 writer/fresh readerへのruntime在庫接続（2026-10-06着手）

**clean code `b2a6065f84c916bd32191d16ef2d4003b5a9e559`で、実writer/fresh readerの前後runtime在庫、元handle identity、exit0・回収、親post-exit disk照合がpass。旧e04の5 payload pinを維持し、共有96.187/300秒、別保存checkerもpass。**

保存済み架空入力を使う2公開役の限定試行。生成・50,000 draw再計算・観測readerを起動していない。登録holdout観測payload読取り0、新評価0、追加agent0。正式gate `s4_acceptance_not_frozen`、`formal_permission=false`、正式credit0、全source/runtime閉包・独立S6未完了を維持する。

## 実装と由来

observerに専用 `anomaly-v03-publication-runtime-profile-v1` / `...-observation-v1` を追加。従来のanalysis/audit v1形式は保持し、新2役のrole/operation・entry sourceを区別する。実 `worker_main` のrequest decode後、既存 `_perform` 全体を前後観測で包む。公開・4回のretained count/mapping検証、5 payloadのframing・fresh marker確認、child60秒/512 MiB/log64 KiBは同じ。

callerの任意 `publication_runtime_profiles` はwriter/reader両方の外部raw/pinを保持し、保存control/観測subset/共通outerへ伝播する。共有時計内で現tuple/選択Git sourceを照合し、元request pinを両phaseへ結ぶ。親はPopenの元handle identityとstdout・両phaseを照合し、exit0/回収後にsource・全stdlib・loaded disk bytesを再確認する。公開後はprofile/stdout/phase rawを再読取り。checked欠落やpin差替えは保存/outer工程ともfailedになる。

限定実機入力の数値由来は旧 `02d567fc23603c661af78329489617916367b155`。worker codeは新 `b2a6065...` と別欄で固定し、旧数値のsource revisionを書き換えていない。e04 result 37,804 B / `b0379ab5f978d93ee4b3b5bd2352477fffbe2024bd4ea5ea593f5c54e3e4ee63`から旧writer request 8,097 B / `041d7e1c0ce33675cacd92b71cdf6ebf412d62f876acac2bf7deedc46594ac04`を結び、11入力をpin付きで新rootへコピーした。数値sourceとworker sourceを明示的に区別するfixture経路で、正式campaign認証ではない。

実ロードproject・入口・凍結config/schema/plan/workflowの**75 source**を開始前にGit tree blobとworking bytesへ照合。profileのstdlibは**2,559 file /51,017,552 B**、native候補47、cache候補141。準備31.780秒は共有時計外。cache使用・途中load/unload・memory内code・外部Git/helperの完全在庫は認証しない。

## native結果

| 項目 | writer | fresh reader |
| --- | ---: | ---: |
| PID | 8368 | 27488 |
| owned child経過秒/上限 | 45.365 /60 | 19.426 /60 |
| peak private bytes | 74,137,600 | 72,433,664 |
| 終了 | exit0・回収・元handle一致 | exit0・回収・元handle一致 |
| loaded file前/後 | 332 /332 | 332 /332 |
| module前/後 | 217 /217 | 217 /217 |
| native image前/後 | 47 /47 | 47 /47 |

loaded内訳は各phase project59、stdlib85、native39、extension8、cache候補141。全stdlib disk2,559件とは別。workerのPID/creation time/start tokenを親の元handleと照合し、fresh readerはwriterと別PID/token。Windows11 Pro26H2/build26300/UBR9457、CPython3.14.0の候補tupleを維持した。

共有clockは**96.186969/300秒**、381 samples、parent peak108,064,768 B/512 MiB、最大root11,748,424 B/96 MiB・46/128 entries・depth2/5。commit最低余裕6,932,602,880 B、RAM最低8,342,609,920 B、disk最低342,951,432,192 B。stop/errorなし、sampler joined。sampling/checkpoint監視でOS hard quotaではない。全4役・全7役・最終正式全工程の予算合格ではない。

## 試験・保存・失敗保全

焦点11 module・固有132件は**622.398秒、fail0/error0/skip0、対象19 source/test/scientific pin前後一致**でpass。新13件とouterへの両候補伝播/checked・pin拒否を含む。先行70件/45.141秒、接続23件/1.846秒はこの132件へ重複するため加算しない。repository safety pass。実機試行中のtracked file編集は0。

rawは [runtime02](../../artifacts/anomaly-v03-preformal-saved-row-document-budget/trial-20261006-runtime02/)・[helper/checker](../../artifacts/preformal-publication-runtime-20261006-prep/)へ保存。別stdlib checkerは40保存raw pin、75 source raw、2役元handle identity/token、4 phaseのprofile/request/stdlib概要とloaded metadata、5公開payload/markerを照合してpass。stdlib/DLL raw再hashや算術再実行はchecker自身では行っていない。

初回runtime01はhelperのretained入力tupleをJSONへ渡して準備停止し、worker起動0。終端記録も同じ型で停止したため、旧helper・13保存pinとlauncher-failureを保全し、JSON listへ直した別trial2/root02で実行した。checker初版は`published/`直下を仮定して停止。実形式`published/payload/`とmarkerへ合わせた別check3で再照合し、旧check2とsaved-check-failureを保全した。product code・上限を変えてnativeを反復していない。

| raw | bytes | SHA256 |
| --- | ---: | --- |
| result | 30,231 | `43fc6d802892056d4c4b3744a988979dda4f14715c59091b8ca60762c13207da` |
| source-manifest | 10,473 | `e81a9dd587eae6069cca912a78658815f733ed2f6d01c475caf13520bacc9b39` |
| resource-budget | 4,267 | `9956b37377ded5fbb09ac2ac81c0f889d03882bb0235326049de695616822e29` |
| saved-check | 1,092 | `2f23548968a468ec159d6c24b815274a8845ed0e23b15d1fddd387aabb2f555c` |
| focused.json | 22,084 | `5a731b8014b4ea78551a801deb6f4c37c9ed12ace786437c4dabee79c9eeea35` |
| trial2.py | 9,671 | `c7f07b76591ff0f9f9c2137242cf3d1c4b86b80fd8c03626ffed8179b866fbe8` |
| check3.py | 6,823 | `dbd8bb666044e7fd887a03f0294174510a01092581b933a2a331713c54066822` |

## CIと次の残件

前保存点 `eebfa8095698f10366563eed9f4f6ba388b81131` の [CI37436807053](https://github.com/tyaro/banto-ai/actions/runs/37436807053) は全3job成功。両minor各3,026件・fail0/error0/skip237、共有29 fixture/必須28試験pass。10 rawを保存しローカルverifierとremote回帰結果が一致。[complete-summary](../../artifacts/ci-diagnostic-37436807053/complete-summary.json) 2,591 B / `f8be9f42573013dc5d2ede205700ee08ef8e78f9073323f07a79ed7458d3aabe`。3jobのrunner logはUbuntu24.04 /20260927.320.1、digest未取得・採択false。新b2a6065の結果へ代用しない。

次はproducer・初期reader・保存readerのruntime実境界、外部program/Git在庫と異常子孫回収を接続する。analysis/audit＋writer/fresh readerの任意profileは共通callerまで実装済みで、新4役/全7役のnative通しは未実施。正式consumer、版付き運用契約・runner同定、最終同revisionのLinux/Windows・正式dev8/smoke2・独立受入、全容量2倍は残る。[受入案v3](../anomaly-v03-s4-acceptance-scope-draft-v3.md)の5条件を維持し、旧成功/失敗rootを保全する。
