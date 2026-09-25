# consumerのsource/runtime固定対象と実行前の残件

2026-09-25接続追記：[実観測reader](anomaly-v03-reader-evidence.md)がsource10本・Python2file・実process identity・15入力を外部期待値へ結合。新規13＋既存回帰27種類がpass。source/runtime全閉包は未完了。次は依存source/stdlib/extension/loaded DLLの採取範囲を広げる。[結果](results/anomaly-multiseed-v0.3-reader-observed-evidence-2026-09-25.md)。

2026-09-25実装追記：[役割別実行証拠validator](anomaly-v03-consumer-evidence.md)を追加。16架空試験pass、外部期待値・前後source/runtime・process・全入出力bytesの対応を検査する。実processの採取・正式受入・closureは未完了。次は通常権限readerの実観測との接続。[結果](results/anomaly-multiseed-v0.3-consumer-execution-evidence-2026-09-25.md)。以下の41source候補表はe9826bd時点の記録。

2026-09-25、状態 **proposal / 未freeze**。対象revision `e9826bd0245cf26cf540e1ff470528c001f3cd5f`。[実確認](results/anomaly-multiseed-v0.3-consumer-source-runtime-review-2026-09-25.md)、[運用契約案](anomaly-v03-consumer-io-proposal.md)。現在の実装と保存証拠を整理したもので、正式実行を許可する文書ではない。

## 固定対象の候補

| 役割 | 静的なproject依存候補 | 現在の入口 |
| --- | ---: | --- |
| engineering writer | 23モジュール | 保存済みdev/smokeの記述結果を公開 |
| engineering reader | 25モジュール | writer終了後の別process確認 |
| 架空の推論・文書・slice | 17モジュール | 純粋関数、実IOなし |
| 独立検算の計算部品 | 15モジュール | 生成/score/ledger/seed/sliceの既存部品 |
| 既存inspection inventory候補 | 19モジュール | 実行processの正式受入には未接続 |

重複を除き41本、working source合計566,551bytes。33個の外部top-level importは当該Pythonのstdlib名で、候補位置も解決できた。第三者packageを必要とする静的importは見つからなかった。設定・schema・registry metadata・計画・build/workflow等18fileと、補助CLI2fileも記録した。登録holdoutの観測を読んだものではない。

これは条件付き・未使用importを含む候補一覧。15箇所のnative呼出し・subprocess生成を記録し、readerの文字列bootstrapも手動参照に含めた。完全な呼出し関係、動的依存、DLL/CRT、stdlib内部の全依存を確定したものではない。

### source bytes

41本中39本はworking bytesとGit blobが一致。`generator.py`と`manifest.py`の2本はCRLF/LF差だけで、改行正規化後には一致する。raw一致とは扱わない。元作業コピーは変更しない。

最終実装が決まった段階で、full commitを指定した別clean checkoutを固定元にする。`.gitattributes`は`* text=auto eol=lf`だが、既存working fileの一致を保証するものではない。既存capture_checkout等の全tracked clean・source/configのraw/Git一致・untracked source拒否を利用し、不一致をその場で正規化して受理しない。現在の既存dirty文書も保全する。

producerの過去実行revision `c01d1c978f78bab51391392d56cdcb7aab5afaab`と新consumerのrevisionは別に持つ。今回の41本を過去producerの実行sourceとして登録し直さない。

### 起動と検索経路

変更前のreaderは`-I -B`。実際のinterpreter-only probeではisolated=1、user site無効、**no_site=0**で、`C:/Python314/Lib/site-packages`が検索対象に残った。今回観測したsitecustomize/usercustomize moduleは0。

提案の`-I -S -B`ではno_site=1、site未import、同site-packages pathが消えた。明示したcheckoutのsrcだけをproject検索先へ追加する方針と組み合わせる。候補レビュー時点では起動probeのみだった。その後readerへ`-S`を適用し、14接続試験と旧条件を検出する対照試験で確認した（[結果](results/anomaly-multiseed-v0.3-consumer-reader-no-site-2026-09-25.md)）。この変更はengineering readerに限り、正式runtime受入ではない。

