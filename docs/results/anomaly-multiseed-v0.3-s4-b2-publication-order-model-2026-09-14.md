# S4-B2 残存権限・完了印のpure model結果

2026-09-14、基準5826995638f79757db7e630a46d427bc6d9d1c66。
実装savepoint **39cac0d947bbb51cd2079af416edce1c01fc23b9**。
[未採用の順序案](../anomaly-v03-publication-order-options.md)に対応する、IOをしない別modelを実装した。
[設計](../anomaly-v03-publication-order-model-design.md)と[前回の実機結果](anomaly-multiseed-v0.3-s4-b2-same-parent-rename-2026-09-14.md)を参照。

隔離の根拠が不明なら、既知の別actorが0で最終照合が全て一致していても、完了印の書込み開始を拒否する。
新規20件＋既存182件＝**202件pass/0.205秒**、failure/error/skip/expected failure/unexpected successは全て0。
実装・試験・設計の独立レビューは新規P0〜P3=0、read-only、進捗ポーリングなし。
これは条件不足と故障時の扱いを検証した結果であり、実OSの隔離成立や方式採用を認定していない。

## 確認した動作

| 対象 | modelで確認したこと |
| --- | --- |
| 既取得の親権限 | 最大8 handleのadd_child/delete_childを保持し、親固定で消さない。発見と変更を合計32件まで記録 |
| 最終検査の後の変更 | epochを進め照合を失効させる。停止後・仮想公開後も外部変更を記録し、publisherの再開は認めない |
| 隔離の未解決 | peerが0でも書込み拒否。assume_isolated_for_testは後段故障用の反実仮想に限り、既知peerがあればなお拒否 |
| rename応答喪失 | unknownとして後続の親固定・marker書込みへ進ませない |
| marker書込み | 固定した最大16KiBのtoy bytesとexact prefix/残量を照合。全量前のflush/close、工程飛越し・繰返しを拒否 |
| write intent後の故障 | 部分/全量/flush/close応答前までunknown。最初の失敗を保ち、後発の資源停止を昇格 |
| 仮想close完了後 | confirmed_model_onlyの履歴を保つ。後発の変更は現在の確認を失効させ、将来の不変性を認めない |
| 読み手の単発分類 | absent/共有違反/空はnot_ready、部分はincomplete、読取り失敗や照合欠落はindeterminate、不正bytes/不一致はinvalid |
| 完全なmarker | namespace/ID/payload bytes/SDの4照合も全て一致して初めてsnapshot_matches。保護済みcommitとはしない |
| producerとの関係 | 完全writeの応答喪失によりproducerがunknownでも、consumerには完全bytesが見える場合を扱う |

markerのpin、各照合結果、固定やcloseの応答はsynthetic入力であり、真正性・同時性・実所有終了を証明するものではない。
全出力でprotected_commit_allowed/future_immutability_proven/native_publication_performed=false。
既存6工程model、native adapter/entry、S3/D2/productionは変更しない。新規native試行は0、監視process・別checkoutも追加していない。

## 保存記録

ignored artifacts/publication-order-model-2026-09-14/へ記録した。
initial-checks.jsonlが最終試験根拠。30 source＋補助2 filesのraw bytesが試験記録・作業領域・実装Git blobで一致する。
repository safetyと差分空白検査はpass。試験後のコード変更・重複試験はない。
前回same-parentのmanifestと記載された18 artifactsのhash不変を照合した。旧失敗sourceは再検査・hash取得・複製・再利用・削除していない。

| 記録 | bytes | SHA-256 |
| --- | ---: | --- |
| initial-checks.jsonl | 147351 | a58d9f063229a26004e87a5a190aa84d697bf4ea8966c8f3dc3d870804875407 |
| savepoint-evidence.json | 9006 | c5f2844abdf7bbbc9fdcaf32497e8819b64e17c40fc1fc72eeceb5ee936896e6 |

manifest以外6 artifactsの論理bytesは193851。filesystem全占有量ではない。
既存の親policy結果書の作業差分は8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621のまま保存し、今回commitから除外した。
元の保存bytes/patchは前回same-parent記録に残る。差分を消してcleanにしない。

## 資源と次の作業

試験前UTC10:48:30は空きRAM13.55GiB/C118.93GiB/D74.23GiB、試験後10:52:01はRAM13.38GiB/C118.92GiB/D74.23GiB。
build26200.9445/boot2026-09-09T10:43:08.5000000+09:00。Windows Update engineering緩和を維持し、正式pinは変更しない。
試験processは終了し、新規常駐処理なし。この2点はprocess最大使用量・長期リーク不在の証明ではなく、空き容量変動の原因も特定しない。

次は別actorの事前取得を防ぐ生成/隔離条件、または残存権限があっても変更できない操作境界の根拠を具体化する。
実consumerの一貫した観測・共有違反の有界な扱い、marker writerの権限/寿命も未実装。
別actorを脅威範囲から除外せず、仮想隔離flagを実機での隔離認定に使わない。根拠不明のまま候補のnative publisherへ進まない。
既存の受入契約に触れる点は、具体案を作って判断対象にする。
親全保護、marker/全publisher、独立token、native故障/競合、正式OS整合、VM digest、runtime closure/consumer、B2/S4受入は未完了。
formal_permission/execution_authenticated=false、acceptance_status=not_completed。本流889cfc3・正式pinは不変、旧CI件数へ加算しない。
旧batch/B1再開、push/merge/CI、新runtime/サービス/account、別projectへの操作なし。
