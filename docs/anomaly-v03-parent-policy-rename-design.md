# S4-B2 親DACLと相対renameの比較設計

2026-09-14、基準594bf1d。[前回2回枠](anomaly-v03-directory-rename-design.md)は終了済み。
そのattempt/記録を再操作せず、新規parent-policy-rename-2026-09-14で親DACLの条件を比較する。

## 仮説と変更範囲

前回の直接NtSetInformationFile呼出しは、親に0x1600a7を保持していてもNTSTATUS0xc0000022で失敗した。
[FILE_RENAME_INFORMATIONのRootDirectory説明](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/ns-ntifs-_file_rename_information)では、
内部target openがFILE_WRITE_DATA/SYNCHRONIZEを要求し得る。親のEveryone deny0x10156にはWRITE_DATAのbit2も含まれる。
保持親の既取得権限と、新たな内部openの許否は同じではない、という仮説を比較する。
カーネル内部の拒否箇所をtraceした証明ではなく、このローカル環境・小fixtureの条件比較である。

DirectoryRenameのparent_policy既定はfrozenのまま。比較だけprivateを明示できる。
privateではrootのDACL設定だけを省き、stage固定後のroot元ID/private SD完全一致と実権限を再検査する。
証跡保存後も元root観測へ一致させ、状態はprivate_verifiedとする。固定完了のverifiedと混同しない。
stage/子fileは両条件とも同じfrozen DACL。全子close、証跡barrier、保持権限、no-replace相対要求、失敗時停止は共通。
完了後の別読取りはrootを選択したpolicy、payload/factsをfrozenで検査し、元ID/bytes/SDを照合する。
既存6工程journalはprepare unknown/stopped・teardown succeededの局所試験を維持する。

## 新しい2条件枠

| 項目 | 固定条件 |
| --- | --- |
| 新規root | artifacts/parent-policy-rename-2026-09-14/attempt-1、attempt-2のみ |
| entry | tests/fixtures/anomaly_v03_parent_policy_probe.py。既存probeを明示比較modeで呼ぶ |
| attempt-1 | 親private、stage/file frozen。rename成功・終了後3 objects一致・全closeを期待 |
| attempt-2 | 親frozen、stage/file frozen。同じ直接NT要求でアクセス拒否を検査。1の完全成功・終了を確認したときだけ実行 |
| 回数 | 各条件1回、最大2回。再試行枠ではない。1が不成功ならそこで終了、2は結果によらず終了。繰越・第3条件なし |
| 取得権限 | root0x1600a7/stage0x1700a1、share READ+WRITEでDELETE共有なし。file writer0x12019f→0x160081 |
| 内容 | 新規stage/facts.json45 bytes、markerは証跡内bytesのみ。別private sinkへ証跡3個 |
| API | NtSetInformationFile/class10/40 bytes、RootDirectory=保持root、leaf payload、上書きなし。API/名前/親のfallbackなし |
| CWD | 新規attempt親。保持source-fixture rootとは別 |
| 予算 | source4096 bytes、証跡各64KiB/3個、報告128KiB、private256MiB/working384MiB、空きRAM/disk各2GiB |
| 監視 | worker境界40秒、外側45秒。hidden保持Processを約1秒観測し終了確認 |
| 前提 | pure/fault・独立レビュー完了、clean exact HEAD/原source hash/監視hash固定、既存CPython3.14.0 Win64 |
| 正常終了 | 成功時は31 tracked handles＋token2、rename失敗時は28 handles＋token2。全closeとworker終了を確認 |
| 異常時 | 後続IO停止、所有終了のみ。native完了不明ならbuffer保持後worker exit80。不明close再試行・source再検査・削除なし |

Windows Update後のengineering UBR緩和を維持し、各build/bootを記録する。正式OS pin・runtimeは変更しない。
各条件の実装revision/API/class/bytes、CWD、writer/保持実権限、子close、証跡数、資源・終了状態を並べる。
異なるfixtureのIDやhandle値は一致を要求しないが、各fixture内部では元値との一致を要求する。
private成功/frozen拒否がそろった場合のみ親policyの違いに整合する結果とする。別要因を排除した内部因果証明とはしない。
frozenの拒否はworker exit1/directory_rename=failのまま記録し、試験比較の成立とrename成功を分ける。

## 保護と公開順序の未解決点

| 状態 | 観測できること | まだ満たさない条件 |
| --- | --- | --- |
| file/stage frozen、親private | 子の内容固定と保持stageの名前変更を試せる | 親に新しい子名を作る/親経由で消す一般操作の拒否、完了印前の親保護 |
| file/stage/root frozen | 元権限を保持したsource/親と、固定済みSDを検査できる | 前回はrenameが拒否された。marker renameも成功を仮定できない |
| 名前変更後に親固定する案 | 新しい順序の候補 | 途中のadd/delete競合、固定前後のinventory再検査、marker作成との整合は未実装 |

親privateでrenameが通っても、全publisherの順序をそのまま採用しない。
親がprivateな時間帯の通常tokenによる競合と、完了印の発行前に必要な保護を両立する設計が必要。
root固定を遅らせて6工程の成功を捏造したり、既存S3 hardlink marker/D2契約を黙って変えたりしない。
今回変更は試験fixtureの比較状態だけで、production入口・marker commit・正式pin・既存modelの工程順は変更しない。
独立token実操作、native競合/故障、全publisher、S4受入は未完了。全formal/authenticated flags=false、acceptance=not_completed。

## 実結果と次の候補

a31ae9bの同じclean実装で172件pass・独立P0〜P3=0を経て2条件を実行した。
privateはNTSTATUS0、3 objectsの終了後読戻し一致、31 handles/token2個close、worker exit0。
frozenはNTSTATUS0xc0000022/WinError5を再現し、28 handles/token2個close、worker exit1。最大2条件枠は終了。
[結果・保存記録](results/anomaly-multiseed-v0.3-s4-b2-parent-policy-rename-2026-09-14.md)を参照。

同じ公式資料が記す同一親内rename（RootDirectory=NULL、単一leaf）を、次の別adapter候補として設計する。
保持rootの同一物/寿命検査は残し、固定済み親で成功するかは別の新規仕様・pure/fault・reviewを経て実検証する。
今回の保持親形式からの自動fallbackではなく、既定API・既存6工程/S3/D2契約を変更しない。
この候補で成立しない場合は、親保護/marker順序と競合の具体案へ進む。

続く[同一親内形式](anomaly-v03-same-parent-rename-design.md)も親frozen下で5拒否となり、1回枠を終了した。
[順序案](anomaly-v03-publication-order-options.md)は未採用で、親private中の別actorの既取得権限を排除/隔離する条件が未充足。
次はこの残存権限を消去しない小modelとconsumer条件を具体化し、追加nativeより先に保護の成立条件を整理する。
