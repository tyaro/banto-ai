# consumer接続の到達範囲と容量・時間の見積り（2026-09-25）

[契約案](../anomaly-v03-consumer-io-proposal.md)のT01〜T12を、[engineering consumer入口](../anomaly-v03-engineering-consumer.md)までの実装へ対応付けた。**engineering接続済み5群、保存済み検証の再利用3群、計算部品まで1群、受入・外側状態・別reader/auditの接続が残る3群**。この区分は正式評価の合格数でも、Phase2/3全体の残件数でもない。

対象revision `6af1c024be52c063e82f9a43143f2fc5e228258b`、OUT `artifacts/consumer-coverage-budget-review-2026-09-25`。今回は文書・保存記録の整理だけで、sourceや科学条件を変更していない。最終revision/pinはOUTのsavepoint-evidence.json。

## 12群の対応

| ID | 現状 | 確認できたこと | 残る接続 |
| --- | --- | --- | --- |
| T01 | engineering接続済み | 正式modeをI/O前に拒否。fixture/engineeringの区別を保持。 | 将来の登録済み正式契約・受入証拠との結合。 |
| T02 | engineering接続済み | 外部pin、明示path、公開印・固定inventoryを認証。 | 正式対象の全payload/producer終了までの一貫した入口。 |
| T03 | engineering接続済み | 全120区間720枠・順序・候補間の入力pin対応。 | 正式40 seed/480区間2880枠へ別adapterで接続。 |
| T04 | engineering接続済み | 過去失敗を残し最終attempt採用、inconclusiveをsuccess化しない。 | 正式失敗時の別version/root/未使用seedによる再登録規則。 |
| T05 | 保存済み検証を再利用 | 720評価の独立観測/score/ledger・生成検算を保存点から再利用。 | 新しい正式観測から独立auditへ渡す経路。既存720件の再検算は不要。 |
| T06 | 保存済み検証を再利用 | 10 cluster・元count/null・両層/layout対応を保持。 | 40 clusterの完全性と推論入口への結合。 |
| T07 | 計算部品の検証まで | 共通draw・ratio-of-sums・type-7・gateの既存手例。 | 正式40 cluster・50000 draw・180 gates・C1優先選択のfull document。 |
| T08 | 保存済み検証を再利用 | 記述18表・4系列5670行と対象外参照を保持。 | 主slice1233行/sidecar2835行の正式mapping採択と接続。 |
| T09 | 正式受入の接続が残る | 正式受入フラグをfalseに維持。旧readinessは履歴。 | clean source/runtime依存閉包・full schema/意味受入。 |
| T10 | engineering接続済み | 単一writerの新規保存、callback、途中失敗保全、非上書き。 | 正式wrapperのexecution/coverage/analysis/diagnostics/verification保存。 |
| T11 | 外側状態の接続が残る | 保存部品は応答消失でも既存markerを撤回しない。 | consumer外側の応答消失/公開後読取失敗の状態・外部receipt回復。 |
| T12 | 別reader/auditの接続が残る | writer終了後、同じprocessのreaderで全出力bytesを確認。 | 別process readerと独立意味audit、再封印した不整合への外側判定。 |

元契約案の12参照と追加18参照、計30件のtest methodが現sourceにあることをASTで確認し、正確なfile/行番号/raw pinをcoverage-map.jsonへ保存した。入力validator22、adapter新規15、公開reader14、集計結合14、入口16の計81新規試験は各工程の保存済み合格記録。adapter工程で再実行した既存22件を重複加算していない。**今回の試験実行は0**。旧独立算術・保存試験も再実行せず、参照とsource bytesを確認した。

T11/T12の次の作業は、通常権限・単一writerを維持して、writerが閉じた後の別process readerと外側の確認receiptを接続すること。表示や監査の不一致を外側に保存し、確定payload/markerを修正しない。保存部品の応答消失試験を作り直す必要はなく、consumer接続の小さな固定入力と拒否例へ絞る。保留中の専用principal・同時書換え試験の再開は含めない。

## 5まとまりの残件更新

| 作業 | 現在地 | 次の完了条件 |
| --- | --- | --- |
| 1. 正式運用契約 | 単一writer・OS実値記録の契約案はdraft | slice対応、Windows更新許容範囲、正式失敗時の再登録規則、対象revisionを揃え採択する |
| 2. 正式consumer入出力 | engineeringの保存済み記述結果を選択・出力する入口は完了 | 正式40 cluster/固定推論/full documentへのadapterを架空入力で検証。実holdoutで実装調整しない |
| 3. source/runtime受入・固定 | 旧証拠と今回のsource33件は一致。完全依存閉包は未確定 | 入口実装確定後、clean checkoutでraw source・runtime閉包・必要なplatform回帰を固定する |
| 4. 公開と独立reader | 通常保存・同一processでの順次読取は接続済み | T11/T12の外側状態と別process readerを接続し、正式analysis/audit別rootへ拡張する |
| 5. 容量・時間・停止予算 | 下記の実績と外挿、仮の予算枠を作成 | 未接続の正式推論/最終独立監査の予算を補い、実行前の空き資源と停止条件を固定する |

