# 単一writerによるv0.3評価実行への移行案

2026-09-16。照合した実装は `9365d513a40ce34b7160aab190c943007e682774`。
2026-09-16の提案確認後、ユーザーの「次に進めてください」を受け、運用改訂を採択した。
現在は **adopted / 固定6件controller実装済み / 初回6件の保存・再計算成功**。[実行方法と記録の読み方](anomaly-v03-engineering-evaluation.md)と[初回結果](results/anomaly-multiseed-v0.3-engineering-trial-2026-09-16.md)を参照。
ユーザーの「同時に同じ個所を進めない限りは不要」と、Windows Updateの条件緩和・資源配慮の方針を、研究評価へ接続するための具体案。
既存の[科学計画](anomaly-multiseed-evaluation-plan-v0.3.md)・registry・runtime gateは、この文書では変更しない。

## 照合結果

| 項目 | 現行実装・条件 | 接続に必要な作業 |
| --- | --- | --- |
| 公開run入口 | `anomaly_v03_runner.run_campaign` はruntime probeと受入拒否の後に実行処理がない | 新しい運用契約のcontroller・保存・consumerを接続する。gateの削除だけでは実行できない |
| OS | `probe_runtime` とregistryは26200.9168を固定。現在の観測値は26200.9445 | 新契約でWindows 11 Pro 25H2/AMD64/NTFSとPython 3.14.0を指定し、OS build/UBRは各attemptで記録・照合する。再起動・更新で試行中の環境が変われば停止し別attemptへ |
| 保存 | 旧S4はprotected DACL・別token/AccessCheckを要求。通常LocalPublicationは利用可能 | 新契約では同一出力先の単一writer、非上書き、失敗後の再使用拒否、完了印、全payload再検証を必須にする |
| 入力 | local previewは最大18000行の部分入力も診断用に受理。既存`validate_dataset`は2設備×9000秒と全metadata/eventsを要求 | 部分previewを評価datasetへ読み替えず、固定materializerの完全なpaired datasetを保存してから読む |
| 計算 | `compute_evaluation` にprofile/score/episode/matching/accountingがある。identity・イベント・分母は登録済み契約に結合 | 実際のdev identityと完全な保存済みdatasetで再利用する。任意の観測へ架空の登録identityを付けない |
| provenance | `capture_checkout` はtracked全体のcleanを要求。現作業コピーには保全対象の既存doc変更がある | 確定commitの別clean作業コピーで実行し、既存変更をstash/削除/取り込みしない。全対象sourceとGit blobの一致を確認する |
| 再検証・監査 | `verify_evaluation` はproducer再計算。独立S6解析・監査やbootstrap/昇格判定とは別 | 保存後の再計算は利用する。独立監査・性能判定・promotionを未実施のままpassにしない |
| 全体規模 | 現行devは576評価、smoke144、holdout2880 | 最初は下記6評価のengineering trial。全dev/smokeの代替や正式受入と扱わない |

根拠となる実装: [_anomaly_v03_runtime.py](../src/banto_ai/_anomaly_v03_runtime.py)、[anomaly_v03_runner.py](../src/banto_ai/anomaly_v03_runner.py)、[anomaly_v03_materializer.py](../src/banto_ai/anomaly_v03_materializer.py)、[anomaly_v03_episodes.py](../src/banto_ai/anomaly_v03_episodes.py)、[_anomaly_v03_io.py](../src/banto_ai/_anomaly_v03_io.py)。
`_run_prepared` はrole全体の固定inventoryと旧producer resultに結合しているため、6件だけに切って正式matrix resultを作らない。

## 推奨する契約変更の範囲

新しい実行方針IDを **`anomaly-v03-single-writer-v1`** とし、元の科学仕様への参照を持つ運用改訂として記録する。
変更点は単一writerの保存契約とOS更新の扱い。Windows側のPython 3.14.0一本化、候補式、fit/calibration/test分割、6桁丸め、seed順、layout、quality、閾値、persistence、matching、分母、bootstrap、performance gateは維持する。既存Linuxの3.12/3.14検証条件は変更しない。

