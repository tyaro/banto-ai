# S4-B1 RCと制限アプリ識別子の互換性候補

状態: **ユーザーの見直し方針了承済み / 候補実装・pure/fake276件pass / 限定native未実施**。

2026-09-10の「お願いします」は[判断資料](anomaly-multiseed-v0.3-s4-b1-token-compatibility-decision-2026-09-10.md)への了承。
保護対象のwrite禁止を維持し、権限構成を見直して検証を進める。引継書§6の従来RCのみを前提とした禁止は、
本候補の具体的範囲についてこのユーザー判断で更新する。他の禁止、受入条件、本流/formalのgateは維持する。

## 選定の根拠

固定KsecDD metadataを親contextで1回取得し、前回未分類だった2 ACEを固定SID bytesと比較した。
追加した処理は2種類の既知SIDラベルと新規出力先だけであり、open/query/close・権限・上限は前回と同じ。
2026-09-10T08:23:34Z、open/query/close各1回confirmed、188 bytes、0.001秒、resource_stop=false。
SD hash80855ee5cacdab07dcb48643d08ae3898dd45bef77695ab67057a08395cd8521は前回と一致。
未分類1はAllApplicationPackages、未分類2はAllRestrictedApplicationPackages、双方allow1201bf。
raw SID/SDは新規保存・公開せず、匿名化summary ksecdd-security-classified.jsonへ保存した。

MicrosoftのWinNT.hにあるAPP_PACKAGE_AUTHORITY15、BASE_RID2、
ANY_RESTRICTED_PACKAGE2を照合し、後者1種類を追加候補に選定した。
[Microsoft WinSDK header](https://github.com/microsoft/win32metadata/blob/main/generation/WinSDK/RecompiledIdlHeaders/um/winnt.h#L10080)。
AllApplicationPackages、Everyone、user、Administrators、LocalSystemを追加しない。
この選定は全Windows objectに対する数学的な最小権限の証明ではない。

## 固定recipeと影響

coreの_RESTRICTING_SIDSをRCとAllRestrictedApplicationPackagesの2個に固定する。利用者入力なし。
CreateRestrictedTokenはflags9、normal groupのprivileged SIDをdeny-onlyへ、SID_AND_ATTRIBUTESの入力属性0。
返却と実child profileは既存profile()の文字列昇順に正規化した2 SID・属性7の完全一致を要求する。
作成入力のRC→制限アプリ順と、profile出力の制限アプリ→RC順を区別する。
DISABLE_MAX_PRIVILEGE、WRITE_RESTRICTED、同じuser/logon/session/integrity、非昇格、
SeChangeNotifyPrivilege以外を残さない条件を維持する。
診断用DebugTokensも同じ固定tupleでpreowned SID bufferを確保し、追加SIDの中断出力を未確認のままcloseしない。

restricting SID側はRCと追加SIDの両方が個別に全権限を許可するAND条件ではない。
追加SIDを許可する他のobjectにも効きうるので、KsecDD専用・従来と同一の隔離とは主張しない。
AppContainer/LPACの生成ではなく、既存のrestricted tokenへの固定SID追加である。
KsecDDの今回のallow maskには参照要求100003が含まれるが、実AccessCheckやdriver固有判定を未実測の段階で成功とは扱わない。

protected DACLは変更しない。frozen領域のEveryone向けwrite系deny、control領域のRC write allowを維持。
OS device/DLL/ACL、既存artifact、通常user権限、プロセスglobal設定へ変更なし。
DLL patch、親のdevice handle継承、impersonationによる回避、通常Popen fallback、required skipは導入しない。

## 検証範囲と実行

初回選抜69/69・全体275/275はpassだったが、独立実装レビューでprofileのソート順不一致P2を検出。
検証側とwrapperをprofile同様にsortedとし、owned fake TOKEN_GROUPS bufferを実profile()へ通す回帰を追加した。
是正後は選抜pure/fake70/70（0.216秒）、全体276/276（7.118秒）pass。
固定2 SID以外（不足・余分・重複・順序・属性・別package・Everyone・SYSTEM）、core作成のflags/配列、
追加SID確保失敗時の未作成と解放、診断用追加SIDの中断出力保持を確認した。
独立設計レビュー新規P0〜P3=0。実装P2の是正確認後に候補をcommitし、保存後read-only preflightを実施する。

次は既存run_control_harnessを新規fixture1個で1回実行する。起動時のbreakpoint collectorは使用しない。
保存済み固定child・DETACHED+suspended・非継承handle、source/runtime照合を維持する。
child resume前に実child tokenを照合し、そのtokenのduplicateでcontrol/frozenの実AccessCheckを検証する。
child側もtoken/sourceを照合し、read positive、control write positive、frozen negative全操作を実施する。
parent DELETE_CHILD、rename/replace、cleanup snapshot/ledger、owned teardownと最終reportの整合まで確認する。

wrapper token-compatibility-control-once.pyは既存detached-control wrapperを複製し、新規公開出力先と固定2 SIDの成功時照合だけを追加。
30秒待機/親＋child512 MiB未満/temp空き1 GiB以上、失敗fixture保持とresource停止後の追加hash/save/scan禁止は維持。
run_control_harness呼出はAST上1箇所。自動再試行なし。最終状態を先にstdout flushし、資源停止がない場合だけ詳細を保存する。
成功した場合もnative_accepted/s4_accepted/formal_permission/execution_authenticatedはfalse、
Windows Python3.12必須受入・本流統合・B2/publisherは未完了のまま。

未実行wrapperは3907 bytes/hash01fbc5015ea5fc91beaa3544cd478ab18532199f3c6ca56bb2b8b55011b97ad6。
分類summaryは1606 bytes/hash26be0758bdd1113c9933dc11a1fee87fb5cddc1a1576051b2b394d3488c9e915、既知pathから有界readで完了状態を確認済み。

独立実装P2の是正確認済み、新規P0〜P3=0。担当は新回帰1件だけpass（0.002秒）。
native/query/wrapper/編集なし、完了通知のみで進捗ポーリングなし。repository safety/diff-check pass。
