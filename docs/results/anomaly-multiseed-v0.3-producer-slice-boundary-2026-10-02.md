# 架空producerの補助集計入力を最新試行へ結合

2026-10-02 JST。[API](../anomaly-v03-producer-slice-fixture.md)。各評価のincident/score/context内訳を主入力と同じ登録・試行receipt・入力hash・要約pinへ結合した。最新attemptだけを集計し、未完了なら主coverage/失敗を保持して補助集計を返さない。

開始c60f86747339f5d9011b1936adc7ce844499ce01、実装bde59a7a98bd2ed1f5c263458a1ddf1e28211268、clean候補ps01/banto-ai。OUT artifacts/producer-slice-boundary-2026-10-02、tests-1/full-invented-example。最終文書revisionと80code/18data/成果物pinはsavepoint-evidence.jsonへ保存する。

前保存点producer-input-boundary-2026-10-02/savepoint-evidence.jsonは23,536bytes/SHA256 b7982e3d93125099e8668c1dd1a09f18f6994b546321ca6cb8cb43af11ecb12c。前の架空主入力3fileをそのpinから再利用し、実評価データを読まない。

## 機能試験と資源停止

新21項目はfailure/error/skip0、82.665秒で全pass。ただし同じ試験実行の資源監視はpipeline_commit_headroomで失敗。システムcommit余裕の最小値5.20MiBが2GiB下限を割った。試験processのpeak privateは86.71MiBであり、他processの内訳や因果は確認していない。ユーザーから別Bantoリリース処理の同時稼働が報告された。

[機能試験結果](../../artifacts/producer-slice-boundary-2026-10-02/tests-1/test-results.json)、[ログ](../../artifacts/producer-slice-boundary-2026-10-02/tests-1/tests.log)、[試験の資源診断](../../artifacts/producer-slice-boundary-2026-10-02/tests-1/resource-budget.json)。外部pin、行/列encoding、全inventory、別枠/別attemptへの差替え、主集計との一致、合計を保った分類先変更、遅延分布、profile、省略理由、失敗/未開始/履歴、上限、I/Oなしを検査した。

監視の停止理由は保持され、最後のcheckpointで失敗として確定した。純粋関数内を強制中断するhard quotaではなく、この実行では機能assertionが終わるまで進んだ。21件の機能passを資源passへ読み替えない。試験コード/候補は変更せず、機能試験の反復は0回。

資源回復を確認し、元verify-initial.py・失敗したresource-budget.jsonを保全して、[再開記録](../../artifacts/producer-slice-boundary-2026-10-02/tests-1/resource-stop-recovery.json)を保存した。[同時稼働の申告](../../artifacts/producer-slice-boundary-2026-10-02/concurrent-release-context.json)は状況記録であり、原因の特定ではない。他のprocessを変更/停止せず、上限も据置き。以後は保存例1回と保存作業だけを行った。

## 保存例

40架空cluster/480区間/2,880枠の主入力に、2,880件の補助payload/12,265,920bytesを追加。両manifestと両側payloadの合計22,831,115bytesは32MiB以内。全外部pinと各評価単位の整合性を照合し、3候補×2層×40 clusterの240セルへ結合した。各セルは12 layout分を加算した既存slice-input形式である。

最新success2,879＋inconclusive1、主側の旧失敗attempt1件、ゼロ分母、対象外signal/試験範囲外の省略、zero cellを保持。保存例の旧失敗は未完了slotのみのためhistorical_summary_countは0。別の機能試験では旧失敗attempt内の成功summary1件も照合し、合算に入らないことを確認した。

[保存例の結果](../../artifacts/producer-slice-boundary-2026-10-02/tests-1/full-invented-example/result.json)、[結合出力](../../artifacts/producer-slice-boundary-2026-10-02/tests-1/full-invented-example/bound-slices.json)、[形式検査](../../artifacts/producer-slice-boundary-2026-10-02/tests-1/full-invented-example/compatibility-check.json)。所要67.880秒。主集計の純粋な結合/加算を新補助入力と合わせて検査したが、旧実評価の再計算や数値推論・文書生成・公開は行っていない。

| 保存対象 | bytes | SHA-256 |
| --- | ---: | --- |
| slice-manifest.json | 482,429 | b208043df9fddb9a1eaec06d2f17e340358f157c26bb753d0577f16113eaaa0a |
| slice-snapshots.jsonl | 12,891,840 | c57cd1aba6a0ecf2c76761a21cd85692997bd45a0849ebb089f6ae1d77509f00 |
| bound-slices.json | 13,277,817 | a3e98c14fb800cc835976ddff7798efa5126df9968bfcd48860a0ca432834d48 |

JSONLは論理pathと正確なraw UTF-8 bytesをまとめた容器。2,880個の実ファイルを作らず、保存終了時も容器のpin/inventoryを照合する。旧主入力3fileは複製せず、元保存点のpath/pinを参照する。

## 保存例の資源と残件

[保存例の資源監視](../../artifacts/producer-slice-boundary-2026-10-02/tests-1/full-invented-example/resource-budget.json)は165sample、errorなし/終了確認済み/pass。親peak private99.51MiB、directory最大25.42MiB、commit最小余裕27.19GiB。120秒/512MiB/32MiB/256entries、RAM/commit余裕2GiB、disk余裕5GiBを維持。監視中の最大容量は最終診断ファイル込みの成果物総量とは区別する。

保存例後RAM空き16.59GiB、C/D空き115.66/365.90GiB。最終値とOSはsave-checks.json。OS25H2/26200/9457を観測し、旧formal9168は維持。短い観測からメモリリークの有無は断定しない。

主入力v1と旧78code/18dataは不変、新module/test2本で計80code。実観測読込み・新評価・既存720評価の再実行・数値推論・owned worker起動は0。登録観測からの導出、実producer/source/runtime認証、正式契約・全体予算の受入は残る。formal/promotion/S6/trust/execution_authenticated/full closure/analysis_authorized=false、正式null4欄/ready=falseを維持。 過去の試験結果を今回revisionの全回帰passとは表現しない。

次は外部pinで結んだ主入力と補助入力を、既存の限定fixture解析/audit経路へ接続する。供給記録から文書・別検算までの対応を確認し、旧720評価や正式holdout・50,000反復は起動しない。 raw観測から分類・score・episode/matchingを正しく導出したことの受入は別。Phase2/3全体は未完了。

実計算c01d1c9/main6f1285d/closed/既存dirty文書・旧候補/成果物は不変。banto-24 PAUSED、principal/保護root/UAC/ACL/同時書換え保留、Windows3.12必須化なし、push/mergeなし。
