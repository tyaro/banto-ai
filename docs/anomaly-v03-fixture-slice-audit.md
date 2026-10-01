# 架空の条件別集計・補助診断表の独立検算

`anomaly_v03_fixture_slice_audit` は、保存済みの架空40clusterのcountから条件別集計を別実装で導出し、本文と補助診断表へ正しく反映されたか検算する。[実装](../src/banto_ai/anomaly_v03_fixture_slice_audit.py)、[純粋関数の試験](../tests/test_anomaly_v03_fixture_slice_audit.py)、[所有processの試験](../tests/test_anomaly_v03_fixture_audit_worker.py)。計算側のslice集計・mapping・validator関数は呼ばず、importはstdlibのhashlib/jsonのみ。

主9表の[既存primary audit](anomaly-v03-fixture-numerical-audit.md)にこの検算を加えたoperationを、同じ`audit_with_evidence`から選択できる。旧primary-onlyの入力inventory・operation・出力名・検算範囲は維持する。保存済みの元analysisや旧receiptを書き換えない。

## 検算するもの

| 対象 | 確認内容 |
| --- | --- |
| 入力 | invented IDの40cluster、3候補、2層、12layout相当の整数counts、固定key inventory |
| incident | class/equipment/modeの結合表と周辺表、各partitionのplanned/detected/histogram一致 |
| score | target/mode、8種類の排他的partitionとevent-offset参照、available/exceeded/onsetの部分集合 |
| 分母と省略 | observed/unscored_target/outside_testのaccounting、event-offsetを排他的partitionと扱わない |
| primaryとの結合 | recall/precision/availability/false-alert/clean counts、profile、検出済みdelay multiset |
| 集計・本文 | core/quality-stress/overallのcountの和、本文1,233行 |
| 補助診断 | 4系列2,835行、詳細9表、histogram・露出時間・profile・省略件数 |
| null | ゼロ分母はvalue=null・CI=not_applicable、検出なしのdelayはnull、CIを捏造しない |

集計は固定座標ごとの和をとり、delayは整数秒のmultisetを展開してmedian/mean等を計算する。計算側の再帰的加算や累積histogramの順位検索は再利用しない。delay展開は最大19,200件に制限する。固定ラベルを含む全行を比較するため、行数・合計だけが同じでも別cellへの割当や重複/欠落を見逃さない。

純粋関数は`audit_slices(fixture, slice_input, document)`。主表の全CI/gateは別のprimary auditが受け持ち、所有workerの新operationでは両方が成功する必要がある。`success_summary`は親が必要な成功主張とdigestを保持するための関数で、これだけでは検算しない。

## 所有auditの入力

入口は`audit_with_evidence(request, *, expected_revision, receipt_parent, receipt_name, budget_limits=None, resource_budget=None)`のまま。mode=fixture、role=audit、request formatも維持する。

| operation | 入力数と合計上限 | 出力名 |
| --- | --- | --- |
| `audit-invented-primary-numerics-v1` | 従来5入力、6MiB | `payload/primary-audit.json` |
| `audit-invented-primary-and-slices-v1` | 従来5入力＋`fixture/slices.json`、14MiB | `payload/primary-and-slices-audit.json` |

追加slice入力の上限はanalysis側と同じ8MiBで、canonical JSON、絶対path、外部保持pin、links=1を要求する。新operationの14MiBは6＋8MiBの入力読取り範囲。既存operationの上限や実行時間・directory予算を引き上げたものではない。operation descriptorは`operation_descriptor(revision, analysis_reference, operation=SLICE_OPERATION)`で作り、requestと一致させる。

元analysisの外部result/evidence pinとsource revisionを起点に、実行記録にある`fixture/input.json`と追加`fixture/slices.json`のpin、文書pin、完了記録を照合する。slice入力のpinだけ更新し、元analysis記録との結合を外すことはできない。元receiptの完全な再認証を行う入口ではないため、呼出し側が保持する保存点の由来を維持する。

親は数値・sliceを再計算せず、固定の成功要約と入出力期待pinを起動前に保持する。子が主表とsliceの両方を検算し、成功時のみ新しい出力名で保存する。選択sourceは15本、Python本体/DLLは2file、新operationの入力は6file。sourceとruntimeの前後観測、元Popen handleと子のPID/生成時刻、終了/reap、出力pinを既存evidence validatorへ結ぶ。

## 結果と停止

新operationの成功は`status=verified`、`fixture_numerical_audit_performed=true`、`fixture_slice_audit_performed=true`。出力はformat=`anomaly-v03-fixture-primary-and-slices-audit-v1`、status=`primary_and_slice_numerics_matched`。既存主9表/180gateの情報に`slice_audit`の範囲と入力digestを加える。旧primary-only receiptへこのフラグを遡って追加しない。

[限定資源監視](anomaly-v03-fixture-resource-budget.md)を維持する。共有120秒・親512MiB・directory32MiB/256entries/深さ8、commit/RAM余裕各2GiB・disk5GiB、子60秒/256MiB/stdout+stderr1MiB。新しい共通rootに保持入力とaudit出力を置き、同じmonitorを渡せば合算できる。sampling/協調停止の限界も維持する。失敗時は自動再試行・予算拡大・元成果物の削除を行わない。

## 残る境界

この検算は**渡された架空countからの集計・mapping**を対象とする。raw producer観測からそのcountが正しく導かれたこと、登録coverage、正式50,000反復、正式slice mapping採択、5payloadの公開、全source/runtimeの受入は対象外。結果に明記し、formal/promotion/S6/closureはfalse、文書の正式null4欄とready=falseを維持する。

次は生成済みの5payloadを通常公開・別readerへ接続し、今回のaudit範囲とwriterの実行記録を結ぶ。旧4payload公開の繰返しだけで新5payloadの確認を代替しない。登録holdoutや正式gateを起動する工程ではない。
