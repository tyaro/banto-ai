# S4-B2 管理者起動取消後の新規準備f

2026-09-15。[準備e](results/anomaly-multiseed-v0.3-s4-b2-principal-setup-e-2026-09-15.md)のrequest-launch/error1223後、旧対象を再使用せず次の新規枠を準備する。既存方式への再承認ではなく、管理者画面を操作できるタイミングの回答待ちである。
新rootを **C:\ProgramData\BantoAI-S4B2-principal-20260915f**、記録先を **artifacts/principal-setup-f-2026-09-15** に固定する。C#はroot定数、launcherは出力先とattempt.rootだけをe→fへ変更する。旧末尾なし/b/c/d/eの5 rootはunknown/閉鎖を維持し、存在確認/再open/列挙/hash/copy/deleteしない。旧guard再利用なし。
[準備e仕様](anomaly-v03-principal-setup-e-design.md)の権限scope/初期保護・disabled標準account/Users/readonly policy・順序・失敗停止・資源上限・成功後のみの既知receipt照会を全て維持する。49件試験と通常load-only、独立差分レビュー、source/hash保存までを先に行う。
**管理者画面を操作できる回答が来るまでは、新規Runを開始しない。** 回答後、直前の資源、対象SAMと新規f不存在、保存source/DLLの不変を確認して入力記録を保存し、新しいCREATE_NEW guardでRun一度だけ行う。追加の特権付与、P enable/logon、旧作成の再実行なし。
全許可flags=false、acceptance_status=not_completed。Windows Update engineering緩和/正式pin不変を維持し、現在のbuild/boot/資源を記録する。
