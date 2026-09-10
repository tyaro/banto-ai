# S4-B1 bcryptの同期オブジェクト初期化と後始末直前の候補値を観測

状態: **了承済み限定実機1回を実施済み / 後始末前の混合値を取得 / 所有終了・証跡保存確認済み**。

実測は[詳細経路の結果](anomaly-multiseed-v0.3-s4-b1-bcrypt-detail-result-2026-09-10.md)を参照。以下は実行前に保存した計画。

[今回の結果](anomaly-multiseed-v0.3-s4-b1-bcrypt-failure-result-2026-09-10.md)はcall_59e0からC0000022が返る地点を示した。
次はDebugDriver(bcrypt_detail=True, detached_console=True, bootstrap=True)を使い、
同じ検証済みbootstrap pendingで初期threadに固定4地点をDR0〜3へ1回設定する。

| DR | bcrypt RVA | 候補 | 固定caller |
| --- | --- | --- | --- |
| 0 | 5af1 | RtlInitializeCriticalSection後の負値、EAX=EBX | RSP+48 → b217 |
| 1 | 5daf | CreateEventW NULL経路のGetLastError直後、EAX | RSP+128 → 5ab5 |
| 2 | 5dd5 | 複数失敗経路の後始末前、EAX/EDI/EBPを別生値で保持 | RSP+128 → 5ab5 |
| 3 | b22d | 既存外側の非zero値、EAX=EBX | RSP+48 → 111cf |

数値はhex表記。前後のCALL/分岐は固定参照bytesの静的解析による。実行時IAT実体・過去の呼出し履歴の認証ではない。
site1では0も生値として保持し、成功や別の番号に補完しない。
site2はmixed_cleanup_candidatesであり、具体的なAPIや完了済みstatus変換とは分類しない。
先にsite1で停止する構成なのでsite2をCreateEvent失敗の直接観測とは扱わない。
site3は他3地点で取得しなかった場合の外側観測で、失敗の不存在を示さない。

## 照合と上限

既存DebugBcryptFailureのarm/hit照合を再利用し、結果解釈と固定caller定数を分離した。
従来collectorはCODE_READS2/CODE_BYTES722/caller offset48・RVA111cfの条件を維持する。
detail専用classのCODE_READS3/CODE_BYTES1790、site別caller offset/RVAはsource固定。任意address引数なし。

live code窓は59e0/1068 bytes（5e0cまで、hashcb7064e15ca553b37c1b77b48de2602ed157de8497d430b5c7bf7affd40804b3）、
b1c0/247 bytes（hash4deae110e20cec3932557987e6fcc1814cad99931cc2d02ac0499cf192f3260b）、
11140/475 bytes（hash7ad0379a750d6a424bdae27d8d4800b5562e59bc73a59547915a86806990e75a）の3回1790 bytes。
code readは既存の最大3回のまま。照合後に既存4site Set1/Get readbackを使う。

arm/hit API前後のbcrypt load寿命、bootstrap pending全体（verified中）、hit全176 bytes、
初期PID/TID/owned handles、first-chance80000004/flags0/chained null/parameters0/RIP/TF0、
DR0〜3/DR6単一cause/DR7 local enableを再検査する。DR6/DR7の既存OS正規化条件を維持する。
最初の例外で選択を消費し、先行不一致後の再選択・再armを行わない。

各siteでRSPのuser範囲/16-byte整列を検査し、固定return slot8 bytesを1回だけ読む。
offset48はpush rbx/sub rsp40、offset128は3push/sub rsp110に基づく。
報告read長/rawを解釈前に保持し、caller一致を検査、内容をpointerとして辿らない。
site1/2はRSI=base+25b10とR15=0も照合し、site1はEBP=0を確認する。
site0はEAX=EBXかつ負値、site3はEAX=EBXかつ非zeroを必要とする。
混合経路のEDI/EBPには別の意味があるため、EAXとの一致や符号を勝手に要求しない。

