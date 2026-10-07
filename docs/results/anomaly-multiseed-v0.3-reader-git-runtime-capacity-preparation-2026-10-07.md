# initial-reader runtime候補と容量準備（2026-10-07）

後続の[保持順と失敗stdoutのサイズモデル](anomaly-multiseed-v0.3-reader-git-coupled-peak-plan-2026-10-07.md)では、全pending単純加算を通常ピークとせず、正常schemaモデル786782B/31entryを整理した。失敗stdoutの既存1MiB保持はreaderだけ1704030Bとなり、capacity/native許可は未完了。以下はこの準備時点の原記録。

対象clean HEADは `be0309561ad385c51bd2f865e6d8bd38a428038f`、業務codeは `a12c3e91883d9e79fadbdd8f4b23b06f02add2ff`。専用保存先は `artifacts/preformal-reader-git-runtime-20261007-01/`。native開始0、完成済み試験・全7役・旧rootの反復0、上限変更0。

## 保存した候補

- 実準備processで読み込んだimport/image在庫とGit working/blob照合済み117sourceを保存。initial-reader profileはstdlib2559、native候補47、cache候補179。これはcallerの自己観測候補であり、完全runtime閉包・実worker・実exeの認証ではない。
- reader対象は30source、各phase head/status＋30blob＝32要求、予定64Git Job。source総量は各phase493168B、最大source48839B。source追加による64call超過はない。
- Git実行ファイルを新たにbounded hash/identity/linksで観測し、現在revisionの外部private Job policyを保存。policy現物・PATH解決も照合した。GitのDLL/CRT全ロード閉包は未確認。
- `reader-plan-v2.json` は外部path/pin・profile pin・30source pin・revisionを結び、上位の未使用4root検証とplan resolverに通した。rootは作成していない。最初のnested root案は上位root契約に適合しない案としてrawを保持する。
- `call-template.json` は正確な64callの準備形。元shared clock、request pin、実root identity、元worker creation identityは未発行。実native request・launcherは未準備。

| 保存物 | bytes | SHA-256 |
|---|---:|---|
| initial-reader-profile.json | 390207 | `7c6bc8827c89973c446accdac4c945cacb275da758beb34b3cb0534496ae036e` |
| reader-plan-v2.json | 5048 | `f785c97118e31e1a2308246abd08679ff8b740fe1c93f1bdcd515bc85e176022` |
| call-template.json | 21585 | `e88b50e16f34c17ecbdab85661ec5e495c0cf0187bdaceb74fbb4f8ae88b033b` |
| capacity-preparation-v2.json | 2826 | `2b506f174e8a6d8795aea099e2b7123db64a889ca53cacbc593e1d54cf4f583e` |
| preparation-result-v2.json | 2099 | `651bd054ef89ca882cf98a99443d3d02a4e2e0adddaa8d86198c3a2aafcbbb15` |

## 容量の残件

control完成6frame＋各pending、caller inventory、archive、inflight3file、2directoryを計上した保守的なreader上限は1097728B。outerの1MiBからreserve128KiBを残した917504Bを180224B超える。reader19entryに親identity4callの16entryと診断2fileを同時に残す単純計上は37entryで、既存32entryを超える。

これは全pendingや各上限を同時に足した値であり、到達可能な実ピークを測った値ではない。capacity合格とはしない。限定callerの正常時／失敗時の生成・保持順、実controlの最大サイズ、親診断・receipt、archiveとinflightの共存を具体的に固定する。worker archiveのstdout cache/dedupは未接続で、各phaseのsource rawを個別保存する。旧parentの使用済みarchiveへ追加せず、上限緩和や未測定rootへの移動も行わない。

## 失敗と終端

最初の準備はprofile/plan/call保存後、容量表のtupleをclosed JSONへ渡して失敗。元観測とrawを保全した。補完v2はmodule参照ミスで容量計算前に失敗。補完v3は保存候補の照合と容量表だけを完了し、profile/import/image観測を再実行していない。これらを単一の成功準備runに読み替えない。

原helper PID48348/creation134358494804631665、補完35720/134358496384210511、補完32284/134358496612215457はexit1/1/0、各tokenはlive/execution rawに保存。CIM残存なし・critical ownerなし。native0。

文書保存後はHEADが変わるため、この候補を新HEADのnative許可へ読み替えない。次はcoupled peak inventoryと元owner保持付き限定reader launcherを小さく固定し、最終clean HEADに新exclusive request/profile/policy/root pinを準備する。正式gate `s4_acceptance_not_frozen`、formal_permission=false、正式credit0、登録holdout観測未読、正式5残件を維持する。
