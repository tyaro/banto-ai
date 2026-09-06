# event-aware anomaly multi-seed evaluation v0.3 S3監査結果

状態: **S3完了 / 独立監査合格 / formal run未実施**
監査日: 2026-09-07
実装基準commit: `dc522661a1ea19c7269ab40485bd19caca50cf8e`
親commit: `bb42d37f541e56b234a30a5ce88ff9999755f567`

## 経営層向け要約

S3は、実験を安全かつ再現可能に実行するための土台を完成させた工程です。固定した組合せを漏れなく処理し、途中障害が起きた場合も確認済みの証拠を保全して止まれることを確認しました。これは性能結果ではなく、モデルの優劣・本番利用許可・顧客設備への展開を示しません。

次のS4で、正式なWindows runtime受入、dry/smoke、独立consumer freezeを完了するまで、formal dev/smoke/holdoutの実行権限と正式出力rootは閉じたままです。顧客データは使用していません。

## 結論

| 判定 | 結果 |
| --- | --- |
| `S3_READY` | yes |
| `INTEGRATION_READY` | yes |
| P0 / P1 / P2 / P3 | 0 / 0 / 0 / 0 |
| 性能結果・winner・promotion | 未評価・未決定 |
| formal dev/smoke/holdout run | 未実施 |
| 正式output root | S4受入まで閉鎖 |

S3の判定は、deterministic runner、共通materialization、台帳、来歴、公開境界とその攻撃試験に対するものです。`S3_READY=yes`を性能達成や本番利用承認へ読み替えません。

## 実装の来歴

S3実装は、次の4コミットを経てmainへ統合されています。

1. `bdd59c5` — v0.3 deterministic runnerの初期実装
2. `2a01146` — I/O境界でfail closedする修正
3. `bb42d37` — 例外グラフ、停止後I/O、回復証拠境界の強化
4. `dc52266` — `CellFailure`に包まれた整合性・契約・割込み原因の全体停止分類

最終基準revisionは`dc522661a1ea19c7269ab40485bd19caca50cf8e`です。S3の科学・実験仕様は既存の凍結planを変更していません。

## S3で確認した機能

- 固定されたseed、layout、stratum、candidateの組合せ一覧と、960 datasets／2,880 evaluation slotsの固定inventory
- 対になるcandidateへ同一の保存済み入力bytesを供給するpaired materializationとhash照合
- success、partial、inconclusive、failed、not_startedを含む全枠の実行台帳
- I/O、root、入力変更、契約違反、割込み、公開境界の障害時に安全停止し、後続枠を`not_started`として保持
- 確認済みの入力hashとevidenceを、回復処理や例外ラップで上書き・水増ししない境界
- 例外のcause／context／ExceptionGroup全枝を走査し、整合性・契約・割込み原因を通常の候補失敗へ降格しない分類
- source、plan、runtime、入力bytesを結ぶprovenanceと、atomic／non-overwrite publication境界
- 停止後に安全性を失った保存領域へ再アクセスせず、完全なメモリ上台帳を返す停止経路

formal output root、formal artifact、独立analysis／audit rootはS4受入まで作成・公開しません。

## 検証結果

### CI

GitHub Actions [run 34044283016](https://github.com/tyaro/banto-ai/actions/runs/34044283016) は、Python 3.12／3.14の全工程をgreenで完走しました。所要時間は3.14が15分15秒、3.12が16分21秒です。共通契約、runner攻撃試験、safety、manifest、consumer境界を両環境で確認しています。

### ローカル

Windows CPython 3.14での新規全体探索は、`Ran 686 / 3667.360s / FAILED (errors=1, skipped=2)`でした。内訳は、684件成功、既存のartifact不在によるskip 2件、`SavedEvaluationTests.setUpClass`の`compute_evaluation`中に`copy.deepcopy(scores)`が発生させた`MemoryError` 1件です。このセットアップエラーにより、同classの5試験は未実行でした。

同classだけを新規プロセスで再実行した結果は5/5 PASS（809.438秒）でした。したがって、今回の`dc52266`の変更に由来する欠陥とは確認されていません。ただし、ローカルでの根本原因、失敗時のpeak memory、commit limitは未解決です。全体探索の失敗を「全体green」「環境原因確定」「test-only」とは扱わず、S4受入前の容量確認と同一revision再確認事項として残します。

S3専用のmaterializer／runner／publication／provenance suiteは73/73 PASSでした。これは全体探索のMemoryErrorを隠すものではなく、S3変更範囲を独立に検証した結果です。

## 残る制約と次段階

S3は、性能指標、candidate winner、promotion、実設備一般化、本番利用許可を判定しません。formal観測の生成・採用、独立analysis、独立audit、bootstrapと性能gateも未実施です。

次はS4です。

- platform/runtime/native Windows acceptance
- dry/smokeと独立consumer freeze
- 正式pin、source/runtime inventory、容量、再現性、consumerの確認
- GitHub CIのgreen結果と同一revisionのローカル受入確認

S4完了まではformal dev/smoke/holdoutの実行権限を与えません。S4の受入後に初めて、計画に定めた正式実行の可否を再判定します。

## 参照

- [v0.3凍結計画](../anomaly-multiseed-evaluation-plan-v0.3.md)
- [v0.3 S0計画監査](anomaly-multiseed-v0.3-plan-audit-2026-09-06.md)
- [v0.3 S1監査](anomaly-multiseed-v0.3-s1-audit-2026-09-06.md)
- [v0.3 S2監査](anomaly-multiseed-v0.3-s2-audit-2026-09-06.md)

この文書はS3完了後のliving audit recordです。凍結planや過去のS0〜S2 result本文の時点記録は遡及修正していません。
