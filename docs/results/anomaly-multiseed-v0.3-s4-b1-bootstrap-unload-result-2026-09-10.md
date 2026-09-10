# S4-B1 検証した初期停止点の継続と自然終了の観測

状態: **診断observed / bootstrap継続confirmed / 自然EXIT C0000142 / UNLOADなし / no native acceptance**。

ユーザーの「お願いします」を[計画](anomaly-multiseed-v0.3-s4-b1-bootstrap-unload-plan-2026-09-10.md)の1回への了承として、
cleanなca6a6da（実装4c964c8）で新規fixture1回を実施。wrapper2768 bytes/hash
01f6e8074f8bfc1657b2b0eed4c02b5f4bf4a35ae37ed88a754442e7e4d6350bを照合し、自動再試行なし。
初期reportまで2.376秒、driver/observer observed、primary/secondaryなし、resource_stop=false。
要求flags0x40e/creation_state=created/ownership transferredを証跡でも照合した。

## 経過と結論

通常22 events/Continue22。python.exe＋13 DLL load、3 create_thread、slot17で初期停止点、
slot18〜20でthread exit、slot21でprocess exit。後ろ4件は全て0xC0000142。
bootstrapはntdll LOAD slot1、初期PID/TID一致、80000003/first_chance1/flags0/chained null/parameters1/parameter[0]=0。
exception RVA122239、実GetによるRIP RVA12223a、TF0/RSP16-byte整列、code62 bytesの固定hashを確認。
callerはRVA8df44（LdrpInitializeProcessのCALL後）、caller8 bytes/CALL5 bytesが一致した。
Get1/RPM3回75 bytesでverified、同じpendingのDBG_CONTINUE完了までconfirmedとなった。
RIP=address+1という前回未測定だった候補条件を、このrunで確認できた。

UNLOADは無く、従来contextはready/not_observed、entry not_startedのまま。追加Setなし。
自然EXIT C0000142を観測したので、初期停止点以降にも起動障害が残っている。
今回どのDLL/内部APIが失敗したかは未特定。診断のobservedをchild E2E成功に読み替えない。

## 終了・保存・資源

Terminateはnot_started、drain0件。process signaled、debug ownership解消、所有process/thread handle close、
teardown pass/failure_count0、driver teardown failures0を確認。
stop側exit_continued=falseはdrain処理が不要だった記録であり、通常側22/22 Continue/自然EXITと区別する。

private113291 bytes/hashc5aae2427953ccc3d1545fecf6a2e33e7c0d41818f022a8f99cbb3a9185c46d2、
write/flush confirmed、file closed。有界held-file read1回でhash、raw全events、bootstrap CONTEXT/code/caller、
launch/stopを照合しreader close。両領域inflight false、未確認領域の非zeroなし。
公開記録bootstrap-unload-native-summary.jsonl/readback.jsonへ保存。fixtureは保持し存在確認/repair/削除なし。

同run preflight23 sources/255021 bytes、Windows10.0.26200.9445/Python3.14.0、既存runtime hash一致。
last boot2026-09-09T10:43:08.5000000+09:00。UBR緩和を維持して実測buildを記録。
memory153 samples、親＋child peak commit27140096 bytes（25.88 MiB）、peak working36941824 bytes（35.23 MiB）。
実行前RAM7.48 GiB、C107.92/D75.36 GiB。単発値からリーク有無未判定。他project操作なし。

次の観測には、既存のntdll静的解析を再利用する。追加DLL/PDB read/downloadはしていない。
init-failure-probe-recipe.jsonで既存845-byte窓/hashとe86eの失敗bit書込み命令を照合した。
次は[初期化失敗経路のDLL候補を取得する計画](anomaly-multiseed-v0.3-s4-b1-init-failure-plan-2026-09-10.md)を参照。
全acceptance gate no、本流889cfc3はcleanのまま。


準備作業後の空きRAM8.26 GiB、C107.92/D75.36 GiB。次の候補はpure/fake252件・独立実装レビューpass。追加実機なし。