ここで使うruntimeはCPython3.14.0（v3.14.0:ebf955d、MSC v.1944、64bit）。Python3.12をWindowsの追加必須条件にはしない。repositoryの>=3.12宣言やLinux CIの3.12/3.14 matrixは別の互換性範囲として保持する。

## runtimeの受入方法

1. producer・analysis・audit・readerごとに、full revision、command、PID/終了、CWD、検索経路、起動flag、input anchorとoutputを対応づける。親のruntime値を子の観測値として代用しない。
2. Python exe/DLL・build、stdlib/zip、実際にloadしたextension・Windows DLL/CRT、CPU、実OS build/UBRを開始/終了時に記録する。動的loadとエラー経路を含め、対象fileとidentity・bytesの対応を確認する。
3. 外部programも対象に含める。source確認は現コードで`git`をPATHから解決しているため、実行Gitの絶対path/version/bytesを固定する案とし、helper/DLLの範囲も確認する。今回のGit観測は2.51.2.windows.1で、完全なGit runtime閉包ではない。
4. 既存inspection collectorはproducer/workflowを必須にする設計で、`full_runtime_inventory_complete=false`のinspection scopeを持つ。analysis/audit/readerの正式受入へそのまま転用せず、役割ごとの必要sourceとprocessへの結合を追加する。
5. source snapshotsは信頼した呼出し側が指定revisionから取得する。自己申告のpass、scope/role違い、source不足、process終了未確認、前後runtime差を受入にしない。既存`validate_result_contract`は供給bytesの一致を検査する部品であり、これだけで実行証明にはならない。

ユーザーのWindows更新許容方針を維持し、attemptごとに実値を記録する。実attempt内の変化は停止対象。今回観測はProfessional25H2/build26200/UBR9457。過去の記録と旧正式pin9168は保持し、新しい正式運用契約に更新方針を明記する。OS設定を変更しない。

## 次に行う作業と判断点

| 順序 | 作業 | 完了の根拠 |
| --- | --- | --- |
| 完了（engineering） | readerへ-Sを追加 | 14接続試験pass、起動flag/検索経路と旧条件の検出を確認 |
| 続く実装 | 正式consumerとsource/runtime証拠validatorを接続 | 間違ったrole/source/process・自己申告pass等を拒否、既存入口の制限を維持 |
| 候補確定後 | 別clean checkoutでsource固定、役割別runtime採取 | 全raw bytes、実process前後、正式contractとの対応 |
| 必要な回帰 | 最終revisionで関連純粋・通常権限Windows試験、必要なplatform確認 | 現候補に結び付く試験証拠。保留principal試験を混ぜない |
| 実行前の判断 | 運用契約と完全な資源予算を採択 | 下記2件の未充足を解消してから判断 |

**将来の採択事項は2まとまり。今は採択待ちで作業を止める段階ではない。**

- 正式運用契約：通常権限の単一writer、OS実値記録、本文slice＋補助記録、解析と監査の別出力、正式失敗時のversion/root/未使用seedでの再登録。完全consumer・証拠結合・最終audit接続を仕上げてから対象revisionとともに提示する。科学的な閾値は維持する。
- 正式実行予算：旧案のproducer240時間・出力96GiB・空き32GiB（開始時1copy128GiB、同volume2copy224GiB）は未適用。正式推論と最終独立auditの時間・メモリ枠が未確定のため、現時点で全体予算を確定しない。既存上限を変更しない。

候補レビュー時の54試験は当時のsource pin一致を確認した過去の合格記録。その後readerとその試験の2fileを変更し、reader14試験を新たに実行した。他suiteは再実行していない。旧CI revisionからselected source28本が変わっているため、旧CIを最新全体の回帰合格には用いない。現在のworkflowはLinux3.12/3.14の試験で、今回実行/再検証はしていない。

正式gate/holdout、実データ50,000回bootstrap、principal/UAC/ACL、同時書換え試験、push/mergeは起動していない。banto-24はPAUSED。正式source/runtime受入・S4/S6・Phase2/3全体は未完了。
