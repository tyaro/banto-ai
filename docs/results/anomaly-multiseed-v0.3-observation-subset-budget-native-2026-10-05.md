# v0.3 観測reader部分行と全体fixtureの接続（2026-10-05）

code保存点 `ebdd4b9224ae2ed3a01edb8d410bb4e6d473fda7`。正式gateは `s4_acceptance_not_frozen`、正式許可false、credit0、holdout40未読、追加agentなし。

## 接続した範囲

[専用projection](../../src/banto_ai/anomaly_v03_observation_subset_fixture_projection.py)は、[先行readerで観測から再計算・終了時照合した架空g02の6行](anomaly-multiseed-v0.3-saved-attempt-final-readback-native-2026-10-05.md)を、全480区間metadata fixtureの区間0だけに反映する。残り479区間・2,874評価は明示的な架空metadata行。部分6行を別seed/layoutへ複製しない。

両方の元pin、歴史source、recipe、元metadataの4入力pinとfailed履歴を保持する。全体に一つの歴史sourceを割り当てず、`declared_historical_source_revision=null`。metadataは架空 `a`×40、部分行は生成保存点 `3be274c59ce4ffa0b5b60ba42993e2aa44a57039` のまま。部分receiptの終了時22ファイル照合の宣言、凍結slot、latest attempt、外部10 raw pinを照合し、影響するseed0のprimary分母・profile・delay・slice・coverageを再集計する。以前の同一source/recipeを要求する入口は維持した。

新しい[実行入口](../../src/banto_ai/anomaly_v03_preformal_saved_row_document_budget.py)は、metadataのdisk読取り、部分行の検証／集計、4入力、50,000 draw、別process監査、文書／slice、writerと終了後fresh reader、metadata disk再照合／部分raw再照合を同じ時計へ接続する。部分10 rawのロード、期待pinの準備、実観測reader／producerは時計外。`same_budget_subset_rows_to_fresh_reader_measured=true`、`same_budget_observation_reader_to_fresh_reader_measured=false`、`complete_observation_campaign_verified=false`。

これは固定fixtureでのconsumer接続の証拠で、480区間の観測確認や共通campaign認証ではない。観測payloadを読む新processは今回起動していない。正式bootstrap、正式文書、独立S6、正式同形全工程予算・容量2倍のflagはfalseのまま。

## 検証とWindows実測

専用projection9件（75.088秒）、接続／既存budget21件（4.846秒）、既存同一由来projection11件（147.863秒）は別runでpass。部分変更、外部pin不一致、重複・異なるslot、終了照合未完、正式mode、input上限、公開完了後の部分raw変更を検査した。準備時の旧4入力pin比較で、共通pack処理への整理後も旧入口のbyte結果が維持された。safety・diff checkがpass。凍結計画／registryは変更していない。

clean HEADで新root `artifacts/anomaly-v03-preformal-saved-row-document-budget/trial-20261005-06` を使用。helperは `artifacts/anomaly-v03-observation-subset-budget-20261005-a3/`。旧rootは保持した。

| 測定 | 保存値 |
| --- | --- |
| 共通予算 | 271.835678秒／1,200秒、passed、stopなし、sampler終了確認 |
| parent private最大／新root最大 | 229,478,400 B／512 MiB、10,304,286 B／96 MiB、44／128 entries、深さ2／5 |
| commit余裕／RAM／disk最小 | 14,225,563,648／12,591,439,872／405,656,895,488 B |
| analysis／audit | PID18608／30520、56.920／130.638秒、private125,349,888／29,171,712 B、両exit0・回収 |
| writer／fresh reader | PID36600／17512、13.865／7.347秒、private67,919,872／67,887,104 B、別creation token、両exit0・回収 |
| input byte上限 | metadata129,026,491＋部分349,409＋index690,985＝130,066,885 B／256 MiB。外部入力は新root directory測定外 |
| source/runtime | 40選択sourceの前後・disk/Git一致、26H2/build26300/UBR9457・CPython3.14.0一致。全依存在庫ではない |

部分6行の正当なinconclusiveを保持し、全体fixtureはsuccess2,874・inconclusive6・partial/failed/not_started0。40 cluster、50,000 draw、9算術table、117 primary・72 paired estimate・180 gate、1,233 slice・2,835 diagnostic系列行・9詳細tableを保存した。区間479のfailed attempt1→latest2を保持した。4 workerと3 mapping outputの完了が共通receiptで一致。control-read／reread各483 checkpointのsample/probeを維持し、履歴は各phase1行。

