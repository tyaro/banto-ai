# 単一writerによる固定6件の開発評価

採択済みの[運用改訂](anomaly-v03-single-writer-evaluation-proposal.md)を実装した経路。
方針ID `anomaly-v03-single-writer-v1`、実行区分 `engineering-dev`。元の科学仕様、registry、正式runnerと受入gateは変更していない。

## 範囲と実行

最初のdev seed・layout 0を固定し、core/quality-stressの各C0/C1/C2を順番に処理する。
2 dataset・6 evaluation・288 profile・86,400 score行。対象を変更する引数や自動再試行はない。
以下の計画表示はデータ生成・runtime観測・出力作成を行わない。

```powershell
C:\Python314\python.exe -B tools/evaluator/run_anomaly_v03_engineering.py plan
```

実行は確定commitのclean作業コピーから行い、同じコピーのentrypointを使う。
既存の変更をstash・削除する必要はない。実行前に別のclean worktreeを作成し、HEADの完全40桁を確認する。

```powershell
C:\Python314\python.exe -B tools/evaluator/run_anomaly_v03_engineering.py run --root . --expected-head <40桁commit> --name trial-01
```

出力先はその作業コピーの `artifacts/anomaly-v03-engineering-dev/trial-01` と `trial-01-control`。
同名は拒否し、失敗した出力も残す。内部の `_worker` はsupervisor専用で、直接実行しない。
専用アカウントや管理者起動は使わない。

## 保存・再計算・停止

単一workerが通常の保存APIを使用する。全sourceのGit/作業コピー一致と実runtimeを確認し、固定6枠を最初に保存する。
登録済みの正常系列から1 pairを生成し、2層の全bytesを保存・再読取りしてから計算する。同じ層の全候補が同じ保存bytesを読む。
既存の `compute_evaluation` を呼び、各評価と開始/完了journalを順次保存する。大きな前の結果は次の候補へ進む前に解放する。
公開前にpairを再生成して保存bytesと照合し、全評価を `verify_evaluation` で再計算する。writerを閉じた後もreaderで同じ検証を行う。
これは同じproducerによる再計算であり、独立S6 consumerや性能判定ではない。

上限は全体900秒・所有workerのprivate bytes 2GiB・出力1GiB。開始時に空きRAM4GiB/volume20GiBを要求する。
supervisorは0.25秒間隔で所有processのメモリと経過時間を確認し、worker側も保存前・公開直前に予算を検査する。
保存前には出力bytesに1MiBの管理記録予備を加えて検査する。上限超過で所有workerを停止し、終了を回収する。
監視APIの失敗も成功へ変換しない。一次停止理由・終了確認と、追加観測の失敗を分けて記録する。
OS build/UBRは実値を記録するが、Python3.14.0/build/binary・Windows11 Pro25H2/AMD64/local-NTFSの条件は維持する。実行境界でsource/runtime変化を検査する。

## 結果の読み方

- `payload/planned.json`: 未実施6枠と固定条件。
- `payload/context.json`: 実source/runtime。
- `payload/datasets/`, `payload/evaluations/`, `payload/journal/`: 入力・評価・各枠の進行記録。
- `payload/manifest.json`: 固定範囲、保存hash、6枠の状態、coverage。`resources.measurement_end=before_publication` は最初の計算・保存段階までの実測で、再計算を含む全体値ではない。`payload_bytes` はmanifest自身を除くpayload量。
- `trial-01-control/supervision.json`: 全worker期間（公開前再計算・公開・writer終了後再計算・終了を含む）の時間とpeak private bytes、停止理由、終了コード、空き資源。**試行全体の資源値はこちらを使う。**
- `trial-01-control/stdout.jsonl`: 各枠の保存状況と、最後のmarker hash付きreceipt・reader検証結果。

`.complete` は保存の完了印。これだけで試行全体の成功とは扱わず、supervisionのstatus=complete/exit0/終了確認と、最後のreader成功記録を合わせて確認する。
公開前の失敗では完了印を作らず、可能なら `failure.json` に未実施枠も残す。強制終了では保存済み計画/journalとsupervisor記録が証拠になる。
公開後readerの失敗では、作成済みmarkerを削除しない。supervision failedを保持し、成功件数に含めない。
profile不足はinconclusiveを維持する。6枠完了でも全dev576件/smoke144件の代替にせず、performance=not_evaluated・formal_permission=falseを維持する。holdoutは実行しない。

## 検証範囲

小さなfixtureによる新規25件と既存通常保存12件がpass。固定範囲・順序・paired入力・再計算・失敗時の保存・重複拒否・資源停止・監視の二次障害を確認した。試験で登録seedの観測は生成していない。
独立レビューの2指摘（監視二次障害時の記録欠落、資源値の計測期間）を是正し、再レビュー指摘0。
