# engineering結果の別process readerと外側の確認記録

2026-09-25更新：子の起動に`-S`を適用し、siteの自動初期化とsystem site-packages追加を除外。通常権限の14試験が通過し、旧起動条件を検出する対照試験も確認した。[結果](results/anomaly-multiseed-v0.3-consumer-reader-no-site-2026-09-25.md)。source/runtimeの完全受入は引き続き未完了。

`anomaly_v03_consumer_reader` は、[engineering consumer](anomaly-v03-engineering-consumer.md)のwriterを閉じた後に、保存済みレポートを別processで確認する。[確認結果](results/anomaly-multiseed-v0.3-consumer-separate-reader-2026-09-25.md)。既存のprocess監視とLocalPublication readerを使用し、通常権限で動く。

## API/CLI

```python
from banto_ai.anomaly_v03_consumer_reader import check_in_subprocess

result = check_in_subprocess(
    publication_root, binding_savepoint, report_savepoint, analysis_input,
    expected_mode="engineering-dev-smoke",
    expected_marker_sha256=retained_marker_sha256,
    expected_binding_pin=retained_binding_pin,
    expected_report_pin=retained_report_pin,
    receipt_parent=existing_check_parent,
    receipt_name="new-check",
)
```

呼出し側がwriter終了と単一writer/readerの順序を保証する。外部に保持したmarker SHA256と、結合・記述保存点の `{bytes, sha256}` を必ず渡す。検査対象から期待marker hashを自動採用しない。正式/未知modeや不正anchorはファイル操作前に拒否する。

PowerShellで `PYTHONPATH=src` を設定し、下記のplaceholderを実際のpath/pinに置き換える。

```powershell
$env:PYTHONPATH='src'
C:/Python314/python.exe -B -m banto_ai.anomaly_v03_consumer_reader --mode engineering-dev-smoke --publication-root PUBLICATION --marker-sha256 RETAINED_MARKER_SHA256 --binding-savepoint BINDING_SAVEPOINT --binding-bytes BINDING_BYTES --binding-sha256 BINDING_SHA256 --report-savepoint REPORT_SAVEPOINT --report-bytes REPORT_BYTES --report-sha256 REPORT_SHA256 --analysis-input ANALYSIS_INPUT --receipt-parent EXISTING_PARENT --receipt-name NEW_CHECK
```

成功はexit0、読取不一致・未確認はexit2。結果JSONの `status=verified`、`separate_process_verified=true`、`reader_exit_confirmed=true` を確認し、返されたresult_pinを外部保存する。

## 検査と所有process

親は新しい確認directoryを排他的に作り、入力・期待pinをrequest.jsonへ保存する。Pythonを `-I -S -B` で起動し、明示した現在checkoutのsrcだけを検索pathへ追加する。環境変数のPYTHONPATHやuser siteを子へ引き継いでimport先を選ばない。`-S`によりsite初期化・system site-packagesの自動追加も止める。子はproducer/別process/writerを起動しない。

既存supervisorで所有する子を、30秒・private512MiB・stdout/stderr合計64KiB以内に監視する。Windowsでは非表示起動し、終了code・PID・メモリ・監視側runtimeの前後値を記録する。6つの入口/保存/監視sourceとrequestのraw hashも前後で確認する。これは全依存閉包や子processの完全runtime受入ではない。

子はrequestの外部pinを確認し、前工程のprepare_engineering_resultで7保存fileを認証する。元入力に対応する4payloadをメモリ上で準備し、公開directoryの固定inventoryと各サイズ上限を先に検査する。その後、marker hardlinkの同一性・外部marker hash・全payload hash・元入力に対応する全bytesを確認する。値を変えて新しい完了印を付けても、元の保存点との対応が違えば拒否する。

親は子の終了とstdout pin、request pin・対象root・marker・PID・scopeを結合してからverifiedにする。子から終了code0だけが返っても、報告が欠ける・壊れる・対象が違う場合はfailedとする。集計/比率/scoreの再計算は行わず、旧数値検証を再利用する。

## 外側の保存と応答消失

確認directoryは公開物と各入力directoryから分離し、毎回新しい名前を使う。

| ファイル | 内容 |
| --- | --- |
| request.json | 明示path、期待marker/保存点pin。期待情報を自己申告出力から補わない |
| worker/report.json、worker/stderr.json | 子の出力。既存監視が容量を制限する |
| supervision.json | 所有processのPID/終了code、終了確認、上限・runtime・メモリ |
| result.json | 外側のverified/failed、期待pinと報告pin、確認範囲 |

書込み後の応答を失っても、独立に保持した期待markerと入力anchorがあれば、新しい確認directoryから結果を読み直せる。期待情報がない場合は未確認のままにし、writerの再実行や対象からのhash採用で成功扱いしない。

元publicationへの書込みはない。不一致・timeout・子報告消失は外側のresult.jsonへfailedを残し、元markerを撤回しない。確認directoryの非上書きも維持する。確認記録自体が途中までしか残らなければ、それを完了証拠にせず新しい名前で確認する。

`UnreapedWorker` ではログを追加読取りせず、外側はworker_exit_unconfirmedと記録し、元process ownerを例外に保持する。API呼出し側はそのownerをreapする必要がある。CLIは既存retain_until_exitで所有processの終了まで保持する。後から終了が確定しても、古い未確認記録を成功へ書き換えない。

## 到達範囲

T11の外側状態とT12の別process読取をengineeringの保存済み記述結果へ接続した。再封印不整合の拒否は、認証された元レポートへのbytes対応検査である。別processというだけで独立した数値監査を実行したことにはならず、`independent_numerical_audit_performed=false` を保持する。

正式analysis/auditの別root、40 cluster・実CI/gate/選択、source/runtime freeze、正式運用契約、S4/S6は未完了。principal分離や敵対的同時書換え保証を追加せず、UAC/ACL変更は不要。formal/promotion/S6/trust等はfalse、performance/decision未実施。
