# S4-B1 AllApplicationPackages互換性候補

状態: **ユーザー了承済み見直し方針の次候補 / 実装・選抜70件pass / native未実施**。

[RC＋AllRestrictedApplicationPackages候補](anomaly-multiseed-v0.3-s4-b1-token-compatibility-result-2026-09-10.md)は、
CreateRestrictedTokenでWinError87となり、child/fixtureを作成する前に終了した。
API引数・配列・寿命の再点検と独立点検に新規所見はなく、一般禁止の一次資料も確認できていない。
同じ候補を再実行せず、実測KsecDD ACLにあるもう一方の非特権SIDを評価する。

## 固定候補と差分

RCを残し、追加1種類をAllApplicationPackagesへ置き換える。
既存の分類結果ではallow1201bfが参照要求100003を含む。
WinSDKのAPP_PACKAGE_AUTHORITY15/BASE_RID2/ANY_PACKAGE1、およびWinBuiltinAnyPackageSid84に対応する。
[Microsoft WinSDK](https://github.com/microsoft/win32metadata/blob/main/generation/WinSDK/RecompiledIdlHeaders/um/winnt.h#L10080)、
[Microsoft WELL_KNOWN_SID_TYPE](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ne-winnt-well_known_sid_type)。

前の計画でAllApplicationPackagesを追加しないとしたのはARAPを先に選ぶ候補範囲であった。
ユーザーの見直し方針（既存ACLに対応する非特権SIDの最小候補）の中で、この選定を更新する。
Everyone/user/admin/systemへの追加へは拡大しない。
ARAPを含む両方を追加する構成にもせず、RC＋今回1種類だけを作成・検証する。

fixed tuple、入力属性0、profileで正規化した属性7の2 SID完全一致、flags9、normal groups、
非昇格・同一user/logon/session/integrity、privilege削減、protected DACLと全実操作の条件は不変。
source・DebugTokens・childの照合は同じcore tupleを用いる。
追加SIDへのallowがある他objectにも効く。KsecDD専用・従来同等・AppContainer化は主張しない。
ARAPとAAPの全objectへの権限集合の包含、APIが本候補を受理することは未実証。

## 検証と終了条件

df09964からの変更はcore定数名・SID値・対応するfake検証だけ。
選抜70/70（0.237秒）pass。前候補で追加した実profile buffer/canonical順序/重複拒否の回帰も含む。
前候補276件の結果を本候補の全体再実行結果とは扱わない。

独立レビュー後に保存し、保存後preflightと、新規fixture1個のcontrol harnessを1回実行する。
token作成が失敗すればfixture/childへ進まない。作成成功後も実child tokenと親AccessCheckをresume前に照合する。
起動・read positive・control write positive・frozen negative全操作・parent DELETE_CHILD・rename/replace・
cleanup/teardownまで通ることが条件。保護条件の軽減やfailedのpass/skip化なし。
30秒/親＋child512 MiB未満/temp空き1 GiB以上、資源停止後の追加hash/save/scan禁止、
失敗fixture保持を維持する。今回候補もtoken作成で拒否された場合はSID試行を打ち切る。

未実行wrapper app-package-control-once.pyは3895 bytes、
SHA b91507bef035154b83c4eda1279b1dd40f430d58588aa5bf4c85643e44394fa6。
前wrapperから新規出力先・定数名・成功時recipeラベルだけを更新。run_control_harnessは1箇所、自動再試行なし。
新しいdevice metadata queryなし。OS/既存artifactのACL変更、DLL patch、別account、通常Popen fallbackなし。
本流統合・Windows Python3.12受入・formal/B2/publisherは許可しない。

独立差分レビュー新規P0〜P3=0。担当の再試験/native/query/編集なし。
repository safety/diff-check pass。保存後preflightへ進む。
