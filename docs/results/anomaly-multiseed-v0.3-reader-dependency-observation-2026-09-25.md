# readerの依存source・実行環境観測の拡張

2026-09-25 JST。実装 `0b03b91a59c7359e4eb05e3585242b88aa8c8cab`。[API](../anomaly-v03-reader-evidence.md)、[計画](../anomaly-v03-consumer-source-runtime-plan.md)。OUT `artifacts/reader-dependency-observation-2026-09-25`、成功は `attempt-2/`。保存revisionと各pinは最上位savepoint-evidence.json。

## 結果

`check_with_evidence(..., observe_dependencies=True)` を追加。子processでrequestを読み、collector自身のimportを準備した後、公開結果の検査前後に採取する。sys.modulesの177 module、実際にloadしたWindows image48本を記録。親は終了確定・stdout pin照合後、sourceを指定Git revisionと、各fileの内容/identityをディスクと比較する。

| 種類 | 一意file数 |
| --- | ---: |
| project source | 28 |
| stdlibのfile origin | 79 |
| 既存bytecode cache候補 | 77 |
| Python extension（.pyd） | 8 |
| その他loaded image（Python executable/DLLを含む） | 40 |
| 合計 | 232 |

1 snapshotで47,574,229bytes。前後の一覧・pin・identityが一致し、読取り中の追加module/fileは0。native48本はextension8＋その他40で、重複計数しない。ESETのeamsi.dll/ebehmoni.dllも実際の読込みを観測した。外部DLLは親にもloadされた**同一絶対path**だけを許し、任意directoryへの読取り許可は追加しない。

Git/raw一致の候補checkout `C:/Users/TKent/.codex/worktrees/rd01/banto-ai` を指定commitから作成。743 tracked files/8,430,967bytesをGit blob IDと比較した。候補はcleanで保全。元70b0のgenerator.py/manifest.pyのCRLF差は変更しない。candidateは正式freezeではない。

## 試験と資源

新規13試験pass、failure/error/skip0、10.825秒。小さい架空publicationで実childを起動し、Git/raw不一致・内容改変・hardlink・上限・許可外path・参照欠落・module消失・再封印された子hashを検査した。同工程初回の既存reader13＋pure evidence16もpass。その後の変更は新collector/testだけなので、その29種類を再利用（unique42、最後に全42を再実行したわけではない）。

最初のunit runは10件中2error。Windowsのlstat/fstatでctime値が一致しない場合があり、device/inode/link数/size/mtimeと内容hashへ照合を統一。次の候補41件は既存範囲外のESET DLLにより新規live2件がfail、残り39件pass。external nativeの親load照合を加えたattempt-2で新規13件pass。初回記録と失敗した候補の記録は保全。

保存例child PID20520、exit0/reaped、監視1.566秒、peak private38,060,032bytes（36.30MiB）。stdout240,485bytes。資料生成後の観測では空きRAM11.08GiB、commit余裕19.47GiB、C124.35GiB/D365.94GiB。最終保存時は別snapshotを保存する。試験harness全期間のpeakは採取しておらず、子process監視値と保存確認processの値を区別する。

子の30秒/512MiBは維持。opt-in時のみstdout+stderr枠を1MiBへ広げ、既定64KiBは維持。依存fileは最大512本、1file64MiB、snapshot合計256MiB、1MiB bufferでhash。親のGit処理も各10秒timeoutで、正式な総予算とは扱わない。元publicationは不変。架空入力原本は一時directory終了で片付け、期待値・観測・report・monitor・crosscheckを保存した。

## 到達範囲と残件

従来の外部期待値validatorはsource10/Python2fileの結合を継続。追加の232fileは**子が列挙した観測を親が終了後に照合する補助記録**で、独立した事前runtime期待一覧ではない。`dependencies.json` と `dependency-crosscheck.json` を保存する。builtin/frozen/no-file moduleを区別し、既存pyc候補の存在を実使用の証明とはしない。disk hashは実memory内code、途中でunloadされたDLL、未実行branch、Git helperの完全性を証明しない。

reader用の依存一覧を実行結果とは別に保持する期待profileへ落とし込み、import準備の境界と照合手順を定義する。今回の観測一覧をそのまま正式な期待値やfreezeとして採択しない。 解析/auditのrole profile、正式consumer/最終audit・全体資源予算も残る。

旧52code/18dataのうち意図的変更はreader adapter1本、新collector/test2本追加。旧境界・dirty guard・終了済RUN・banto-24 PAUSED不変。新評価/登録データ読取/実bootstrap0。formal/promotion/S6/trust/execution_authenticated/full closure=false。正式gate/holdout/正式freeze、principal/UAC/ACL、push/mergeは行っていない。Phase2/3全体は未完了。
