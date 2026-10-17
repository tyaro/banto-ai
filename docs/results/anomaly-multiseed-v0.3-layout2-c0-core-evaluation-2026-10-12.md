# dev layout2 C0 core実評価（2026-10-12 JST）

## 原入力と実行範囲

保存済み合成dev seed2486912926863618161/layout2/coreを既存CLI C0 c0-diff-controlで一件実compute_evaluation。新ID dev-next-core-c0-20261012は前工程の予定名を使用。10input pins照合→新input snapshot→fresh calibration→原profile/score/episode/event/incident/metrics保存。元payload書込み・新dataset生成・replay・production/test変更・類似owner追加・追加agent・holdout本文読取り0。

input manifest: C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\002\attempt-0001\result\payload\manifest.json

manifest 75699B/c97c3564c28b679668c2f7425b33aaedadec0c90c45e5705e929131826797783、dataset anomaly-v03-dev-seed-2486912926863618161-layout-02-core。生成dataset identityのcandidateと実評価candidateは別fieldで保持。actual文書checkoutHEAD548e519f06f0e43a051449afcb051fa91462c3f8、計算code661b27511826fcc87cb4a02930f276afbb8f95d9不変。actualPython3.14.0 Windows AMD64、elapsed18.83848399994895秒/OScheckpoint peak private146202624B。

既存engineering900秒/2GiB private/output1GiB/single32MiB/files32のcheckpoint上限を維持。blocking計算中断・full loaded runtime閉包・全writer/global/native容量証明ではない。

## 原実結果

CLI exit0/complete/1cell success。処理successをモデル性能合格・採択・勝者・正式受入へしない。

- 機械0/10・sensor0/10・precision0/3・clean誤警報3・全未対応equipment3。
- calibrated48、C0原fit_samples各0/calibration各290。score14400、利用可能13920・不能480、全primary/nonexclusive mode_recipe_or_phase。全不能score/residual null、threshold_exceeded=false。
- 原input mask/observations18000行対応、non-ok input record0。quality欠測による不能0/peer不能0。今回の未検出を欠測で説明しない。
- source3/equipment3/incidents20/events40、原20incident全no_candidate_in_window/candidate0/causalfalse/matchednull/selected source null/support[]/delaynull。
- delay count0、median/mean/min/max原null、未検出delay補完0。
- clean_rate原3/3365/value25.676077265973255、effective_clean_seconds3255/effective_clean_rate26.551936078672405、false_alert_burden3/20/value15.0。これらを単純確率へしない。

## 未検出と固定persistenceの対応

### cycle00 machine: motor current / low_speed

event start7274/end7277/windowend7280。原matching candidate0。

| sample | available | 原score | streak | exclusion |
| ---: | --- | ---: | ---: | --- |
| 7274 | True | 32.21755133935066 | 1 | None |
| 7275 | True | 0.3247037426630626 | 0 | None |
| 7276 | True | 0.09299239078738782 | 0 | None |
| 7277 | True | 33.3092916329281 | 1 | None |
| 7278 | True | 1.435643472357744 | 0 | None |
| 7279 | True | 0.27820537931136063 | 0 | None |
| 7280 | True | 1.440170168678071 | 0 | None |
| 7281 | True | 1.8370018742612677 | 0 | None |

7274score32.21755133935066/streak1→7275 .3247037426630626/0、7277score33.3092916329281/1→7278 1.435643472357744/0。固定C0threshold4/persistence2不成立。全motor4targetの原score windowも保存。

### cycle00 sensor: motor temperature / low_speed

event start7281/end7284/windowend7287。原matching candidate0。

| sample | available | 原score | streak | exclusion |
| ---: | --- | ---: | ---: | --- |
| 7281 | True | 184.62984497661753 | 1 | None |
| 7282 | True | 0.29369641246287376 | 0 | None |
| 7283 | True | 0.4089700250831749 | 0 | None |
| 7284 | True | 185.57947997582082 | 1 | None |
| 7285 | True | 0.18546382420233276 | 0 | None |
| 7286 | True | 0.6560543930619088 | 0 | None |
| 7287 | True | 1.8426291264630492 | 0 | None |
| 7288 | True | 0.7817505746349682 | 0 | None |

