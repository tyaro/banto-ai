# consumer実行証拠validatorの架空接続確認

2026-09-25。実装 `c79fc9e5db7d486a22c2ed4b5f5e75ca0027f7a0`、基準 `86fc575480da0549e2f6e9ecaf0c2b3cce87b181`。OUT `artifacts/consumer-execution-evidence-2026-09-25`、最終文書revisionとartifact pinは同directoryのsavepoint-evidence.json。[API](../anomaly-v03-consumer-evidence.md)。

## 変更と試験

analysis/audit/readerの供給証拠を外部期待値とsource/runtime/input/output bytesに結合する純粋validatorを追加。source descriptorは既存形式を維持し、全入力・全出力の実bytesをhashで結ぶ。正式gateや既存readerの動作・既存schemaは変更していない。

新規16試験pass、failure/error/skip0、0.081秒。全3役割×2mode成功、返り値の独立copy、wrong role/scope/revision、PID・生成token・command/cwd違い、未終了/非zero exit/監視欠落、実行前後runtime差、source/runtime/input/outputの過不足・同長差し替え、raw CRLF差、再封印後のinput/output期待値不一致を確認。

自己申告passやclosure欄、空inventory、source欠落、site読込・環境検索先、危険なpathとcase別名、boolをintegerとして渡すケース、strict JSONとparse前上限、formal modeの早期拒否も確認。open/Path.read_bytes/subprocess.runを拒否した状態で正常検証できる。Windows更新は別invocationの期待値へ記録可能、同一invocationの前後差は拒否する。

保存例invented-example.jsonは、架空source2file・runtime5file・input1file・output1file・架空PID/CPUを使う。全byte内容はtest fixtureに明示し、実runtimeや実行証明とは扱わない。過去の720評価・数値suite・14reader試験を繰り返していない。新しい子process/collector起動0、登録データ読取0、bootstrap0。

## 資源と保存

試験processの最大private 27.20MiB、試験前後の最小空きRAM 11.20GiB / commit余裕 19.57GiB、試験後C/D空き 124.34/365.97GiB。 変更前後で前工程の47code/18data pinを照合し、不変。新規source/tests2fileだけを追加し、旧保存点は変更していない。既存dirty guard、closed、実計算checkout/main、banto-24 PAUSEDを保持。

成功が証明するのは、信頼した呼出し側から渡された期待値とbytesの対応。期待値やprocess観測の真正性、全runtime閉包、独立計算監査は未完成なので、formal/promotion/S6/trust/execution_authenticatedはfalse。正式運用契約・予算採択・S4/S6・Phase2/3全体の完了とはしない。

## 次の接続

通常権限readerの実際の起動観測と外側で保持した期待値を、このvalidatorへ接続する。最初は既存の小さな架空公開結果で確認し、親の観測値を子の値として流用しない。 source revisionの採取・実processの生成identity・command・前後環境・保存outputが外側の記録で対応するようにする。現在のvalidator自体は実行も読込もしないため、自己申告値の単純な転記を採取と呼ばない。正式freeze/holdout/追加評価や、保留principal/UAC/ACL・同時書換え試験は起動しない。
