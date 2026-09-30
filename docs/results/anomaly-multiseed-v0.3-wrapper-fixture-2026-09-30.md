# 架空入力の5出力・実行記録を結合（2026-09-30）

**5種類の予定結果ファイルを、草稿・全予定枠・外部に保持した架空の実行記録へ対応付けた。新規16試験pass。** [API](../anomaly-v03-wrapper-fixture.md)、[前回残件](anomaly-multiseed-v0.3-acceptance-gap-update-2026-09-26.md)。

作業開始revisionは536c66721878c04fb8c781ffcb86c4e868407033。追加はanomaly_v03_wrapper_fixture.pyと対応testの2fileのみ。既存62code/18dataは変更していない。JSON objectの並び順に依存する既存slice処理に対し、新adapter境界で固定template順へ整える。値・配列順・canonical input pinは変えない。OUT artifacts/wrapper-fixture-2026-09-30、最終検証はtests-2/、実装・文書の保存revisionとpinは最上位savepoint-evidence.json。

## 実装と確認

入力はfixture専用。既存の文書・slice・consumer evidence validatorを利用し、40個の架空cluster×12layout×2層×3候補の宣言を保持する。役割・mode・operation・revision・入出力pinを検査する。期待値は呼出し側から受け、供給記録から自動作成しない。対象processを起動したかのような証明は付けない。

新規16試験、failure/error/skip0、58.729秒。正常な5出力、I/O/推論再計算禁止、正式mode早期拒否、宣言への成功フラグ混入、保持pin不一致、保存結果準備のoperation流用、役割/mode/未終了記録、source/output差替え、coverage順序/欠落/型/profileの不一致、途中失敗と未開始、文書の未供給、inconclusive保持、再封印による改変、入力の非破壊、canonical JSON保存・読戻し後の全5payload/pin一致を検査した。既存保存/別reader試験や実720評価は再実行していない。

保存例の5payloadは計1,973,806bytes。analysis草稿は本文1233行、diagnosticsは4系列2835行/詳細9表。全2880枠は架空の宣言。fixtureの準備には既存builderの4draw手例を使ったが、新adapter自身はCIを再計算しない。登録40seedや50,000反復の結果ではない。

不完全coverageに完成文書を付ければ拒否する。文書なしの場合は元coverageと失敗を保全し、analysis/diagnosticsの値をNoneにする。全枠処理済みでも証拠なしでanalysis完了へ進めない。inconclusiveは科学的判定不能として保持し、software failureへ置換しない。

完全なfixture例でもstatus/provenance/analysis_consumer/bootstrapの4欄はNone、文書がない場合は10欄全てを未充足とする。外側selected_candidate=None、formal_ready=false。writer/reader/auditはnot_run、producerはfixture_declarations_only。5payloadのpinは外側descriptorに保持し、公開markerや自己参照hashは作らない。

## 保存例と資源

tests-2/example/にexecution.json・coverage.json・analysis.json・diagnostics.json・verification.json、外側descriptor、架空request、架空analysis記録、別保持期待値、架空source/runtime bytes（hex）を保存した。これらはtest harnessが書いた検証例で、アプリケーションの公開APIを実行した成果物ではない。PID/path/runtimeの値は架空であり、実測と混同しない。

試験/例保存harnessのpeak private 104.19MiB。保存例後の空きRAM 13.74GiB、commit余裕 14.42GiB、C/D空き 115.31/365.67GiB。最終値はsave-checks.json。OS実観測は25H2/build 26200/UBR 9457。engineering更新方針に従って記録し、旧formal pinを変更しない。単時点/単工程の記録からリークの有無は判定しない。

最初のbaseline準備はautomation.tomlの既定cp932読取りで失敗し、出力directory作成前にUTF-8指定へ修正した。保存点start.jsonに経緯を記録。初回tests-1は15試験passだが終了時メタデータが未保存だった。元harnessは停止済みで、終了コード/最終出力を保持できていないため未保存の直接原因は不明。保存例の回収確認で、canonical JSONの辞書順変更が既存slice検査に影響する問題を検出した。新adapterで固定template順に整え、保存・読戻し試験を追加したtests-2の16試験で再検証。初回コード・ログ・例は保全し、この工程の不足を正式成功と扱わない。

## 保全と次の作業

前保存点18702bytes/SHA3d5338c6e51d901b513b748dc95438455e8e9c5e13190e7f4876b76edaf1c28f、実計算c01d1c9・本流6f1285d・closed・既存dirty文書/CRLF差を保全。新しい候補checkoutは作らず、旧pc01等を変更しない。banto-24 PAUSED。formal/promotion/S6/trust/execution_authenticated/full closure=false。

T09/T10の架空結合まで進んだ。実producer、数値analysis/auditのprocess証拠、正式source/runtime受入と全体予算は残る。次は、小さい架空入力を数値計算する所有workerと、起動前に呼出し側が保持する期待値を接続する。保存済み結果準備のoperationとは区別し、実holdout/正式50,000反復は起動しない。その後、独立数値auditの入口と全工程の資源停止条件を揃える。正式契約採択・gate/holdout/freeze・principal/保護root/UAC/ACL・push/mergeは対象外。