stdlibだけの別checkerは、元480区間controlと部分10 raw、先行checkerに束ねた53 raw（保存22 physical fileを含む）、両由来のslotとpin、全240 candidate/layer cellのprimary・delay・slice集計、文書mapping、公開byte／marker、4終了記録、40 sourceを計4,904 raw pinへ再結合した。先行physical bytesの再読はこのcheckerの時計外。独立50,000 draw再実行やscore再導出、独立S6は行っていない。

## 保存pin

native pathは新root、helper pathは上記a3からの相対名。rawはローカルのGit管理外で、文書pushはraw転送を意味しない。

| 保存物 | bytes | SHA-256 |
| --- | ---: | --- |
| native `result.json` | 37,245 | `18b914fab742ce67d2d73bc8872aa5eaef3d8a23fd9c222d0faa73fa7f6eda19` |
| native `resource-budget.json` | 6,909 | `6514d02fc1f01be1b1a7436c5bdb98a2374e436970410d638e94f11a6db77ed4` |
| native `projection.json` | 1,182,140 | `1c1de121756feba0fd67fd1e7e397fc90b7fa278703d935514087178de6b646b` |
| native `inputs/input.json` | 203,731 | `97989bd8037a07eb4536598e86014d4d43f69bfda3dd83fd82f93ab1c8ba8649` |
| native `inputs/slices.json` | 4,328,055 | `5ac878860f90865f8515c223b21224e89488b12a30b84b36049158deafaa1b91` |
| native `inputs/coverage.json` | 36,637 | `2d262a2d72e6f21d001ceb92931ffd253a26604b188355eeffb7982c19f7bffe` |
| native `inputs/operation.json` | 175 | `6acdf5319f5fa143a08b963b85077fcbec3638cb025a809d4a0f3a8a0a8b0990` |
| native `document.json` | 128,090 | `fa7b44d97d2f534d76c1ff49cf6e8d97ff0f2073f1ceb2a43a074659bc1f766e` |
| native `slices.json` | 1,972,118 | `94d1a10f0f3ee5abbd8f6a79fa292e27b1d9e30f8e98f8ec05ec03c566c5c94d` |
| native `writer/result.json` | 7,981 | `24862233e83649bb68193c2916e2beb9febc0c1c72f011d2e7d6fea7614d9562` |
| native `reader/result.json` | 7,888 | `9a23293dccd689cf6f37c0f98071bf76c67cc95615f13be7cec7ac1d775d1cfa` |
| native `published/.complete` | 1,281 | `841472b057996f3f744a735aa35b6c43afed2751bd1b2f512cc0e321b57ea9cf` |
| helper `prepare.py` | 5,263 | `282c336d0dc4b858055f15f9d0b59298bb5db6dde64958a7d9c2a354d76773bb` |
| helper `run.py` | 4,413 | `207c9e2ba7d3d5bc88e21e1a46e7cb4d0b80c5d49a2046706ae859c4d97554ba` |
| helper `request.json` | 4,797 | `77404941138a39707f7f64737fa7eaafc9ca50dc6a26e33616cd760fe54b7da2` |
| helper `capacity-preflight.json` | 278 | `5af8ccb76d2de91a553ba0c6b036bc5642fea3d827eaf53cbfeb56ab3b6ef758` |
| helper `execution.json` | 763 | `bac6d50d7ad042bbf16780c2975284bacfabab0d6341203650f929db23dbc229` |
| helper `postcheck.py` | 26,391 | `7c77f00931c275fba47723e0cf7329afc64f70b33810497c196467218e658b77` |
| helper `postcheck.json` | 857,111 | `fc0f8e8cc14920877fa6440fe4c28ee90771cfd3975ae3258a8fae4a06cd1dd4` |

helper a1の誤revision指定とa2のWindows pin key／区切り文字不一致は、本測定・観測payload読取り・request保存前に拒否された。各rootと失敗記録を保全し、a3で修正して実行した。a1 `prepare-invocation-failure.json` は381 B／`292e982507624e0abe321923dac3a45c6f13358bbecfc30a38acd3079c23bc82`、a2 `prepare-pin-lookup-failure.json` は287 B／`2e58c324118e69e68936865476b875000662f80e9040d00a75a910f33619a514`。失敗を成功へ変更していない。

## 次の作業

producerと保存形式readerを同じ外側時計へ接続し、出力root・終了記録・観測由来をその時計で結ぶ。正式同形のsmoke由来容量2倍、運用契約改訂の採択、source/runtime全在庫、最終両OS・正式dev8/smoke2・独立受入は残る。架空480区間の実生成完走を追加必須にしない。[受入範囲案v3](../anomaly-v03-s4-acceptance-scope-draft-v3.md)は引き続き未採択。
