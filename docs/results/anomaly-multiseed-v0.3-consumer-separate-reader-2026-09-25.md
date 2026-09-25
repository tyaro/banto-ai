# engineering結果の別process reader接続（2026-09-25）

[API/CLI](../anomaly-v03-consumer-reader.md)を追加し、writer終了後に別processで保存結果を確認、その成功/失敗を外側へ記録する経路を接続した。実装 `35842261a90b1efe475056dc9ef962c56773f1f1`、OUT `artifacts/consumer-separate-reader-2026-09-25`。最終文書revisionとartifact pinはsavepoint-evidence.json。

## 確認結果

13新規試験pass、failure/error/skip0、3.291秒。既存の保存・算術試験は再実行せず、小さい架空の入力を再利用した。

- 実際に別processを起動し、PID・終了・source対応を確認。確認directoryの上書きを拒否。
- 元保存点pin違い、再封印した同サイズの値の変更、未完了marker、元publicationに重なる確認先を拒否。
- writerのcommit後応答消失でも、独立に保持した期待markerで確認可能。元結果は不変。
- 子の応答消失・timeout・終了未確認は外側のfailed/未確認へ。終了未確認時は元ownerを保持。
- 容量不一致をpayload読取り前で拒否し、request改変・formal modeも拒否。

実保存点はengineering-consumer-entry-2026-09-25（11477bytes/SHA256830d2de2202166c7f3f735603c21b317cb18bb33809530d1f3bf8d8c87403219）を外部起点とした。成功publicationのmarkerは97c8bc637328cb173e6c1a678765c7785512fb2ad7b66ed8af15939e819c874e。既存writerを再実行せず、この公開物を1回の新規reader invocationで確認した。

| 項目 | 実確認 |
| --- | --- |
| 親 / 子PID | 35884 / 27688、別process |
| 子終了 | exit0、worker_exit_confirmed=true、監視error0 |
| 保存点からの認証 | 7file / 7,896,608bytes |
| 元入力と対応する公開payload | 4file / 2,755,533bytes、全bytes一致 |
| 元publication保全 | 4payloadと2marker名、計6fileのpin不変 |
| 所要時間 | 監視を含むreader0.826秒、外側確認全体1.055秒 |
| process peak private | 親33.34MiB、reader35.91MiB（各process別の値） |
| システム余裕 | 最小RAM12.30GiB / commit20.24GiB、終了時C130.25/D329.72GiB |
| 監視側runtime前後 | Windows26200.9457 / CPython3.14.0、一致 |

記録はOUT/verified/request.json、worker/report.json、supervision.json、result.json。実行入口・保存・監視の6source raw pinとrequestは前後不変。全runtime/dependency closureの受入とはしていない。

## 維持する条件と次の作業

新評価、観測/score payload読取、集計/比率/score再計算、bootstrapは0。元の失敗履歴・判定不能値を含むレポート内容を保持。旧数値検証は再利用し、独立数値audit実行はfalse。formal/promotion/S6/trustはfalse、performance未実施。

T11/T12のengineering部分が接続できた。正式full document・独立数値audit・source/runtime受入は残る。次は正式consumerの40-cluster入力と推論・全documentへのadapterを、非登録の架空入力で準備する。実holdoutで実装調整しない。正式gateを閉じたまま、既存の算術・schema部品を使う。

旧保存点・source、実計算clean c01d1c9、本流clean6f1285d、closed、既存dirty guardを保全。banto-24 PAUSED。専用principal・UAC/ACL・同時書換え試験は再開していない。短い確認であり、長期リーク不在やPhase2/3全体の完了は主張しない。
