# v0.3 正式開始前の5役割 source/runtime 証拠境界（2026-10-04）

基準保存点は `87a8034d5cb65d32a8c494313bdf9698a508574b`。これは既存の役割別観測を、正式開始前に必要な事前profileと対照した棚卸しである。新しい実process試験、正式40 seedの観測、S4受入、完全な依存閉包を示す記録ではない。[受入残件表](anomaly-multiseed-v0.3-preformal-acceptance-scope-2026-10-03.md)の事項3を具体化する。

| 役割 | 現在保持する証拠 | 正式開始前に不足する境界 |
| --- | --- | --- |
| producer | 保存済みdev/smoke 720評価は過去の `c01d1c978f78bab51391392d56cdcb7aab5afaab` に属する。40 seed・2,880枠の登録metadata fixtureは実producerを起動していない | 最終producer revisionの別profile、生成・保存・再開を含む全source/runtime、各子の起動・終了と入力/出力の外部期待値。旧720評価のrevisionやOSを新campaignへ付け替えない |
| analysis | [記述結果準備の事前候補](anomaly-multiseed-v0.3-analysis-dependency-profile-2026-09-26.md)は別成功実行から作った234依存fileの候補。架空40 clusterの数値workerは選択sourceと終了後依存を観測済み | 正式50,000 drawを行う**最終数値analysis**の役割・operation固有profile。記述結果準備の候補や架空4draw workerの依存集合を流用しない |
| audit | [架空主表・sliceの所有監査](anomaly-multiseed-v0.3-fixture-slice-audit-2026-10-01.md)は選択source15本、終了後236依存fileを照合した | 登録観測からの完全な独立S6再導出と50,000 drawを対象にした別実装・別rootの事前profile、実行証拠、資源上限。既存の終了後一覧は受入済みprofileではない |
| writer | [架空5payload公開](anomaly-multiseed-v0.3-fixture-publication-2026-10-02.md)は選択source13本と終了後234依存fileを観測。現receiptには依存一覧・子応答・監視記録のpinを保持する | 採択した正式公開方式と最終payloadに固有の事前profile。26H2での新pin付き実process回帰は[起動前停止](anomaly-multiseed-v0.3-registered-summary-runtime-change-2026-10-04.md)のため未検証 |
| reader | engineering記述結果readerには[232依存fileの事前候補](anomaly-multiseed-v0.3-reader-dependency-profile-2026-09-25.md)がある。架空5payloadの別readerは終了後234依存fileを観測 | 正式公開物をwriter終了・回収後に読む最終role/operation/profile。記述reader候補と架空5payload readerを同一profileとして扱わない。26H2での新pin付き実process回帰も未検証 |

役割ごとに、最終clean Git revisionのraw source、起動command/flag・CWD・検索経路、入力と期待出力、子自身が開始・終了時に観測したOS/Python/runtime、stdlib・extension・DLL/CRT・外部programと動的依存、PID/生成identity・exit/wait/reapを、実行前に保持した別の期待profileへ結ぶ必要がある。子の終了後に集めた一覧を、その同じ子の事前期待値として自己承認しない。親のruntime値を子の観測値の代わりにしない。attempt内のsource/runtimeまたはOS build/UBR変化は成功receiptを付けず停止する。

現在の26H2/build26300/UBR9457は、採択済みengineeringの25H2条件と旧正式25H2/build26200/UBR9168の双方から外れる。版付き計画・契約と独立再監査を先に整え、対象clean revisionで必要なWindows native・Linux 2 jobs・正式dev/smokeの受入対象を定める。今回の棚卸しで `full_runtime_inventory_complete`、`execution_authenticated`、`formal_permission`、`formal_ready` をtrueにしない。
