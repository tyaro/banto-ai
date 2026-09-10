# S4-B1 bcryptのデバイスopen・制御要求・後始末の3地点を観測

状態: **候補実装・pure/fake272件・独立実装レビュー完了 / 保存後preflight前 / 実機未実施**。

[今回の実測](anomaly-multiseed-v0.3-s4-b1-bcrypt-detail-result-2026-09-10.md)は後始末前にEAX/EBP=C0000022、EDI0を示した。
次はDebugDriver(bcrypt_device=True, detached_console=True, bootstrap=True)で、
検証済みbootstrap pendingから初期threadの固定3地点を1回設定する。

| DR | bcrypt RVA | 観測する候補値 | 固定caller |
| --- | --- | --- | --- |
| 0 | 8129 | helper8154から保存した負値R12D、EAXへ移す前 | RSP+b8 → 5d53 |
| 1 | 80ac | NtDeviceIoControlFile後の負値EAX | RSP+b8 → 5d53 |
| 2 | 5dd5 | 後始末前のEAX/EDI/EBPを別生値で保持 | RSP+128 → 5ab5 |

数値はhex。DR3はaddress0・無効、DR7 local enable15。従来の4地点collectorはenable55のまま。
全4 DR addressを照合し、DR3に別addressが入る、未使用B3 causeが立つ、余分なenableが立つ等は不一致で停止する。
共通armは固定targetsを4枠へzero paddingし、有効BREAK_RVASの範囲だけをhit選択に使う。

## 設計レビューの是正

初案の4地点には応答値取得8131が含まれたが、独立設計レビューでP2を検出した。
8131へ至る経路は先に80acを通り、最初の例外で停止する条件では取得できないため、
8131を今回の候補から外して3地点に絞った。追加の例外継続を導入していない。
80acで80000005（buffer overflowに対応する値）が返る場合もAPI戻り値を記録して停止する。
その後の応答値を取得したとは扱わず、必要なら別の明示的診断範囲として準備する。自動再試行なし。

## 照合と取得

既存DebugBcryptFailureのbootstrap/pending/初期thread/所有handle/load寿命/RIP/TF/DR照合を再利用する。
最初の例外で選択を消費し、hit全176 bytesもAPI前後で再検査する。
既定off、bool必須、DETACHED+bootstrap必須、他collectorと排他、任意address入力なし。

live参照窓は次の3回1758 bytes。保存field名code_windows_confirmedは互換維持し、3つ目が文字列であることを明記する。

- 59e0/1068 bytes/hashcb7064e15ca553b37c1b77b48de2602ed157de8497d430b5c7bf7affd40804b3
- 7f50/660 bytes/hash1a67c25ccbd32bcfb4c60ebb399b9453c6fc55882bc88651ad916de8182382bc
- 1f098/30 bytes/hashe7df70a79aa2fdf8e999c635fb354bc1d25ad32e2b4b52426c98a88eea54d3fb（固定名\\Device\\KsecDD、終端込み）

site0/1はRSPのuser範囲・16-byte整列に加えて、RSI=RSP+60、RDI/R14=0、R15=8を照合する。
caller offsetb8は7push＋sub rsp80の固定prologueに基づく。
site0はR12D負値を採用し、直前LeaveCriticalSection後のEAXをhelperの戻り値へ読み替えない。
site1はR12D=0とEAX負値を検査する。warning値もbit31で分岐するため、そのまま記録して停止。
site2はRSI=base+25b10/R15=0とcaller offset128→5ab5を照合し、EAX/EDI/EBPを混合値として保持する。

固定caller slot8 bytesを1回だけ読み、報告read長/rawを解釈前に保持する。pointer walkなし、応答bufferの追加readなし。
helper8154やIAT名・固定文字列はAPI候補を説明する参照根拠であり、過去のCALL完了や実行時IAT実体の認証ではない。
親の診断コードから対象deviceへ追加open/IOCTLを発行せず、childの既存起動経路を観測する。
token/DACL/ACL/デバイス設定を変えない。

collector最大Get3/Set1/RPM4回1766 bytes、bootstrap込みGet4/Set1/RPM7回1841 bytes。
30秒/256 normal events/親＋child512 MiB未満/temp volume空き1 GiB以上、drain32回/5秒、
context8 KiB/bootstrap4 KiB/metadata72 KiBは不変。同期APIを厳密な時刻で中断する保証ではない。
hitを通常Continueせずbcrypt_device_observed_stopとして所有終了処理へ進む。
不一致/資源停止/hitなしの終了処理、再選択・再arm禁止、非受入を維持する。

## 保存・検証・次の判断

新sourceを含む27 inputsを保存後にindex照合する。core/固定child/environmentは不変。
未実行wrapper artifacts/context-offline-2026-09-10/bcrypt-device-once.pyは2760 bytes、
SHA-256 6ef9ba31f8ddebdf112453375f365f5cdee0f8b9f4db845bdc928b3469aee0a0。
構文/AST run1箇所を確認済み。新規公開要約を起動前にopen、最終reportをstdoutへ先行flushし、
資源停止時の後続詳細/hash/保存中止と既存private evidence保存方式を維持する。

関係fake60/60（4.429秒）、全体pure/fake272/272（5.802秒）、repository safety/diff-check pass。
3site・warning停止・R12とEAXの区別・未使用DR3・各frame/status・caller失敗/OOM/pending/load・固定名不一致・
除外した応答地点の再選択禁止・排他/hitなしを確認した。既存4site collectorも回帰済み。
独立実装レビュー・保存後preflightを追記する。

準備完了後、新規fixture1個で固定3地点から最初の1hitを取得して終了する診断1回を判断対象とする。
引継書§6の追加probe条件を維持し、この問いへの「お願いします」「続けてください」は当該1回への了承として扱う。
同じ了承を再確認せず実行し、自動再試行なし。今回のbcrypt-detail1回への了承は消化済み。
全acceptance gate no、本流統合/formal/B2/publisher未実施。

独立P2は是正確認済み、実装レビューの新規P0〜P3=0、指定fake60/60（4.596秒）pass。
担当のnative/wrapper/private参照/編集なし、完了通知のみ、進捗ポーリングなし。
作業後RAM7.82 GiB、C107.98/D75.36 GiB、本流889cfc3 clean。