7281score184.62984497661753/streak1→7282 .29369641246287376/0、7284score185.57947997582082/1→7285 .18546382420233276/0。窓内はavailableだが連続2超過なし。cycle01 machine/sensor及びcycle09 sensorの全4target窓も原extractへ保存。GT・threshold4・persistence2・first-equipment-onset-no-retry-v1・science変更0。実入力対応・保存・状態分類実経路不具合観測なし。

## 原未対応episode3とclean3

| equipment episode onset sample | target source | context | matched_event |
| ---: | --- | --- | --- |
| 7242 | anomaly-v03-dev-seed-2486912926863618161-layout-02-core-c0-diff-control-score-motor-01-vibration_feature-7242-source | clean | None |
| 7712 | anomaly-v03-dev-seed-2486912926863618161-layout-02-core-c0-diff-control-score-conveyor-01-motor_temperature-7712-source | clean | None |
| 8517 | anomaly-v03-dev-seed-2486912926863618161-layout-02-core-c0-diff-control-score-motor-01-vibration_feature-8517-source | clean | None |

motor vibration7242、conveyor温度7712、motor vibration8517の全3context=clean、matched_event=null。先頭7242は今回first machine event7274–7280より前でmatching候補に入らない。過去layout1 C0 coreのclean2/全未対応3や原graceを今回clean3へ書換えない。今回source/equipment全6原episodeと20event/incidentを保存。

## 同seed・旧layout core C0との保存比較

| layout | candidate | machine | sensor | precision | clean誤警報 | available | delay count / median |
| ---: | --- | --- | --- | --- | ---: | ---: | --- |
| 0 | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 13920 | 0 / None |
| 1 | c0-diff-control | 0/10 | 0/10 | 0/3 | 2 | 13920 | 0 / None |
| 2 | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 13920 | 0 / None |

旧layout0 C0は保存初回core2cell manifestからC0 cellだけ、旧layout1 C0も保存manifest/config指標だけ。旧モデル再compute0、旧raw result本文の再展開0。3layout全宣言16calculator source・candidate_config・compiled_candidate_config一致、core inputの10file name集合は同じでもraw pinsはlayout差を保持。今回same seed別layoutで新独立seedではない。3cellを3独立seed評価へしない。C0全layout機械sensor0/10で、clean数3/2/3も原値のまま。bootstrap・統計CI・勝者・採択0。完成layout0/layout1の全12cell・明示replay・既存risk testsを反復しない。

## 原pin・閉鎖root

| 原保存 | bytes | SHA256 |
| --- | ---: | --- |
| input observations | 9600596 | 57b2d660806a00eb3d14d5eb262163ff38273b497ee5665ba994598875dddc02 |
| configuration | 5503 | 06e085edbf1c14cd1f54595adc4c7eb13cd86b74327cf11045bf51966e68d1ba |
| manifest | 8028 | dfaff1ed6a29deb373db3b0598001fe0807abefdfca2e6acaf08b72baaa6ad9b |
| evaluation-0 | 13899030 | 7b37f634063e9d4de46b1588c832ffca29eed5abcf003919fcfdb7c35b844235 |
| numerical | 13893532 | 18989c38caee298827da89812bdfb8550cc65838e71422b0f782f1026514d61b |

| layout core C0 保存manifest | bytes | SHA256 |
| --- | ---: | --- |
| 1 | 8030 | 2617eca766b9a10e840ac5a7d5e9798cc1466e28989bbfdefae45484d4aa2236 |
| 0 | 11019 | 0898a0ee0eb0a5a15af8e52d320832abe06220e30cb8cad0d02f7f774a01e094 |
| 2 | 8028 | dfaff1ed6a29deb373db3b0598001fe0807abefdfca2e6acaf08b72baaa6ad9b |

