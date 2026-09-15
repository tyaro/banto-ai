# S4-B2 Preflight確認後の新規principal準備d

2026-09-15。[修正後の管理者Preflight成功](results/anomaly-multiseed-v0.3-s4-b2-principal-identification-confirmation-2026-09-15.md)を受け、既存許可の範囲で専用環境準備へ進む。直近のユーザーは管理者確認画面を「今なら操作できます」と回答済み。方式の再承認は不要。
新規rootは **C:\ProgramData\BantoAI-S4B2-principal-20260915d**、記録は **artifacts/principal-setup-d-2026-09-15**。末尾なし/b/cの3閉鎖rootへ存在確認/再open/列挙/hash/copy/deleteしない。旧作成/診断guardは再使用しない。dもCREATE_NEWのmax1で、失敗・応答不明では枠を閉鎖してretryしない。

C#は成功したPreflightの正確長8/4・SecurityIdentification要求level1を維持し、root定数だけをdへ変更。launcherの変更は記録場所/rootの固定値だけ。直接Process.Start/UseShellExecute/runas/Hidden/System32、共有observer45秒、有界inline/hash/同bytes load、native40秒/private256MiB/working384MiB/空きRAMとC各2GiBを維持する。UAC待ちとloaderはnativeの時間上限外。
account名BantoS4Publisherを維持する。通常側の事前確認は対象SAMと新root dの不存在だけ。helperも祖先保持後に再確認する。既存account/rootを再利用・変更しない。accountは初期からdisabled標準account、Users所属、rootはBA所有/保護DACL/medium label・U/P readonly、B内unmanaged random secretを保存せず破棄する。Pをenable/logonしない。
祖先保持・dangerous access拒否、単回作成、初期/最終policy確認、preclose receipt、子→root→祖先→tokenの順の解放を既存[準備仕様](anomaly-v03-principal-setup-design.md)どおり実行する。Preflight成功は祖先の実機AccessCheckを代替しない。

通常compile/C#34件・通常load-only・差分独立レビュー・commit・source/DLL/hash/resource保存後に新規Run一度。成功はexit0/終了観測/観測・解放例外なしの全条件。成功時だけdの既知bootstrap-result.jsonとSAMを読取確認する。失敗時はdへ再訪せず、対象SAMだけを読取確認してcode順序による推論と実観測を区別する。通常側から昇格process killやaccount/root補償削除はしない。
新runtime/service/task/VM/profileなし、既存Python3.14.0/.NETを使用する。Windows Update engineering緩和/正式pin不変。P activation/reset/logon/disable、protected code/process/thread/token/IPC、P/U干渉、namespace共通期間/全publisher/frozen/marker/B2-S4は未完了。成功しても全許可flags=false、acceptance_status=not_completed。
