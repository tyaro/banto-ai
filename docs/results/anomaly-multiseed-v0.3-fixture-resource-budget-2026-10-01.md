# 限定fixture工程の資源停止・共有予算（2026-10-01）

親処理から所有子の計算/検算・終了後照合・保存までに、容量/system commit余裕を含む停止条件を接続した。新規16＋影響範囲の既存37、計53試験が成功。共有予算で小さいanalysis→auditを一度通し、全体・両役割ともverified/resource_budget_passed=trueとなった。[APIと限界](../anomaly-v03-fixture-resource-budget.md)、[現在の引継ぎ](../current-handoff.md)。

## 実装と保存点

開始a47b4ba1af372c8159413f0d8f2a8ce5cc5fbd3b、初回実装f4c1918d6586a49d3420ebe9562edf54e355ca0c、修正後実装cf4d9c42c11c202984aacdd71ac5efb0368f22d0。成功候補fb02/banto-ai。fb01とその失敗記録、fa01/fw01などの旧候補を保全した。

新budget module/testの2本と、既存supervisor・analysis/audit worker・各testの5本を変更。旧70codeのうち65本と18dataは不変で、変更した5本の旧pinも今回のmanifestへ残す。OUT artifacts/fixture-resource-budget-2026-10-01、成功tests-2/shared-example/。最終文書revision・全artifact/pin・資源はsavepoint-evidence.jsonとsave-checks.json。

前保存点26669bytes/SHA-256 a57343756c873d9c6e51ba2faa63d68bf8150f8bbde7200ebae69baacc20f531を外部起点とした。旧例の架空入力・既知文書pinを再利用し、変更した資源接続を確認するため小さい40cluster/4drawのanalysisとauditを各1回実行した。既存720評価・正式50,000反復は再実行していない。

## 予算と停止

親/共有工程120秒、親peak private512MiB、通常ファイル総量32MiB、256entries/深さ8、commit余裕2GiB、RAM空き2GiB、出力volume空き5GiB。約0.25秒＋観測時間で監視し、既存の子60秒/256MiB/stdout+stderr1MiBと起動条件を併用する。上限緩和・自動再試行・成果物削除は行わない。

analysisとauditへ同じ共有monitorを渡し、入力保存・各receipt・工程間の容量/時間を合算した。親のphase境界でも確認し、停止理由は最初の1件を保持する。子が稼働中なら元Popenだけをkill/waitし、停止後もpayload/logを保全する。未終了ownerは診断保存やmonitor終了の失敗でも保持する。

## 試験結果

| 項目 | 結果 |
| --- | --- |
| 最終試験 | 53 pass、failure/error/skip0、83.808秒 |
| 内訳 | 新budget16、supervisor13、analysis15、audit9 |
| 共有保存例 | 23.623秒、両子exit0/reaped/error0 |
| analysis / audit子peak private | 66.09 / 46.81MiB |
| 試験・保存harness peak private | 121.75MiB |
| 共有root観測最大 | 11.26MiB、54entries |
| 共有観測sample数 | 94 |
| 共有中の最小commit余裕 | 12.85GiB |
| 保存例後 RAM空き / commit余裕 | 8.25 / 12.93GiB |
| 保存例後 C / D空き | 107.20 / 387.12GiB |

65,537bytesの小さな書込みで容量上限65,536bytesを超過させ、実子の停止・終了確認とファイル保全を確認。別の実子ではcommit余裕だけを模擬的に低下させ、実メモリを大量確保せずに停止経路を確認した。起動前停止、子終了直後の超過による親照合の抑止、親処理中の監視、監視thread異常、停止理由の保持、共有root累積、リンク/entry/depth、最終診断予約も検査した。

初回tests-1は52試験中19 failure/2 error。WindowsのDirEntryキャッシュが通常fileのst_nlinkを0として返し、リンク判定が通常fileを拒否した。path.lstatで実リンク数を取得するよう修正し、監視thread異常を失敗とする試験も追加した。初回ログ・harness・commit/fb01を残し、修正後53試験と共有保存例はtests-2で完走した。

共有例のanalysis文書は既知の1,932,543bytes/SHA-256 2c20d80e63bf53e662ee722ba48f723285cf08182178036a2410a78d6033c6b1と一致。続く別実装auditも主9表/180gateが一致した。selected sourceはanalysis22/audit14、Python各2file。両役割の実行記録とresource-budget.json、共有rootのresource-budget/resultを別に保存した。元入力は不変。

## 限界と次工程

停止はsamplingと親側checkpointによるもので、hard quotaではない。観測間隔、実行中の限定関数/write、停止・終了確認の時間は超過しうる。最終budget/resultに合計64KiBを別に予約する。対象は新規rootの通常ファイルの見かけのbytesで、alternate streams/物理割当/別directoryの総量ではない。親privateと子privateも別上限。共有monitorは全工程が終わるまで呼出し側が保持する。

今回の小さい予算は正式2,880評価や50,000反復の登録予算ではない。slice/sidecar/producerを含む正式数値監査、契約・登録consumer・役割証拠/source/runtime・公開の受入は残る。次は直近のfixture計算・主集計audit・資源停止の証拠を受入残件表へ反映し、正式実行前に不足する対象を具体化する。同じ保存/reader試験やwrapperを増やして埋め合わせない。

正式null4欄、formal/promotion/S6/trust/execution_authenticated/full closure=false。OS25H2/26200/9457を記録し、旧formal pin9168は維持。新評価0、登録データ読込み0、既存評価再実行0。旧実計算c01d1c9、本流6f1285d、closed、dirty文書/CRLF差、旧候補/保存点を保全、banto-24 PAUSED。principal/保護root/UAC/ACL、正式gate/holdout/freeze、push/mergeは対象外。