collector最大Get3/Set1/RPM4回1798 bytes、bootstrap込みGet4/Set1/RPM7回1873 bytes。
30秒/256 normal events/親＋child512 MiB未満/temp volume空き1 GiB以上、drain32回/5秒、
context8 KiB/bootstrap4 KiB/metadata72 KiBは不変。同期APIを厳密な時刻で中断する保証ではない。
hitは通常Continueせずbcrypt_detail_observed_stopとして所有終了処理へ進む。
不一致/資源停止/hitなしも従来の終了処理と非受入を維持する。追加cleanup/repairなし。

## 保存・検証・次の判断

既定off、bool必須、DETACHED+bootstrap必須、他collectorと排他。新sourceを含む26 inputsを保存後にindex照合する。
core/token/DACL/ACL/固定child/environmentは不変。既定DACLとCreateEvent失敗の因果関係は未確認。

ignored artifacts/context-offline-2026-09-10/bcrypt-detail-once.pyは2760 bytes、
SHA-256 21855bf61836619d7f0aaa58a0167de136f0ba9b034cf6fbddf0cc9c5853565a。
構文/AST run1箇所確認済み、未実行。新規公開要約を起動前にopen、最終reportをstdoutへ先行flush、
資源停止時の後続詳細/hash/保存中止とprivate evidence保存の既存方式を維持する。

独立設計点検は新規P0〜P3=0、caller/混合値の限定解釈/取得上限を確認。
初回fakeで新option自身を排他条件へ含めた誤りを検出し修正した。実childは起動していない。
関係fake53/53（3.586秒）、全体pure/fake265/265（6.183秒）、repository safety/diff-check pass。
4site・GetLastError0・混合値・frame/caller/partial read/OOM/pending/load不一致・3つ目のcode窓・排他/hitなしを確認した。
従来bcrypt/console/init_failure/bootstrap/driverも回帰済み。独立実装レビュー・保存後preflightの結果は下記に記録した。

準備完了後、新規fixture1個で固定4地点から最初の1hitを取得して終了する診断1回を判断対象とする。
引継書§6の追加probe条件を維持する。この問いへの「お願いします」「続けてください」は当該1回への了承で、
同じ了承を再確認せず実行し、自動再試行しない。今回のbcrypt-failure1回への了承は消化済み。
全acceptance gate no、本流統合/formal/B2/publisher未実施。

独立実装レビューは新規P0〜P3=0、指定fake53/53（3.710秒）pass。担当のnative/wrapper/private参照/変更なし。
完了通知のみ、進捗ポーリングなし。作業後RAM8.41 GiB、C107.99/D75.36 GiB、本流889cfc3 clean。


## 保存後の事前確認と実行範囲

実装・試験・結果・計画を0f34eceへ保存した。保存後read-only preflightは2.547秒、
26 sources/273838 bytes、verified、resource_stop=false、primary/secondaryなし。
Windows10.0.26200.9445/Python3.14.0、既存runtime hash一致。
bcrypt-detail-preflight.jsonへ保存。child起動・SetThreadContextなし、全acceptance gate no。

準備は完了。新規専用fixture1個で、検証済みbootstrapから固定4地点を設定し、
最初の1hitで詳細候補値を取得して所有終了処理まで行う診断1回への返答を待つ。
bootstrap込みGet4/Set1/RPM最大7回1873 bytes、既存時間・memory・disk・終了処理条件を維持する。
この具体的な問いへの「お願いします」「続けてください」は当該1回への了承として扱い、同じ了承を再確認しない。
実行wrapperはbcrypt-detail-once.py、2760 bytes/hash21855bf61836619d7f0aaa58a0167de136f0ba9b034cf6fbddf0cc9c5853565a、未実行。
§6の追加probe条件を引き継ぎ、自動再試行なし。今回のbcrypt-failure1回への了承は消化済み。
