# S4-B1 初期化失敗経路のDLL候補の限定取得

状態: **候補実装・全体pure/fake・独立実装レビュー完了 / 保存後preflight前 / 実機未実施**。

## 観測対象

[bootstrap継続後の結果](anomaly-multiseed-v0.3-s4-b1-bootstrap-unload-result-2026-09-10.md)はUNLOADなしで自然EXIT C0000142だった。
次はDebugDriver(init_failure=True, detached_console=True, bootstrap=True)を使い、
ntdllのLdrpInitializeNodeが失敗を記録する固定地点RVAe86eに初期threadのDR0を1回設定する。
e868でR14D=C0000142、e86eでOR [RDI+68],100000という静的順序を確認済み。
停止点はORの実行前なので、取得flagsは失敗bitを書き込む前の値。bit未設定を失敗検証の不一致や成功とは扱わない。
R12B=0へはcallbackのFALSEだけでなく例外経路も合流するため、特定のDllMain FALSEや根本原因とは断定しない。

既定off、bool必須、DETACHED＋bootstrap必須。unload_entry/init_return/console_failureとの併用不可。
固定RVA/サイズ/hashをsourceに持ち、任意addressを受け取らない。core/token/ACL/固定child/environmentは不変。

## 設定・取得・停止

既存bootstrapの完全な照合後、そのpendingを通常Continueする前に設定する。
code窓ntdll RVAe5d0/845 bytes、SHA-256
f86272015b824466fa57a03405df5fd1728e1bed86ffe3aab15b61faf419789cをliveで照合する。
既存return-v3のdebug-register設定処理を共通methodとして再利用し、
Get DEBUG→Set最大1回→Get readbackの照合を行う。DR0〜3/DR6/DR7の空き状態、要求値、
Windows APIのDR6表現を考慮したcause mask、DR7の許容固定bit等は既存条件を維持する。
設定中もbootstrapのpending全体を再照合し、Set不確実・readback不一致ならbootstrapを通常Continueせずowned stop。
SetはDEBUG_REGISTERS groupだけ。RIP/EFLAGS/GPR/code/memory/token/ACL/PEBを書き換えない。

bootstrapを検証どおり1回継続した後、最初の例外でhit選択を消費する。
初期thread/PID、first_chance80000004/flags0/chained null/parameters0/address一致、
Get HITでRIP=e86e/TF0、DR0/DR6/DR7、R14D=C0000142/R12B=0を照合する。
先行する不一致例外後の再選択、再arm、後続threadへの設定は行わない。
hitなしで終了した場合はnot_observedとして失敗理由を保持する。

RDIのuser範囲/8-byte整列を確認後、112 bytesのentryを1回だけ読む。
rawと報告read長をfield検証前に保持し、DllBase（+30）、EntryPoint（+38）、SizeOfImage（+40）、flags（+68）を解釈する。
base/size上限、EntryPoint=R15かつ0または同image範囲、対象moduleの生存中confirmed LOADとの対応を検査。
ntdll自身のload寿命もarm/hit時に確認する。sizeは追加readの長さに使わず、pointer walkや別名読取りはしない。
module_load_slot/flags/callback RVAは失敗経路での候補情報であり、そのcallback実行や具体的拒否APIの証明ではない。

照合できたhitも通常Continueせず、init_failure_observed_stopとして既存owned terminate/pending解放/drainへ進む。
不一致・取得失敗・資源停止も同じ所有終了処理へ進み、自動再試行なし。既存fixtureのcleanup/repairなし。

## 上限と保存

bootstrapはGet1/RPM3回75 bytes。失敗collectorはGet最大3/Set最大1、
code845 bytes＋entry112 bytesのRPM最大2回957 bytes。合計Get4/Set1/RPM5回1032 bytes。
30秒/256 normal events/親＋child512 MiB未満/temp volume空き1 GiB以上、
owned stop drain32回/5秒、context8 KiB/bootstrap4 KiB/metadata72 KiBの既存条件を維持する。
同期APIを厳密なwall-clockで強制中断する保証ではない。API前後で予算・所有・pendingを検査する。
新しいcollectorを含む24 sourcesを保存後にindexと照合する。

ignored artifacts/context-offline-2026-09-10/init-failure-once.pyを準備した。
2736 bytes / SHA-256 2de5eb72f155257271d3c7aa638abc2373713dbe6e8a9e6010bbc0e72fc408c2。
構文/run呼出し1か所を確認済み、未実行。起動前に公開要約fileを新規openし、
最終reportをstdoutへ先行flush、非資源停止時だけ公開要約を保存する。
private rawは既存evidence handleへ保存し、write/flush/closeを確認する。report中OOMは既存どおり伝播して後続hash/保存を止める。

## 検証と次の判断

独立設計点検は新規P0〜P3=0。書込み前flags、最初の例外での選択消費、pending再検査、
field解釈前raw保持、load寿命照合、callback候補と実行事実の区別を明文化した。
関係fake41/41 pass（1.891秒）。bootstrapと失敗hitの全経路、Get4/Set1/RPM5、
flag未設定/設定済み/NULL callback、設定・readback・pending・hit/context/read/field不一致、OOM、
不一致例外後の再選択禁止、hitなし終了、既存return/bootstrapとの回帰を確認した。
全体回帰・独立実装レビュー・保存後preflightを追記する。

準備完了後、新規専用fixture1個でこの固定停止点の設定・取得・所有終了処理を1回実施することを判断対象にする。
引継書§6の追加probe条件を維持し、具体的な問いへの「続けてください」は当該1回への了承として扱う。
全acceptance gate no、本流統合/formal/B2/publisherは実施しない。


## 全体回帰と独立実装レビュー

全体pure/fake252/252 pass（5.164秒）、repository safety/diff-check pass。
独立実装レビューは新規P0〜P3=0、指定fake41/41 pass（2.924秒）。
共通設定処理のSet1/readback・bootstrap pending再検査、hit/loader寿命/field前raw保持、
書込み前flags/NULL callback、module候補の解釈、取得上限・単一実行・report資源停止を確認した。
担当はnative/wrapper実行/private証跡参照/source変更なし、完了通知のみで進捗ポーリングなし。
作業前後の空きRAM7.48→8.26 GiB、C107.92/D75.36 GiB。本流889cfc3はclean、追加実機なし。
