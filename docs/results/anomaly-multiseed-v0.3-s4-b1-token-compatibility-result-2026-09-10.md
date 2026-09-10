# S4-B1 アプリ識別子2候補の互換性検証結果

状態: **14e2f53/c795b05の2候補ともtoken作成段階で失敗 / child・fixture未作成 / 未受入**。

ユーザーが了承した[見直し方針](anomaly-multiseed-v0.3-s4-b1-token-compatibility-decision-2026-09-10.md)に基づき、
[RC＋AllRestrictedApplicationPackages候補](anomaly-multiseed-v0.3-s4-b1-token-compatibility-plan-2026-09-10.md)を
独立レビュー・保存後preflight完了後に1回実行した。再実行なし。

| 項目 | 結果 |
| --- | --- |
| 実装・実行HEAD | 14e2f534a1319b56030c27d1a5303ff51624f857、clean |
| 独立実装レビュー | SID正規化順のP2是正確認済み、新規P0〜P3=0 |
| pure/fake | 選抜70/70（0.216秒）、全体276/276（7.118秒） |
| 保存後preflight | verified、2.257秒、27 sources/278074 bytes |
| 実行内preflight | verified、同source count/bytes/runtime |
| native結果 | failed / restricted_token_create / WinError87 |
| core所要時間 | 0.234487秒 |
| fixture / child | token作成後の処理に未到達、未作成 |
| control / cleanup | failed / not_started |
| teardown / resource | pass / resource_stop=false |
| private control / replace | null / null |
| acceptance/formal | すべてfalse |

Windows10.0.26200.9445/Python3.14.0、既存exe/dll hash一致。
公開summaryはtoken-compatibility-control-native-summary.jsonl。
実行wrapperは3907 bytes/hash01fbc5015ea5fc91beaa3544cd478ab18532199f3c6ca56bb2b8b55011b97ad6を直前照合した。
新規fixtureやchildのtoken・アクセス検証結果はない。KsecDDのopenが改善したとは主張しない。
資源peakはchild待機前の失敗で未収集。known_bytes0/retained_basename null。
既存failure rootsやartifactの再走査・修復なし。

再点検ではCreateRestrictedTokenの9引数、x64 SID_AND_ATTRIBUTES配置、count2、入力属性0、
SID確保の寿命、flags9、削除privilege数0は整合していた。
独立点検もこの失敗を説明する新規P0〜P3不具合なし。
公式資料は今回の組合せへの対応保証やARAP一般禁止を明記していない。
**今回の組合せがこの環境で拒否された**という事実を保持し、ARAPが常に使用禁止・唯一の原因とは断定しない。
[Microsoft CreateRestrictedToken](https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-createrestrictedtoken)。

このcandidateの失敗をpassやskipへ読み替えない。実装14e2f53を保存履歴として保持する。
次は既存KsecDD ACLにあるもう一方の非特権識別子AllApplicationPackagesの固定候補を、
同じユーザー了承範囲で独立に準備する。Everyone/user/admin/systemへは候補を拡大しない。

## AllApplicationPackagesの2候補目

ユーザー了承済みの非特権候補見直しの範囲で、実測ACLのもう一方の識別子を固定候補にした。
[候補計画](anomaly-multiseed-v0.3-s4-b1-app-package-plan-2026-09-10.md)は独立差分レビュー新規P0〜P3=0、
選抜70/70（0.237秒）、safety/diff-check pass。
clean c795b05d3d1a874349464b5dccc8c9f781045f33で保存後preflight verified（2.651秒、27 sources/278084 bytes）。
新規control呼出1回は再びrestricted_token_create/WinError87、core0.221246秒。
child/fixture未作成、controlfailed/cleanupnot_started/teardownpass/resource_stopfalse、
private control/replace null、known_bytes0、child資源peak未収集。すべてのgateはfalse。
実行内preflightもverified、Windows10.0.26200.9445/Python3.14.0、既存runtime hash一致。
wrapper3895 bytes/hashb91507bef035154b83c4eda1279b1dd40f430d58588aa5bf4c85643e44394fa6を直前照合した。

両候補の公開summaryを既知pathから1回ずつ有界readして状態を照合した。
token-compatibility-control-native-summary.jsonlは1444 bytes/hashadc2b952ff73a399b52f2ad0263606eaa9818b66f552f1257a78dcd4138b5ee0、
app-package-control-native-summary.jsonlは1444 bytes/hash9e6d0545dddc5e4f101bb1ac986b8349a3204598b3cb281615983986848fea16。
照合結果はpackage-candidates-result-check.jsonへ保存。fixture再open、追加native、ACL変更なし。

2種類の候補がこの環境で拒否された事実を保持し、ここでSIDの実機試行を止めた。
[Everyone候補の判断資料](anomaly-multiseed-v0.3-s4-b1-world-compatibility-plan-2026-09-10.md)は
既存了承で自動採用しないとしていた範囲であるため、candidate準備だけを進め、nativeを追加実行しない。
