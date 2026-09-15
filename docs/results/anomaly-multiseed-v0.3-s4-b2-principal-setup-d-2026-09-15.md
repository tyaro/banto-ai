# S4-B2 新規準備dの保護root作成での停止

2026-09-15。実装 **f5ad7c21389e7ae26eb48858b6017691fecedb22**、[仕様](../anomaly-v03-principal-setup-d-design.md)。修正後のPreflight単独成功から進み、root定数/記録先だけを新規dへ変更した。C#34件pass、独立所見0、通常load-onlyはPID20872/exit0。公開DLL22528 bytes/SHA256 **fc88778d472098160f81302b8058b4b8cabcfa015119098b585fd03cce57007e**、command15335文字。
UTC05:20:34の通常事前照会でSAM2221/free0、account不存在と新規dのattributes0xffffffff/error2による不存在を確認した。末尾なし/b/cの3旧rootへ再訪なし。

新規RunはUTC **05:21:30.6208593Z〜05:23:38.6962403Z**、PID **22336**、**exit263458 = phase4 CreateRoot + native1314**。起動要求124066ms、待機3952ms、合計128068ms。Handle取得・終了観測・observer解放成功、観測例外なし、release_failed=false。起動要求待ちをnative40秒の経過として扱わない。
固定codeの順序ではPreflight、HoldAncestorsの祖先identity/policy/peer AccessCheck、CheckAbsentを通過した。CreateRoot phaseで停止したため、InspectInitialRootとaccount作成以降へは到達していない。phase4にはSD変換とCreateDirectory2W/handle確認が含まれ、個別API名の記録ではない。
UTC05:25:12のSAMだけの照会で2221/free0、account不存在を確認した。**root dは失敗後に存在確認/再open/列挙/hash/copy/deleteせず、状態unknownとして閉鎖**。account不存在からroot不存在を推定しない。今回の作成guardは閉鎖して再使用しない。閉鎖rootは末尾なし/b/c/dの4件となる。

99 sourceをGit/raw照合し、前回98中96不変/2変更/新仕様1、前回6 artifacts不変。input19396 bytes/hash45bc965885a1335787546854b06d077ece3f72172bc1f17ca43a4e885de8c725、input時5 artifacts不変。
artifacts/principal-setup-d-2026-09-15の最終manifest **20341 bytes/SHA256 d009f150c6cfbeb3796517ca6dda2390669884b7a870766bcae817a18059a989**、9 artifacts/論理62344 bytes（manifestは集計外）。記録process終了、本流889cfc3/clean不変。既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保全しcommit除外。
UTC05:20:34 RAM5931921408/C148573458432/D218689720320 bytes→05:25:12 RAM6053531648/C148569583616/D218658721792 bytes。D約203.64GiB。点観測から長期リーク不在やPC全体の変動原因は断定しない。build26200.9445/boot2026-09-09T10:43:08.5000000+09:00、Windows Update engineering緩和/正式pin不変。新runtime/service/task/VM/profileなし、push/merge/CIなし。

1314は[必要な特権を保持していないエラー](https://learn.microsoft.com/en-us/windows/win32/debug/system-error-codes--1300-1699-)。[新規objectのSACLの公式仕様](https://learn.microsoft.com/en-us/windows/win32/secauthz/sacl-for-a-new-object)では明示SACLにSeSecurityPrivilegeの有効化を要求する。今回SDはS:P(ML;;NW;;;ME)を明示している。この要件を確認すべき根拠はあるが、失敗processの特権一覧や有効状態は観測しておらず、原因を確定しない。
次は作成用B processの既存特権と、一時的な有効化/元状態への復元を事前確認へ組み込む設計・故障試験から進める。要求を満たさない場合は追加のOS権限付与へ進めず停止する。SACL/medium labelや初期保護条件を省かず、旧rootやdのretryも行わない。新しい作成先を使う前に、この事前確認を別の新規診断枠で確認する。専用環境の既存許可は継続。
環境準備、P activation/reset/logon/disable、protected code/process/thread/token/IPC、P/U、namespace共通期間、全publisher/frozen/marker/正式B2-S4は未完了。全許可flags=false、acceptance_status=not_completed。