| 原extract | records | bytes | SHA256 |
| --- | ---: | ---: | --- |
| incident-ledger-001.json | 20 | 19369 | af3c825ead81e501b7b205c31066ebcfdb257ad1f8abd5ebb7a73e9206fd9c08 |
| selected-windows-001.json | 5 | 63176 | 7ca58a6287cb689dcfe603b6d2a2480edfb04bedc4fe553c47ee4e8850b94fdc |
| all-source-equipment-episodes-001.json | 6 | 4476 | 8393722672cc98b19c331246566d1ef9660b3969ca6318dfb58e8dc0813338c6 |

data dev-next-core-c0-20261012閉鎖{'bytes': 26939736, 'files': 19, 'manifest_pin': {'bytes': 2249, 'sha256': 'c0e55321f220d203bd79546a5df4f432deb044fb42f7bd34c6bdd1af946c4776'}}。EXTRACT representative-layout2-core-c0-extract-20261012-prep閉鎖{'bytes': 87726, 'files': 4, 'manifest_pin': {'bytes': 705, 'sha256': '1f772d6638fad33b9d3f8f984d2718a143f2d94ddadefdca183b1bd9e35e6d80'}}。MAIN representative-layout2-core-c0-20261012-prep/POST representative-layout2-core-c0-post-20261012-prepのpost-save/owners/root-closedを最終Git状態として優先。

新metadataはpython -B/recursive count-byte-pin、512KiB32entry/reserve128KiB/single128KiB。書込み前にscript/失敗/終端/closure reserve確認、closed/外部固定root追加・原helper再実行・raw削除移動・上限緩和0。EXTRACTscopeは実candidateから作成。117science-source・旧45root count-byte-closure pin・C1 MAIN外部固定35file226520B・旧C2 cache補足pin不変。原C1 MAIN容量超過/原failed、旧C2 closure coverage補足、旧scope/roster文字列とforeground metadata失敗を保全し、今回成功へ書換えない。

元102instrumented helpers full saved creation-start_token/live-execution一致、原9failed93passed/CIM同original不在/repo helper-criticalownerなし、今回モデル/解析2passed。CIMdecimal100ns→microsecondtrunc/full saved token/PID単独0/native回収claim0。foreground fullcreation/stdioNone、selectedCLIを全helperstdioにしない。今回manifest assertion一行だけ72eからc97cへ正確に変更、hash/seed無限定置換0、準備・モデルの新failed0。

## Git承認・次unit・formal状態

送信リスク通知後の人の「承認します」による同送信先 https://github.com/tyaro/banto-ai.git への同種合成dev結果・ユーザー名を含むPC内入力path報告の継続承認でreport/current-handoff2文書を一回[skip ci] commit/pushする。保存後HEAD/upstream/lsremote/clean/docpinsはPOSTを優先し後追い文書再commit0。原自動審査拒否/元Githelper未起動は履歴保全。Git caps512KiB16entry/stdout1MiB/累積30秒維持。automationは文書参照短指示ACTIVEのまま、今回詳細結果・PC内path転記/設定更新0。

次unitは同保存chunk002 manifest/dev seed/layout2/core、candidate C1 c1-phase-level、新ID dev-layout2-core-c1-20261012で1cell実評価。input manifest c97c3564c28b679668c2f7425b33aaedadec0c90c45e5705e929131826797783を維持。生成dataset identityのcandidate c0を実評価C1と混同せず別fieldにする。元payload/新dataset生成/旧cell再実行0。同layout2 quality pairは保存metadata10pinsだけ、次quality観測本文未読/compute0。

CI38138556456/code661bの4130success独立verifier完成保存を維持、今回CIquery/download/verifier0/doc-onlyCI追跡0。旧381365/a54961最後in_progressは履歴のまま。CI成功はモデル性能/native/正式受入成功ではない。

formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout観測未読/正式5残件・最終受入未完了/create_native早期拒否/全7役whole.run reader実起動禁止/元caps-unknown原owner-stop/追加agent禁止。未完了formal/native全証明を少量dev開始条件へ戻さない。Sol容量又は人の停止では原証拠保全後PAUSED、重複再試行0。
