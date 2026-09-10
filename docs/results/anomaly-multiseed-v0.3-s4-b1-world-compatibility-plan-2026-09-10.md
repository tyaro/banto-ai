# S4-B1 Everyoneを追加する限定control候補

状態: **ユーザー「続けてください」により限定control1回を実施済み。token作成・実child token検証・親AccessCheckを通過し、resume後exit1で停止**。
[実行結果](anomaly-multiseed-v0.3-s4-b1-world-compatibility-result-2026-09-10.md)を参照。
以下の未実施・判断待ちの記述は準備時点の履歴。今回分の了承を再確認せず、同じwrapperは再実行しない。

## 判断する具体的な内容

RCにEveryoneを1種類追加した制限トークンで、専用の新規fixture1個を使うcontrol harnessを1回実行する。
実装・独立レビュー・保存後preflightを済ませたcandidateを対象とし、同じ組合せを自動再試行しない。
既存の[判断資料](anomaly-multiseed-v0.3-s4-b1-token-compatibility-decision-2026-09-10.md)では
Everyoneのような広いgrantを自動採用しない条件を残したため、今回のnative実行には追加判断が必要である。

## ここまでの結果

既存KsecDD ACLの非特権package SID2種類は、それぞれ固定候補でCreateRestrictedTokenのWinError87となった。
[結果](anomaly-multiseed-v0.3-s4-b1-token-compatibility-result-2026-09-10.md)を保存し、いずれもchild/fixture未作成・teardown pass。
API引数/配置/寿命の再点検で不具合は確認できていないが、Error87の唯一原因やpackage SID一般禁止は未確定。
SIDを替える実機試行をここで止め、今回のWorld候補はまだtokenを作成していない。

KsecDDのEveryone allow1201bfは参照要求100003を含む。
EveryoneはWinWorldSidに対応する既知SIDである。
[Microsoft WELL_KNOWN_SID_TYPE](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ne-winnt-well_known_sid_type)。
これだけでAPI受理や起動成功を保証しない。

## 権限が広がる範囲

追加されるのはrestricting SID側のEveryoneであり、normal group・user・特権・elevationは増やさない。
ただし、通常側の検査に通り、Everyoneへのallowもあるobjectについて、追加側の検査が通りうる。
KsecDD以外のEveryoneへ書き込みを許すfile/device/IPC等も対象になりうるため、デバイス専用の例外ではない。
RCを残すだけで新しい許可がRCとのAND条件に狭まるとは主張しない。
ホスト全体の隔離が従来同等だという保証はしない。本候補は既存のengineering controlの範囲である。

保護対象のprotected DACL、Everyone向けのwrite系deny、control領域のRC write allowは変更しない。
同一user/logon/session/integrity、非昇格、flags9、privilege削減、privileged group deny-only、
source/runtime pin、固定child、非継承handleを維持する。
OSや既存artifactのACL変更、DLL patch、デバイスhandle継承、通常Popen fallback、別accountは導入しない。

## 固定実装と合格条件

_RESTRICTING_SIDSはRC＋Everyoneだけ。任意SID入力はない。
作成入力属性0、profileの文字列昇順で固定2 SID・属性7を厳密照合する。
core・DebugTokens・実child照合で同じ固定recipeを用いる。
旧package候補、SID不足/余分/重複/属性違いを拒否し、native profile parserを通す回帰も選抜70件に含む。
選抜70/70（0.219秒）pass。これは今回のnative成功を意味しない。

実機はtoken作成→新規fixture→実child token確認→親AccessCheck→resumeの順。
childもsource/tokenを確認し、read positive、control write positive、frozenの全禁止操作、
parent DELETE_CHILD、rename/replaceを検証する。成功時のcleanup/teardown/child report照合まで必要である。
起動成功だけで保護を合格にしない。失敗のskip/pass化や要求操作の削減はしない。

30秒/親＋child512 MiB未満/temp空き1 GiB以上、資源停止後の追加hash/save/scan禁止を維持する。
失敗fixture保持と所有終了を行い、再試行しない。別projectの連続稼働試験や既存failure rootsへ操作しない。
native_accepted/s4_accepted/formal_permission/execution_authenticatedは成功時もfalse。
Windows Python3.12を含む既定受入・本流統合・formal/B2/publisherの許可は含まない。

未実行wrapper world-compatibility-control-once.pyは3891 bytes、
SHA 1c1a92734ce87ea8d3988cd2a3653fb2d096b93a074cf415e7d394607d207348。
前wrapperから新規出力先・定数名・成功時recipeラベルを変更。harness呼出1箇所、前候補の再実行なし。

この具体的な1回への「お願いします」「続けてください」は了承として扱い、同じ了承を再確認しない。

独立差分・計画レビュー新規P0〜P3=0。担当のnative/query/再試験/編集なし。
候補保存後にread-only preflightを行い、実行前のユーザー判断を待つ。


候補コードをc0909ac77263603dab2945bc4ac8f369889178e7へ保存した。
保存後read-only preflightはverified、2.843秒、27 sources/278078 bytes、resource_stopfalse、primary/secondaryなし。
Windows10.0.26200.9445/Python3.14.0、既存runtime hash一致。
world-compatibility-preflight.jsonへ保存。World token作成・child・SetThreadContextは未実施。
今回の広い候補はユーザー判断待ちで、承認前にnativeを進めない。
作業後08:46:53Zの空きRAM8.45 GiB、C108.46/D75.36 GiB、last bootは作業前と同じ。
別projectの連続試験や既存failure rootsを操作していない。単発の資源値からリーク有無を断定しない。
本流889cfc3 clean、repository safety/diff-check pass。記録だけの更新でsource preflightや試験を再実行しない。
