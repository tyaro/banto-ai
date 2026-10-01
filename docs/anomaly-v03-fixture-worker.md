# 小さい架空入力を計算する所有worker

`anomaly_v03_fixture_worker.calculate_with_evidence` は、小さい架空入力を別のPython processで計算し、親が起動前に保持した入力・既知の出力・source/runtimeと実行記録を照合する。確認できた文書を既存の[5payload adapter](anomaly-v03-wrapper-fixture.md)へ渡す。[実装](../src/banto_ai/anomaly_v03_fixture_worker.py)、[試験](../tests/test_anomaly_v03_fixture_worker.py)、[今回の結果](results/anomaly-multiseed-v0.3-fixture-worker-2026-10-01.md)。

これは既知の手例を使う計算接続試験である。登録観測を評価するconsumerや、独立した数値auditの入口ではない。正式modeは入力ファイルを開く前に拒否する。

## 呼出しと入力

`calculate_with_evidence(request, *, expected_revision, receipt_parent, receipt_name)` を呼ぶ。出力先は毎回新しいdirectoryを使い、入力directory・sourceと重ねない。古いattemptへ上書きしない。sourceはGit revisionとraw bytesが一致するclean checkoutから実行する。

requestの固定欄はformat、mode、role、operation、inputs、expected_document_pin。formatは `anomaly-v03-fixture-numerical-request-v1`、mode=fixture、role=analysis、operation=`assemble-invented-document-v1`。保存済み結果準備のoperationやreader役割を代用しない。

| inputsの名前 | 内容 | 上限 |
| --- | --- | --- |
| fixture/input.json | invented-00〜39の40cluster、診断、1〜8個の40要素draw | 1MiB |
| fixture/slices.json | 同じ40clusterの架空slice counts | 8MiB |
| fixture/coverage.json | 40×12layout×2層×3候補の2880宣言枠 | 128KiB |
| fixture/operation.json | operation_descriptor(expected_revision) | 4096bytes |

各入力は絶対path、別に保持したbytes/SHA-256のpin、links=1を持つ。合計10MiB以内、ファイルはcanonical JSON bytesを要求する。coverageは全枠success/inconclusiveの処理済み状態のみ受け付け、partial/failed/not_startedなら計算を起動しない。2880は宣言枠数であり、この試験が新たに実行した評価件数ではない。

`expected_document_pin` は起動前に別に保持している既知の架空文書のcanonical bytesのpinで、最大4MiB。子の返したhashをそのまま期待値へ転記しない。親はCI/推論を再計算しない。今回の既知文書は前工程と同じ計算実装から作られた手例なので、これとの一致は独立した数値検算を意味しない。

## 計算と証拠の流れ

親は21本のselected sourceとGit tool、Python本体/DLLの2ファイル、4入力、既知の出力pinを保持する。invocationにはランダムID・source・requestを入れ、別にpinを保持して固定起動引数へ渡す。invocationは制御情報として両側で照合し、数値入力のinventoryは4ファイルのまま維持する。

既存supervisorが `-I -S -B` の子processを所有する。親は元Popen handleからPIDと生成時刻を取り、起動引数・cwd・期待値を保存する。子は同じ入力から文書計算とslice接続を行い、既知の出力pinへ一致する場合だけdocument.jsonを保存する。source/runtime/input/invocationの前後照合、子自身のPID・生成時刻、依存fileの採取結果とともに応答する。

親はexit0・終了確認・観測error0を要求する。終了後、応答pin、親保持値と保存済み期待値、子生成時刻、文書bytes、role・operation・入力inventoryを照合する。補助依存記録はdisk/Gitへ照合する。これらを通過した文書とanalysis evidenceだけを既存adapterに渡して5payloadを保存し、各hashを読み戻す。

PID・生成時刻・元handleの一致は所有した子との対応を強めるが、実行認証やメモリ内コードの完全な証明ではない。依存採取はselected sourceに加える終了後の観測で、全依存の完全固定でも、新役割の事前受入済みprofileでもない。正式bootstrapの50,000反復は起動しない。

## 資源と失敗時の扱い

子の上限は60秒、private bytes 256MiB、stdout/stderr合計1MiB。既存supervisorが約0.25秒ごとに確認し、超過時は所有processを停止・終了確認する。入力・文書・5payload合計にも10/4/8MiBの上限を置く。出力値のサイズ検査は書込み前、保存後はhashを読み戻す。

これは子processと限定ファイルの上限である。親の全計算を含む連続監視、directory全体の連続容量監視、システムcommit余裕の連続停止条件は今後の全工程予算で接続する。試験harnessは実行前後のRAM・commit・C/D容量と自身のpeak privateを記録する。

起動・計算・照合に失敗した場合は成功payloadを組み立てず、保存できた診断を残す。未終了の子を示す `UnreapedWorker` は元process ownerとともに再送出し、診断保存の失敗でもownerを失わない。呼出し側はそのownerの終了確認を引き続き担う。子が停止済みでも失敗結果を自動再試行しない。

## 出力と受入範囲

receiptにはinvocation、source tool、親のlaunch/expected、supervision、子のreport/stderr、計算したpayload/document.json、evidence/binding、依存記録と照合結果、wrapperの5payload/descriptor、resultを保持する。通常writer/reader/auditや公開markerは起動・生成しない。

成功はstatus=verified、fixture_inference_performed=true。この新欄は小さい架空計算を行ったことを示す。既存のnumerical_analysis_performedおよびformal/promotion/S6/trust/execution_authenticated/full closureはfalse、正式文書のstatus/provenance/analysis_consumer/bootstrapはnull、ready=falseを維持する。科学的合格や正式実行許可へ変換しない。

次は、同じ小さい入力とanalysis出力を別実装で検算する数値auditを接続する。その後、全工程の資源停止条件と正式受入の残件を整理する。
