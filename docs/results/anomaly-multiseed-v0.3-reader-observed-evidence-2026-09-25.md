# reader実観測を外部期待値へ接続した確認

2026-09-25、最終実装 `0ee336e72ca52849e6725415a3d7f8e4ff75aeeb`。OUT `artifacts/reader-observed-evidence-2026-09-25`、成功記録はattempt-3/、文書revision/artifact pinは最上位savepoint-evidence.json。[API](../anomaly-v03-reader-evidence.md)。

新module/testを追加し、既存supervisorにはon_startedの任意hookを追加。親の元handleと子のself handleの生成時刻/PID、前後の実runtime/source、外部anchorで選んだ入力15fileと出力1fileを結合した。旧reader API・元publication・正式schemaは維持。

## 試験と保存例

最終新規13試験pass、failure/error/skip0、15.385秒。変更したsupervisor13試験＋通常reader14試験は同じ工程の初回に通過し、その後この経路のsource変更がないことをGit差分で照合して再利用。合計40種類の関連試験で、最後に40件一括再実行したという意味ではない。

実子の正常確認、再封印した子report/runtimeの拒否、元handleと異なる生成token、終了後に差し替えたlaunch記録、revision/working bytes不一致の起動前拒否、formal早期拒否、確認directory非再利用を確認。callback失敗・未終了owner保持・記録保存失敗時のowner保持は模擬試験。launch改変は終了後の逐次fixtureで、同時書換え・principal分離試験ではない。

初回39試験はGit実体のhardlink2をsingle-linkとして扱ったため7failure/1error、27既存回帰と4新規試験はpass。原因を確認しGitの実リンク数/hashを個別に保持する形に修正。attempt-2は新規12pass。その後、親の生成記録をメモリ保持値から照合する修正と試験を加え、attempt-3で13pass。失敗/中間記録は削除・上書きせず残した。

保存例の子PID 38824、exit0、終了確定、監視0.809秒。入力15file/19773bytes、reader report 1317bytes、stdout 9956bytes。元handleと子selfの生成FILETIME/tokenが一致。source10本は指定revisionのGit/raw一致、Python executable/loaded DLLの2fileを前後照合。

子の実観測はCPython3.14.0/Windows25H2/26200.9457/AMD64、no_site=1、site未import/hook0。CPU名と明示したsrc＋Python検索pathも保存。親の期待profileと子の実測を別recordとして保持した。Git実体は46480bytes、hardlink2、絶対pathとfull SHA256はsource-tool.jsonに保存。

保存例は実process＋架空publication。fixtureの一時入力は試験後に片付け、外側のexpected/evidence/report/monitor記録を保持した。fixture定義はtestsにある。実登録データ/720評価/bootstrapの再計算は0。

## 資源と残件

今回processの最大private 50.43MiB、保存例の子は36.34MiB。観測時の最小空きRAM 10.21GiB / commit余裕 17.88GiB、保存例後C/D空き 124.38/365.97GiB。 旧境界・dirty文書・closed・実計算/mainとbanto-24 PAUSEDを保全。前工程49code/18dataのうち意図した変更はsupervisor1本、新規adapter/test2本。過去保存点のpinは更新していない。

完全source/runtime閉包や正式consumer/独立audit/予算採択は未完了。verifiedは通常権限の記録とbytesの接続成功を表し、全実行真正性・S4/S6・Phase2/3の完了ではない。次：readerの依存sourceとstdlib/extension/loaded DLLの記録範囲を広げる。既知のCRLF差を現在の作業コピーで修正せず、必要なら指定revisionの一時的な候補checkoutでraw一致を確認する。正式freezeとしては扱わない。 正式holdout/gate/追加評価、保留principal/UAC/ACL、push/mergeは起動しない。
