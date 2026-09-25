# consumer checkpoint adapterの確認（2026-09-25）

完了記録から、最終attempt・失敗履歴・6種input hashを落とさずconsumerのslot検査へ渡す処理を実装した。[API](../anomaly-v03-consumer-checkpoints.md)。実装revision `1a88d33d3dc4953e239a536f2bd5ea183904f02f`。OUT `artifacts/consumer-checkpoint-adapter-2026-09-25`、最終文書revisionと全証跡pinはsavepoint-evidence.json。

## 検証結果

新規15試験と既存入力validator22試験、計37試験が通過。failure/error/skipは0、35.876秒。架空metadataを用い、最終attempt選択、履歴の欠落・並替え、外部anchor不一致、途中journal、manifestとのidentity/source/runtime/outcome不一致、入力hashすり替え、inconclusive、公開後失敗、未知内訳の保持、I/O/生成/再計算禁止、非破壊性を確認した。元validatorの仕様・実装は変更していない。

続いて、旧完走保存点の外部pinに束縛された管理記録484ファイル／10,013,204bytesを1回照合した。別途保存点と目録2,197,895bytesも既知hashへ照合。plan1件、journal362件、manifest121件で、観測・evaluation本文・scoreは読まない。

実記録の120区間・720評価、121attemptを正しく対応づけた。最後の区間119はattempt2を採用し、attempt1のresource_limit失敗を保持。attempt1にはstage上でcompleteと記された6評価のmanifestが残るが、markerはnullで公開未完了だった。これを公開成功へ補正せず、journalの失敗とstage宣言を両方残した。保存metadataへの適用は5.890秒。再評価・bootstrap・正式gate・holdout起動は0。

出力 `adapted-metadata.json`、入力pinとstage/payload選択 `metadata-read-pins.json`、確認結果 `saved-metadata-check.json` を保存。manifest一覧canonical hashはf4a2237b655bae04eeea175a1cb077ff4dabde881ee6dab28464342aec2ed275、出力canonical hashはee2f635872b39306da15895403ffd39d2628a0d50e4704ea405fb5c87b53ec4e。

## 資源と保全

確認中peak73.05MiB、最小空きRAM12.57GiB、commit余裕20.16GiB、C124.22GiB／D298.67GiB。既存の実計算checkout c01d1c9、本流clean6f1285d、完走closedと保存点、開始前のdirty guardは不変。OSの過去記録・正式pinは維持、OS設定変更なし。banto-24はPAUSED、追加controllerなし。

## 残る範囲

変換結果は別checkpoint envelopeであり、全体producerのmarker/終了を要求するconsumer入力v1の完了宣言ではない。profile labelもslot宣言からの対応づけに限る。管理記録のraw hashを旧anchorに照合したが、公開印・payload本体・実controller終了・source/runtime受入を今回認証したとはしない。trust、campaign_completed、execution/analysis/formal/promotion/S6はfalse。

次は固定hash readerとの結合で、区間の公開印・manifest・終了記録の参照関係を認証する。fixtureと保存済み管理記録を対象とし、数値再計算や追加評価を行わない。正式採択・freeze・Phase 2/3全体は未完了。
