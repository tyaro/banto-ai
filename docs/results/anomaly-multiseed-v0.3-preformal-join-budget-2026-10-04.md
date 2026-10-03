# v0.3 架空producer要約・slice結合の連続予算測定（2026-10-04）

状態: **未commit作業ファイル上の暫定限定測定、正式全工程予算は未採択**。基準HEAD `294bf02` 上で、新しい[測定fixture](../../tests/fixtures/anomaly_v03_preformal_join_budget.py)を使い、架空40 clusterの宣言生成から主・slice結合、解析子へ渡す1 drawの4入力ファイル投影までを同一process・同一監視rootで直列に通した。新fixtureのraw sourceは前後pinで照合したが、a1/a2時点ではまだGitにcommitされていない。a2 receiptの `source_revision` は投影descriptorへ渡した基準HEADであり、新fixture実装の固定revisionではない。clean保存点後の別root測定を残す。これは正式producerの2,880評価を実行した記録ではない。登録holdout観測、保存済み登録評価reader、所有analysis/audit子、50,000 draw、writer/readerは起動していない。

## 測定の停止条件と入力

測定専用ID `anomaly-v03-preformal-join-budget-v1` と新root名を固定し、既存rootを再利用しない。入力は[test fixtureの生成器](../../tests/test_anomaly_v03_producer_input_fixture.py)と[slice生成器](../../tests/test_anomaly_v03_producer_slice_fixture.py)による架空宣言で、主snapshot 9,122 file・8,679,400 bytes、slice snapshot 2,880 file・12,265,920 bytes。2つのmanifestは1,397,614 / 482,429 bytes。12,004要素をzipに保持し、外部pin、結合結果と投影ファイルのpinをreceiptへ保存した。作業ツリーのcleanを要求する所有子境界は実行していない。選択した6つのfixture source raw pinだけを前後で比較しており、5役割の依存閉包を主張しない。

共通監視は90秒、親peak private 384 MiB、root論理24 MiB・32 entry、system commit/RAM最低余裕各2 GiB、D空き最低5 GiBで停止する。各工程の前後にcheckpointがあり、250 ms標本の協調的制御である。測定本体は単一Python processで、基準HEAD取得に短命Git helperを使う。所有workerのtime/private/exit/reapは測定対象外。zipは12 MiB、結合出力8 MiB、投影ファイルは既存の入力上限を適用する。

## 保存結果

| 試行 | 結果 | 保存証拠 |
| --- | --- | --- |
| 予備確認 | 保存しない手動呼出しで、40 clusterの結合と投影が約39秒、4 file 4,626,522 bytesとなることを確認。予算receiptではない | 新rootなし |
| `a1` | 初回のzip上限8 MiBに対し実10,043,705 bytesで安全停止。`status=failed`、wall 5.353秒、結合・投影未開始。監視はpassし、失敗rootを保全 | [失敗receipt](../../artifacts/anomaly-v03-preformal-join-budget-20261004-a1/receipt.json) |
| `a2` | zip上限だけを12 MiBに修正した別rootで、4工程完走。`status=measured`、共通wall **37.765秒**、監視pass/101標本。ただし新fixtureは未commit | [暫定成功receipt](../../artifacts/anomaly-v03-preformal-join-budget-20261004-a2/receipt.json) 4,884 bytes / SHA-256 `1f200d6ed6a579ac6627f4e6cd89fc6ba121a33d8a798174d0e2c062c5b6f3cc` |

a2の工程wallは架空入力生成2.476秒、zip保持1.565秒、主・slice結合29.557秒、1 draw投影2.698秒。zip 10,043,705 bytes、結合結果5,148,721 bytes、投影4,626,522 bytesを外部pinで再読取した。root最終は10 entry・論理19,825,539 bytesで、監視中の最大は8 entry・19,818,948 bytes。親peak private 111,366,144 bytes、system commit最低余裕14,417,719,296 bytes、空きRAM最低9,618,980,864 bytes、D空き最低407,569,788,928 bytesだった。監視rootの値とzip内部file数は別の数え方であり、zip内部12,004要素をroot directory entryとみなさない。

新規[境界試験](../../tests/test_anomaly_v03_preformal_join_budget.py)4件がpass。rootの逸脱・再利用拒否、preflight失敗receipt、保存pin改変拒否、選択sourceのHEAD raw照合を確認した。`git diff --check` はpass。

この測定は[全工程予算の閉包案](anomaly-multiseed-v0.3-preformal-end-to-end-budget-closure-proposal-2026-10-04.md)の工程1の**架空宣言生成・純粋結合**と工程3の**1 draw入力投影**にだけ対応する。実producer活動時間、登録保存reader、正式同形の解析全文書、独立S6、5payload公開、別reader、全役割に共通する停止・再開上限は未測定であり、別環境・別入力の[50,000 draw算術receipt](../../artifacts/anomaly-v03-preformal-draw-budget-2026-10-04-17873fd-01/receipt.json)と加算・外挿しない。`formal_permission=false`、`independent_s6_complete=false`、`promotion_allowed=false` を維持する。clean保存点後に同じ上限・別rootで再測定し、選択6 sourceの作業rawがHEAD blobと全一致した場合だけ `source_revision_scope=selected-working-raw-matches-head-blobs` を記録する。これは全依存閉包ではない。