最初の実行区分は **engineering-dev**。旧S4のnative受入を満たしたとは記録せず、旧 `require_campaign_acceptance()` も残す。
新しいcontrollerの入口はengineering-devだけを受理し、環境変数や `--force` による旧gateの解除は設けない。
新scopeのmanifest/result wrapperが実行方針ID・attempt ID・実source/runtime・固定対象一覧を持つ。個別の科学的identityは元の登録値を保持し、外側の実行区分で正式campaignと区別する。
Windowsのobserved runtimeを記録し、`formal_runtime()` の固定辞書を観測値として渡すことはしない。

この方針は、凍結済み計画§8/9とは異なる運用条件として採択した。元の計画の失敗・保留を合格へ置換する意味ではない。
将来の正式研究評価まで進める際は、新scopeの受入証拠・完全runtime inventory・consumer revision・全dev/smoke・容量見積りを揃えて別のfreezeを行う。engineering trialの成功だけではholdoutを開かない。

## 最初の試行を固定する

- 登録済みdev seedの先頭1個、layout index 0。
- `core`、`quality-stress` の順で、各々C0/C1/C2の全候補。計2 dataset・6 evaluation・288 profile・86400 score行。
- seed/layout/候補の選択を結果に応じて変更せず、未実施を含む6枠のledgerを開始前に作る。holdout・smokeは実行しない。
- 1つの正常系列からpaired datasetを作り、2 datasetの全bytesとmetadataを保存・再読取りした後に計算へ渡す。同じ層の3候補は同じ保存bytesを読む。
- 個別evaluationは`compute_evaluation`を順番に実行して保存し、前の大きなledgerを解放する。保存結果は`verify_evaluation`による再計算を行う。
- `anomaly-multiseed-v03-*` の正式rootを使わず、専用の親 `artifacts/anomaly-v03-engineering-dev`（初回に作成）と新しいattempt名を使う。保護rootや既存attemptを再使用しない。
- 新scopeのsummaryは試行範囲・coverage・工程状態・資源実測を報告する。per-evaluation metricが得られても全campaignのperformance/promotionは`not_evaluated`/falseのまま。

新manifestは `anomaly-v03-engineering-run-v1` とし、source/runtime/attempt/6枠ledger/各dataset hash/各evaluation hashを持つ。
LocalPublicationの完了印は保存の完了を示す。6枠が全て完了したことや科学的合格はmanifestのcoverage/statusから別途判定する。
公開前のglobal integrity failureでは後続をnot_startedとし、残せる失敗証跡を保全して完了印を付けない。公開後readerや監視で失敗した場合は既存markerを撤回せず、試行全体のsupervisionをfailedとして残す。通常のprofile inconclusiveを成功へ変換しない。

## 資源と失敗時の扱い

最初の試行上限は **全体15分・専用worker private bytes 2GiB・新attemptの出力1GiB**。
開始条件は空きRAM4GiB以上・出力volume空き20GiB以上。これは既存計画の正式実行容量見積りを代替しない。
専用workerを1体だけ起動し、同時の評価・bootstrapを走らせない。監視はローカルsupervisorが行い、モデルの進捗ポーリングで代替しない。
上限超過では当該attemptの所有workerだけを停止・回収し、既存ファイルを削除しない。同名再開や自動の予算拡大はしない。
実装時には、出力の書込み予算を保存前に検査し、部分書込みやworker終了を完了扱いしないことを確認する。
前回の約75KiBの表示成果物から、完全な6評価や正式holdoutの容量を外挿しない。最初の試行で所要時間・peak memory・出力bytesを測定する。

## 実装の順序と完了条件

1. 運用改訂の採択後、独立したpolicy/manifest validatorと固定6枠のplan builderを実装する。元のscience bundleと旧gateに変更がないことを確認する。
2. clean source/runtime capture、1 pairの保存、順次計算、通常保存API、保存後readerを接続する。まず小さなfixtureで順序・同じ入力・失敗状態・資源停止を確認する。
3. 新attemptで固定6枠を1回実行し、全枠の工程状態と実測資源を保存する。失敗しても部分結果を正式な成功へ読み替えない。
4. その結果で全dev/smokeへ拡張する容量を見積もり、新scopeの受入・独立consumer・freezeの残件を整理する。

初回提案時の到達点は接続案と現行契約の照合までだった。採択後の実装・実行記録は[実行ガイド](anomaly-v03-engineering-evaluation.md)と引継書の最新節へ追加する。旧formal gateは維持する。
