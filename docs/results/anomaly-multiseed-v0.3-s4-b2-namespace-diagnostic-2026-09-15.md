# S4-B2 親作成失敗のエラー記録

2026-09-15 JST、基準2b865dc、実装 **c0f17d8e4dd8b9835215869633bd55c6c2536402**。
[診断仕様](../anomaly-v03-namespace-diagnostic-design.md)の新規max1で、最初のshare3親CreateDirectory2Wが**WinError87**で失敗した。
87はERROR_INVALID_PARAMETER。[Microsoftの定義](https://learn.microsoft.com/en-us/windows/win32/debug/system-error-codes--0-499-)。
具体的にどの引数の組合せが不適合かは未確定で、share3全般の禁止やACL原因を断定しない。[前回](anomaly-multiseed-v0.3-s4-b2-namespace-create-2026-09-15.md)の失われた数値を復元した結果でもない。

既存例外に保持された値だけをsnapshotへ追加し、報告時のAPI照会は増やしていない。実引数・取得/終了動作は維持。
peer/child/第2rootは未開始、evidence保存なし。根元の未確認取得と11 ancestor/evidence leaseをworker終了まで保持し、query tokenはclosed。
worker PID25756/exit81/終了確認、UTC2026-09-14T15:51:00.0939872Z〜15:51:00.7761607Z、0.661秒、監視stop/errorなし。
stdout10432/stderr0 bytes。枠閉鎖、失敗sourceへの存在確認/列挙/再open/hash/copy/delete/再試行なし。

新規2＋既存397＝399件pass、修正後0.487秒、全failure/error/skip等0。
独立レビューP2総1件はLinuxにないctypes属性のfake補助へcreate=Trueを加えて是正、残件0。read-only/進捗ポーリングなし。
PowerShell構文/repository safety/diff pass。corrected-checks.jsonl289110 bytes/hash1636747d851d271e2bc5a2400ef588071d5a7b18f461b5f1b9a4d51a4dedadb3。

新規clean checkout namespace-diagnostic-20260915/banto-ai、input109/選抜71/union140 sourceを前後照合、候補CRLFのみ22件を保全。
input-pin.json17695 bytes/hashae96dd9cf8516cebc65982a221f61676c31680aca0b59dd278cf89753e8b7a2b。
前回namespace-createのmanifest/13 artifacts不変、70 source中66不変。変更4件はnamespace本体/test/probe/supervisor。
artifacts/namespace-diagnostic-2026-09-15に15 artifacts/論理812764 bytes、manifest46686 bytes/hashe5b4255afc638c015daf3246fa6227be7f126a9bb69dab3410d8a2940018aa6f。
内部8点/最後0.064秒、private21086208/working29564928/OS working peak37068800 bytes。外側1点/0.587秒、private20078592/working27639808 bytes。
UTC15:49:37 RAM15885127680/C125464051712/D47940218880 bytes、15:51:50 RAM15885922304/C125462380544/D47691575296 bytes。
上限内、worker/監視終了。他processへ操作なし、全体容量変動の原因未特定、長期リーク不在は主張しない。
build26200.9445/boot2026-09-09T10:43:08.5000000+09:00、Windows Update engineering緩和/正式pin不変。Python3.14.0、新account/service/runtimeなし。
既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621はcommit除外。本流889cfc3不変。

次は過去のdirectory-peerで作成できたshare1条件だけを新規に確認する。share3の作成不適合で本来のpath追加の評価が遮られないよう、単一case仕様へ限定する。
比較controlを除外したことを明記し、同一tokenのpeer要求とpath CREATE_NEWの成否だけを評価する。失敗したshare3を再試行しない。
namespace/全期間/独立token/全publisher/B2/S4受入は未解決。全許可flags=false。
