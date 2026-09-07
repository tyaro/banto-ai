# S4-B1 evidence 独立監査と是正記録

ユーザー承認により別エージェント1体がread-only監査を実施。
再委譲なし。進捗照会は行わず、通知を待って指摘に対応した。
本書は実装担当が受領した監査結果を整理したもの。

## 初回独立監査

対象: `f2f2d95013992bdb1a359f178dc0b74b6e710fd4`、比較基準: `16a037f`。
結果: **P0=0 / P1=0 / P2=2 / P3=0**。
監査担当はpure/fault 98/98 passを確認し、ディスク変更なしの追加注入で3反例を再現した。
native、restricted child、full suite、既存artifact操作、ファイル編集は実施していない。
最初の追加スクリプトはimport path不足で停止し、srcを指定して再実行した。

| 指摘 | 反例と影響 | 是正commit |
| --- | --- | --- |
| P2: trace読取handleの所有喪失 | close failure後もhandleが残るがfixtureの台帳に存在せず、fixture.closeは成功扱い。取得後の_Closing allocation失敗ではclose未試行 | `9797500` |
| P2: teardown reportの二次例外が返却を中断 | cleanup一次失敗＋close失敗＋report MemoryErrorにより、元の原因を失いprivate journalをresultへ返せない | `9797500` |

snapshotの確定・immutable bytes・ledger分離、状態遷移、traceのintent/chain/type/pin/tail、
child resource exitの回収抑止、public summaryの非露出はread-only/pure範囲で確認された。
ただし上記failure境界があるため、初回時点のcleanup/evidence合格は保留とされた。

## 是正内容と実装担当の検証

`9797500`でtrace専用所有slotと事前確保したclose collectorをfixtureへ追加した。
_Closingの取得後allocationを除去し、close成功までslotを保持する。
初回closeが失敗してもfixture teardownで再試行し、元の診断collectorは別に保持する。

private journalとteardown collectorを要約生成前にresultへ接続した。
teardown要約の失敗はsecondaryとして記録し、元のreason/winerror/child exitを維持する。
overall failed化とresidue 0の除去を要約生成より先に行い、要約中のresource stopも記録する。

| 検証 | 結果 |
| --- | --- |
| pure/fault | 100/100 pass、0.252秒 |
| 同一parent実Win32 | 2/2 pass、0.504秒 |
| D2 exact inventory | 1/1 pass、4.982秒 |
| repository safety / diff-check | pass |
| 既存成果物・失敗root | 5,763 entries / 592,342,788 bytes / 6 roots、不変 |

raw hash・属性・SDDLを含むinventory digest:
`0ae21dd53bd4f5a6994d720e019386e50ce4437c9cccf9b883d380b6f0964aa7`。
本流HEADは`889cfc3d5e1fd6dd7fc6c9656273d16d7d56d64e`のままclean。
main/candidateのformal 5 rootは全て不存在。

## 再監査

同じ独立担当が`bb8a038..9797500239f51341da85d96c68b6ee42ad4d804b`を再監査した。
結果: **前回P2の2件は修正確認済み、今回差分の新規P0〜P3は0件**。
独立担当のpure/faultは100/100 pass。元の3反例を再実行し、ValueErrorも追加注入した。
handle slot保持と再試行、取得後_Closing allocation経路の除去、report二次例外時の
primary/exit/private evidence保持、resource詳細抑止、residue 0除去を確認した。
native・restricted child・full suiteは独立担当も実行していない。

限定checkpointの保存と次の診断準備は可。この判定をB1全体の受入に拡張しない。

required restricted-child、Windows 3.12、full suiteは未実施。
既知のchild起動障害`0xC0000142`は未解消で、main統合・native acceptance・formal permissionはno。
