# 自走終了時の証拠保全

人の「次のターンで自走終了しましょう」（2026-10-08T10:41:09Z）に従う最終ターン。開始10:45:39Z、元HEADc2b161d3d111a9a8f2812cc2e0f4c733b20ebe41/origin一致・clean、production5d52f8d7f38e043295a79af00f94748edbcd6347不変。新production/test/focus/native/agent/業務worker/計算を開始しない。文書保存後にheartbeat banto-10を全既存fields保持でPAUSEDへ更新し、明示再開まで自走しない。

## CI観測と保存範囲

| run / fullHEAD | 一度のcompact観測 | 今回の保全・未完了範囲 |
| --- | --- | --- |
| 37756831995 / c5bffdb1e23d1563020d7fc2345fb1bfc1bad5c3 | completed-success、3job成功 | 原run/jobsと未取得3logを一度保存。artifact API失敗、2journal/comparison-regression artifact未取得。件数・local回帰・runner検証未実施 |
| 37763660778 / 5d52f8d7f38e043295a79af00f94748edbcd6347 | in_progress、3.12/3.14 jobともin_progress | 原compact stdout/stderrだけ保存。待機・反復照会・終端download0、attempt/終端未固定 |

compact-state.json1352B/7a6201f2acabc394658fc0b509c6c81333291a91ca2b578c56448a62b1266e78。各gh stdoutは7379B/87cb886ae4dc210a5cdaff18603a0ce512b9272f132679b86404486404108ba2、4666B/639e1fedace68875aea39d6ffbed1b6f9f4c23d77be017fc950b5de376a3d95e、stderrは各0B。これは元CLI返値bytesであり、helper全process stdout/stderr logではない。

終端runはattempt1/push/Phase 1 CI/.github/workflows/ci.yml、3.12job113243338640/3.14job113243338368/compare113260296438へ保存済みrun/jobsを固定。原run.json11679B/jobs.json9143B。artifact一覧APIはunexpected EOF/exit1、原stdout0B/stderr114Bを直接保存。原script・download-failure・live/execution failedを保持し、同API/同scriptの再試行0。新zip/artifact raw0、成功metadataで失敗を補わない。tool tracebackは全helper byte logではない。GitHub API失敗をnative回収・Sol容量エラーへ読み替えない。

別metadata helperは保存済みrun/jobs pinに結び、未取得3logだけ各一度保存。3.12log1011552B/e60ca65cea4d02302cf73ad2535cabee057431a9d9a78187f43cb093de2d21eb、3.14log1011509B/22b69fb981624e87d29756530607de31891b246b7de164f5b265ab0ef97a9214、compare41691B/701daee42ff61ec820564728c76d907ff409e6878d1f8cd54da0dc386b67995e。logs-preservation-summary.json1389B/6c59dfb789169c0db9f81a77e459e8d2f7d3b75923c7924a4a628b4ae92db42b。journal/comparison/regression内容を読んだ検証ではない。3885/3909は算術予定で実journal件数未確認。完成CI保存・runner採択・容量/native/child-owner認証・正式受入へ読み替えない。

未終端runの原観測は3.12job113265921172/3.14job113265921504、compare未発行。最終観測後は完了を待たず、自走を延長しない。

## 元owner/helperと閉鎖root

元post16660/creation134359294181570968/start_token b5cd3cacd3096be69811da510f7ab797f695c476abaea0ef48992b49c3b2f56cの原記録を保持。今回helperは次の別processであり、原failedを書換えない。

| helper | 元PID / creation / start_token | 保存結果 |
| --- | --- | --- |
| compact | 37232 / 134359302584440271 / 02bebd47c4a05823574fd9a1a2bee520a38300dd9571a16897b8fb0ff9869a8e | passed |
| 原download | 48532 / 134359303641475641 / 7ffcd812c8e946c9c2d9c45c7ceae7393dc671bd6b3d60f4abc7c973f2a84113 | failed、原API error bytes保持 |
| 未取得log保全 | 31852 / 134359304571666133 / b67413586245963a9c2730b56fc0ac6a74bf3f2338a78adc12ec64f8c7fa2706 | passed、旧失敗API再試行0 |

10:55:18Z read-only CIMは各live/execution full identity一致・同original不在/repo Python helperなし。PID単独判定なし、critical owner観測なし、native_recovery=false。旧publication prep21file100198B/continuation13file57702B/CI3864root38file10327138Bのmetadata不変。元keeper/HANDLEやunknown ownerをmetadata/EOF/kill-waitで回収trueへしない。

新rootはartifacts/preformal-autonomy-final-stop-20261008-prep/（512KiB32entry/reserve128KiB/single128KiB）、artifacts/ci-diagnostic-37756831995-final-stop/とartifacts/ci-diagnostic-37756831995-final-stop-logs/（各16MiB256entry/single8MiB）。原rawと別log rootのpinを停止metadataに保存して閉じ、旧root追加・整理・receipt移動・上限緩和0。原helper script再実行/完成focus・完成CI反復0。

formal gate=s4_acceptance_not_frozen、formal_permission=false、credit0、登録holdout観測未読。正式5残件・採択・最終受入は未完了。実native入口/create_native早期拒否/全7役whole.run限定reader実起動禁止を維持する。