5まとまりはすべて正式化の残りを含む。直近は4の通常権限の接続を進められる。1/2/4が揃ってから3の最終freezeへ進む。正式gate・holdout・50,000回の実データ推論は起動していない。

## 保存済みの実測と外挿

完走保存点の7800 fileのサイズ索引を合計し、16,081,676,236bytesとの一致を確認した。これは失敗attemptやhardlink名も含む当時の論理bytesで、現在の物理ディスク使用量の走査ではない。全payloadの再読取りはしていない。

| 対象 | 保存実績 | 正式対象への単純外挿 |
| --- | --- | --- |
| 対象数 | 10 seed、120区間、240 datasets、720評価 | 40 seed、480区間、960 datasets、2,880評価 |
| run保存量 | 約14.98GiB（16.08GB） | ×4で約59.91GiB（64.33GB） |
| 累積活動時間 | 160,357.174秒、44.54時間 | ×4で約178.17時間、7.42日 |
| 別工程のprofile/score/ledger監査 | 119区間を新規検算＋1区間の既存検証再利用、1,196.096秒 | 480/119倍で約80.41分 |
| 別工程の生成/丸め監査 | 120 pairs、113.560秒 | ×4で約7.57分 |
| 今回までの記述結果入口 | 保存7file/7,896,608bytes、約2.055秒 | 正式推論とは処理が異なるため外挿しない |

累積活動時間は再開時の再照合・失敗時間を含み、呼出し間の休止や外側の一部処理を含まない。固定長・同じ候補数・逐次実行という仮定のシナリオであり、終了日時の予測や性能上限ではない。高速再開による短縮と、負荷/seed差による延長の両方があり得る。

別工程の約88分は生成・score/ledgerの検算分だけ。正式CI/gate/選択と最終独立auditは未接続で、合計の確定予算はまだ作れない。実データbootstrapを今回動かして見積りを埋めることはしない。

## 仮の予算枠と資源条件

以下は検討用シナリオで、既存48時間/32GiB、producer900秒/2GiB、audit600秒/1GiBなどの設定は変更していない。

| 仮置きする項目 | 値と考え方 |
| --- | --- |
| producer/controllerの累積活動時間枠 | 240時間（10日）。178.17時間の外挿を切り上げた余裕枠。正式解析/最終auditと休止時間は別途必要 |
| 新規run出力の論理上限 | 96GiB。約59.91GiBの外挿に失敗保全・形式差・報告増加等の余裕を置いた案 |
| volumeに残す空き | 32GiB。OSや他作業の余裕として仮置きし、実測必要量とは扱わない |
| 1コピーで開始する空き | 96＋32＝128GiB以上 |
| 同一volumeに同規模の2コピーを保持 | 96×2＋32＝224GiB以上。コピーの実行や保存先の変更は今回行わない |
| 正式推論・最終独立auditの時間/メモリ | 未確定。上記枠を根拠に実行許可へ格上げしない |

今回の資源標本ではC空き121.97GiB、D空き256.05GiB。上の案ではCは1コピー用128GiBを下回り、Dは候補になる。空き容量は変動するため正式開始直前に再確認が必要。前工程のD268.83GiBから減少しているが、今回の出力はC上の小型metadataであり、PC全体の変動原因はこの調査で特定していない。

過去の区間119 attempt1ではproducer900秒上限に達し、同時期にシステムcommit余裕52.73MiBが観測された。失敗worker peakは326.05MiB、controller peak226.75MiB。個別processが小さくてもシステム全体の余裕が不足し得る。割当元や時間超過との因果、リークの有無は未確定である。

したがって、正式な停止予算はprocess privateとsystem commit余裕を別に持ち、区間境界だけでなく実行中の所有worker監視との関係を明記する必要がある。メモリを対象件数の4倍と単純外挿しない。既存の観測診断は強制制限ではなく、現在のwrapperも全体予算を境界で確認する。新しい強制停止条件やworker上限の引上げは未実装・未適用。正式失敗時の同一seed再試行をengineeringの再試行から推定しない。

## 確認・保全

既知の外部hashから20保存file/2,818,781bytesを認証し、33 source/契約pin、30 method参照を照合した。約0.538秒、peak private50.29MiB、最小空きRAM10.38GiB/commit余裕16.88GiB。OS実値はos-state.jsonに保存。長期メモリリーク検証ではない。

新評価、観測/score payload読取、数値再計算、bootstrap、試験実行は0。旧保存点、実計算clean c01d1c9、本流clean6f1285d、closed、既存dirty guardを保全。banto-24 PAUSED、formal/promotion/S6=false。source/runtime freeze、Phase2/3全体は未完了。
