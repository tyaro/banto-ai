# S4-B2 残存権限と完了印のpure model

2026-09-14、基準5826995。[未採用の順序案](anomaly-v03-publication-order-options.md)を、IOしない別modelとして具体化する。
tests/fixtures/anomaly_v03_publication_order_model.pyだけに実装し、既存6工程model・native entry・S3/D2/productionは変更しない。
新規native枠、DLL、file操作、サービス/account/runtime追加はない。

## 権限と確認時点

最大8個の別actorの既取得parent handleを、抽象IDとadd_child/delete_child権限集合で記録する。
この集合はseal_parentでも消さず、publisherから失効/忘却/隔離認定を行うAPIを設けない。
固定後に発見した既取得handleも記録できるが、固定後に新しく開けたとは主張しない。
実Windowsでどの操作がこの保持権限を使えるかを証明するものでもない。
handle発見と外部の追加/削除を合計最大32件の保守的な仮想イベントとして扱い、publisher停止後や仮想公開後にも記録できる。

handle発見/外部変更ごとにepochを進める。最終一致確認はそのepochにだけ対応する。
後からpeerを発見した場合は確認を古いものとし、既に書込み段階なら停止して公開をunknownにする。
仮想close完了後の変更では、その時点のclose応答履歴は保ちながら、現在の確認・将来の不変性とは区別する。
確認前に既知の外部変更があれば、callerが一致flagを全てtrueにしても新fixtureなしで再認定しない。

隔離の既定はunresolved。既知のpeerが0でも、最終inventory/ID/bytes/SDが一致してもmarker書込みへ進まない。
assume_isolated_for_test=Trueは後段故障を試すための反実仮想だけで、観測された隔離根拠ではない。
この仮定があっても既知peerが存在すれば書込みを拒否する。仮定の取付け/差替えAPIは設けない。
仮想正常終了はconfirmed_model_onlyであり、protected_commit_allowed/future_immutability_provenは常にfalse。
実権限の隔離を証明・認定する機能は未実装である。

## 順序・不明応答・終了

準備→子固定→rename intent/応答→親固定→最終確認→marker write intent/部分応答→flush intent/応答→close intent/応答を扱う。
準備/固定/確認はtrusted synthetic acknowledgmentであり、実OS操作や所有終了の証明ではない。
markerは外部でpinされた小さいtoy bytes（最大16KiB）。callerから任意の無制限streamを受け取らない。
write応答は残り長以下のexact prefixだけを認め、全量前にflush/closeへ進まない。

| 停止位置 | markerのmodel上の扱い |
| --- | --- |
| write開始前 | not_started。有効bytes書込みをモデル上で始めていない |
| write intent後/部分/全量/flush/close応答前 | unknown。応答を受けていない完全writeの可能性を排除しない |
| close応答確認後 | confirmed_model_onlyの履歴を維持。後発失敗・peer変更があれば現在の状態は停止/確認失効 |

rename intent後の停止もunknownとしてseal/markerへ進ませない。工程skip/repeat/停止後のpublisher再開は拒否する。
最初の失敗object/理由を保ち、後発のresource stopは昇格する。resource停止後も通常snapshotが必ず割り当て可能とはしない。
外部peerイベントを記録できることは、停止したpublisherのIO再開許可ではない。retry/cleanupはfalse。

## consumerの単発分類

classify_markerはsyntheticな1回分のread結果と外部pinを分類する。native read、polling、再試行はしない。
markerの存在だけで成功を返さない。rawはbytesに限定し、最大16KiBを超えた観測は追加parse/hashなしでinvalid。
raw markerがexact一致しても、namespace/ID/payload bytes/SDの各観測が不足ならindeterminate、falseならinvalid。
全てtrueならsnapshot_matchesに限る。観測の真正性・同時性や将来不変性をこの関数が証明するわけではない。

| 観測 | 分類 |
| --- | --- |
| absent/sharing violation/空marker | not_ready |
| read error | indeterminate |
| pinの一部とだけ一致するmarker | incomplete。準備中かcrash後かは断定しない |
| 異なるmarker/余分bytes/上限超過/不一致観測 | invalid |
| exact marker、照合情報に欠落 | indeterminate |
| exact markerと4種類の照合結果が一致 | snapshot_matches。保護済みcommitや正式受入ではない |

producerが完全writeの応答を失い公開unknownでも、consumerにはexact bytesが見える可能性をモデル化する。
producerの失敗を根拠に未公開と決めたり、consumerの一致を隔離成立と決めたりしない。
全出力はformal_permission/execution_authenticated=false、acceptance_status=not_completedを維持する。

## 次の境界

このmodelは「どの条件が不足しているか」を示す部品であり、隔離の仕組みそのものではない。
別actorを脅威範囲から除外せず、既取得権限の失効を仮定しない。
次は事前取得を防ぐ生成/隔離手順、または保持権限があっても変更できない操作境界の根拠を具体化する。
現実のconsumerの一貫した観測・共有違反の有界な扱い、marker writerの権限/寿命も未実装。
根拠不明のまま候補のnative publisherを作らず、既存の正式契約変更が必要な点は具体案として判断可能にする。
