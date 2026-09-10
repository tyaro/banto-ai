# S4-B1 bcrypt.dll 内部の失敗値を1回の診断で取得

状態: **候補実装・pure/fake259件・独立実装レビューpass / 保存後preflight前 / 実機未実施**。

## 観測の目的

[今回の実測](anomaly-multiseed-v0.3-s4-b1-init-failure-result-2026-09-10.md)はbcrypt.dllを初期化失敗経路の候補として示した。
次はDebugDriver(bcrypt_failure=True, detached_console=True, bootstrap=True)を用い、
検証済みbootstrap pendingで初期threadのDR0〜3へ以下の4地点を1回設定する。

| DR | bcrypt RVA | 静的な直前経路 | 取得値 |
| --- | --- | --- | --- |
| 0 | b270 | b3b8の戻りをEAX→EBXに保持し、非zero分岐 | EAX=EBXの非zero値 |
| 1 | b24d | b348の戻りをEAX→EBXに保持し、非zero分岐 | EAX=EBXの非zero値 |
| 2 | b22d | 59e0の戻りをEAX→EBXに保持し、非zero分岐 | EAX=EBXの非zero値 |
| 3 | 1128d | GetModuleHandleExWがFALSEの経路でGetLastError呼出し後 | EAXの生値（0も保持） |

前3件の値は非zeroの候補で、負のNTSTATUSや特定APIのエラーとは分類しない。
後1件はPE import名と静的CALL順序によるWin32候補であり、実行時のIAT実体や過去の呼出し履歴は認証しない。
この診断で根本原因・callbackの全実行経路を証明しない。

## 照合と取得

bcryptの一意なconfirmed LOADを選び、生存中の同じloadであることをarm/hitのAPI前後に検査する。
bootstrapの完全なpending照合も継続する。固定live code窓は次の2つ。

- 11140/475 bytes/hash7ad0379a750d6a424bdae27d8d4800b5562e59bc73a59547915a86806990e75a
- b1c0/247 bytes/hash4deae110e20cec3932557987e6fcc1814cad99931cc2d02ac0499cf192f3260b

DebugConsoleFailureの4site debug-register設定部分を共通methodへ抽出し、そのまま再利用する。
Get DEBUG→空きDR0〜3/DR6 cause/DR7確認→Set DEBUG_REGISTERS1回→Get readback確認。
要求DR0〜3は固定4address、DR7 local enable55、DR6は既存10800要求とcause maske00fで確認。
DR7固定bit400のOS正規化は従来どおり許容し、その他のbitは一致が必要。
Set不確実/readback不一致ならbootstrapを通常Continueしない。

bootstrap継続後の最初の例外でhit選択を消費する。
初期PID/TID/owned handles/first-chance80000004/flags0/chained null/parameters0/RIP/TF0と、
DR0〜3/DR6の単一cause/DR7を照合する。hit pending全176 bytesもAPI前後で再照合する。
先行不一致例外後の再選択、再arm、後続threadへの設定をしない。

前3地点ではRSPの範囲/16-byte整列を確認し、固定prologue push rbx/sub rsp40に基づく
RSP+48のreturn slot8 bytesを1回だけ読む。報告read長とrawを解釈前に保持し、戻り先bcrypt+111cfと照合。
内容をpointerとして辿らない。EAX==EBX!=0も必要。
後1地点ではRDI==bcryptbase/ESI==0を照合し、追加stack readなし。GetLastError=0も成功と解釈せず生値で保持。

hitを確認できても通常Continueせずbcrypt_failure_observed_stopとしてowned terminate/pending解放/drainを行う。
取得失敗/不一致/資源停止も所有終了処理へ進む。hitなしの既存reason init_failure_not_observedは、
監視期間と初期threadで未取得の意味で、失敗経路が存在しないという意味ではない。

## 上限と起動方法

collectorはGet最大3/Set最大1/RPM最大3回730 bytes（code722＋caller8）。
bootstrap込みGet4/Set1/RPM最大6回805 bytes。4地点目はRPM5回797 bytes。
30秒/256 normal events/親＋child512 MiB未満/temp volume空き1 GiB以上、drain32回/5秒、
context8 KiB/bootstrap4 KiB/metadata72 KiBを維持する。同期APIを厳密な時刻で中断する保証ではない。
既定off、bool必須、DETACHED＋bootstrap必須。他collectorと排他、任意address inputなし。
新sourceを含む25 inputsを保存後にindex照合する。core/token/ACL/child/environmentは不変。

ignored artifacts/context-offline-2026-09-10/bcrypt-failure-once.pyは2735 bytes、
SHA-256 7a452b75ccfc721ecfd53ca8293b0fc9ccaae599fc6c0aec9555a57f49c1b2a8。
構文/AST run1箇所を確認済み、未実行。公開要約fileを起動前に新規openし最終reportをstdoutへ先行flushする。
資源停止時に詳細構築/hash/後続保存へ進まない既存方式を維持する。privateは既存evidence handleへ保存する。

## 検証と次の判断

独立設計点検は新規P0〜P3=0。非zero値の未分類、GetLastError0の保持、hit時load寿命、未取得の限定解釈を確認。
初回fakeで待機中slot=Noneをload寿命照合へ渡すTypeErrorを検出し、選択slotを持つarm/hit中の照合へ修正した。
関係fake47/47 pass（2.935秒）、全体pure/fake259/259 pass（5.006秒）、repository safety/diff-check pass。
4site・0/非zero・Set/readback・code/pending/load変化・CONTEXT・caller短read/不一致/OOM・再選択禁止・hitなしを確認した。
既存console/init_failure/bootstrap/driverも回帰確認済み。独立実装レビューと保存後preflightを追記する。

準備完了後、この固定4地点から最初の1hitを取得する新規fixture診断1回を判断対象にする。
引継書§6の追加probe条件を維持し、この問いへの「お願いします」「続けてください」は当該1回への了承として扱う。
同じ了承の再確認や自動再試行なし。今回のinit-failure実行1回への了承は消化済み。
全acceptance gate no、本流統合/formal/B2/publisherは未実施。

独立実装レビューは新規P0〜P3=0、指定fake47/47（2.818秒）pass。担当はnative/wrapper/private参照/source変更なし。
完了通知のみを利用し進捗ポーリングなし。作業後空きRAM8.55 GiB、C107.98/D75.36 GiB、本流889cfc3 clean。
