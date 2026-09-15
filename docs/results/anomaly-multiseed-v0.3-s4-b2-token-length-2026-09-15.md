# S4-B2 権限情報照会の長さ不具合と修正

2026-09-15。[準備c](anomaly-multiseed-v0.3-s4-b2-principal-setup-c-2026-09-15.md)は管理者起動後のPreflightでerror24となった。[読取診断](../anomaly-v03-token-length-diagnostic-design.md)を **79a8ef302016ace8514cce03767aa10419204396** で保存し、通常権限の自process tokenだけを4条件で照会した。

| 情報class | 渡した長さ | BOOL | error | 必要長 |
| --- | ---: | --- | ---: | ---: |
| TokenLinkedToken (19) | 64 | false | 24 | 8 |
| TokenLinkedToken (19) | 8 | true | — | 8 |
| TokenElevation (20) | 64 | false | 24 | 4 |
| TokenElevation (20) | 4 | true | — | 4 |

UTC03:51:53.7950481Zに完了。class19で成功取得したlinked handleとown tokenはclose成功。class20の値は0（非昇格）。一次/解放例外なし、UAC・impersonation・準備Entry・SAM/root操作なし。旧root3件へ再訪なし。今回の診断guardは閉鎖した。
64-byte指定では両APIにerror24が再現し、構造に対応する8/4-byte指定では成功した。当該Windowsでのバッファ長の不具合を確認した。準備cのphase1記録には個別API名がなく、この比較は通常tokenなので、管理者preflight全体の成功や以前の起動失敗原因まで確定したとはしない。

診断の独立レビューで、未確認のnonzero tokenをcloseするP2一件を修正。各query結果を解釈前に記録する改善も行い、残0で実行した。90既存source不変、新規2を含む92 sourceをGit/raw照合（照合は観測後）。artifacts/token-length-diagnostic-2026-09-15に2 artifacts/論理2195 bytes、最終manifest18201 bytes/SHA256 **7cd7fa72532618593a34421881b786353847c0e8a282dae1312a9e98946900e0**（manifest自身は集計外）。

修正はtests/fixtures/PrincipalSetup.csの2行だけ。TokenLinkedTokenの要求長を(uint)IntPtr.Size、TokenElevationを4にした。64-byte確保と成功後の返却長確認、所有・解放・権限・その他phaseは維持する。独立レビューの追加所見0。
検証buildを新規artifacts/principal-token-fix-2026-09-15へ分離した。初回compileは相対source指定がCS1504となりDLL出力前に停止。絶対source pathと別名build-02でcompile/34件passを確認した。既存build/guardを上書きしない。DLL SHA256 **90f6014c4b70e7b063681086a896141416abccc63bc1c8b2183f711426448e8e**。
通常tokenでの実比較と既存34件passは、修正後の管理者Preflight実行の代替ではない。修正buildで準備Entryは未実行。root定数は閉鎖済みcのままで、現在の準備Runを再使用しない。

次は修正buildのPreflightだけを管理者側で実行し、取得tokenと自己watchdogを終了まで管理する新規の読取専用診断を仕様化・確認する。root/account作成phaseを呼ばず、旧guardや閉鎖対象に触れない。これを確認してから次の新規環境準備を具体化する。既存環境準備の許可は継続し、再承認やUAC表示状況の再質問は不要。
環境準備/P-U/IPC/namespace全期間/全publisher/frozen/marker/正式B2-S4は未完了。全許可flags=false、acceptance_status=not_completed。
