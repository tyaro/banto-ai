# S4-B2 特権修正後の準備e・管理者起動取消

2026-09-15。実装 **e23564c43e7a3c50101c07e38b9c4da052be4c38**、[仕様](../anomaly-v03-principal-setup-e-design.md)。特権の存在/有効確認/元の有効ビットへの復元は管理者診断で成功済み。新規準備はroot/記録先をeに固定し、Buildに特権15件の実行と既存出力guardを加えた。34＋15件pass/独立所見0。
公開DLL25088 bytes/SHA256 **734e654339aa46e4f66cd86e98be1a3ba5585a0ebda4b4bea45d0ce04e09e88b**、通常load-only PID33788/exit0/command16723文字。UTC08:31:35にSAM2221/free0と新規e attributes0xffffffff/error2で不存在確認。旧4 rootへの再訪なし。

RunはUTC **08:32:27.5162967Z〜08:34:30.9979697Z**。request-launchで123472ms、合計123474ms後にWin32 error1223。外側MethodInvocationException/HRESULT -2146233087、内側Win32Exception/HRESULT -2147467259/native1223、切詰めなし。PID/Handle/exit未取得、helperの開始・終了や作成phaseへの到達は未確認。Windowsの取消扱いを記録し、手動操作と時間経過による取消を区別しない。
通常側observer sessionは終了。UTC08:35:30のSAM照会だけで2221/free0、account不存在を確認した。**root eは失敗後に再確認せずunknownとして閉鎖**し、account不存在からroot不存在を推定しない。閉鎖rootは末尾なし/b/c/d/eの5件。今回guardを再使用せず、未知helperへの操作も行っていない。

102 sourceをGit/raw照合、前回101中99不変/2変更/新規1、前回16 artifacts不変。input20101 bytes/hash6d03fa689ea51fa3db02bdcdab79d6ecc077179e510fec16017f9cd935e9efb4、input時6 artifacts不変。
artifacts/principal-setup-e-2026-09-15最終manifest **21481 bytes/SHA256 24a21c73c965c3b489b85b042fa2d650d371ad4329048f072bfa7b9633765c60**、10 artifacts/論理78182 bytes（最終manifest集計外）。
UTC08:31:35 RAM12638420992/C144728379392/D210318372864 bytes→08:35:30 RAM10906451968/C144691527680/D208566575104 bytes。build26200.9445/boot2026-09-15T14:30:24.5000000+09:00、Windows Update engineering緩和/正式pin不変。PC全体の容量減少の原因は未確認で、今回の小規模artifact生成が原因とはしない。長期リーク不在も断定しない。
本流889cfc3/clean不変、既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621保全。追加OS権限付与、新runtime/service/task/VM/profile、push/merge/CIなし。
ユーザーへ現在の管理者画面操作の都合を質問し、回答待ち。既存方式の再承認ではない。[新規準備f](../anomaly-v03-principal-setup-f-design.md)の通常側準備まで進め、回答を受けるまで新規Runは開始しない。環境準備/P-U/正式B2-S4未完了、全許可flags=false、acceptance_status=not_completed。
