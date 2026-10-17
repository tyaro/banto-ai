# v0.3 親source blobの読取り置換境界（2026-10-07）

## 保存点と範囲

code `9af4a965c345930a0ccc2d18417ca0a1fa7244cb` をoriginへpush済み。先行code9ddaed7の[CI37559835322保存](anomaly-multiseed-v0.3-preformal-ubuntu-ci-triage-2026-10-05.md)を文書保存点 `cc0d6d5a872b49b9c36e3f0a049d89b9264d0e75` へ独立保存した後の小さいcode単位。

[document source](../../src/banto_ai/anomaly_v03_preformal_saved_row_document_budget.py)と[generation source](../../src/banto_ai/anomaly_v03_preformal_generation_publication_budget.py)の両blob比較に、opt-in `git_blob` readerを追加した。readerへ full revision・source path・working rawのbytes/SHA-256を渡し、戻り値が厳密なbytesでありworking rawと一致することを確認する。指定なしは既存HEAD/clean・Git show・10秒上限を使用する。

このcallbackはread/compare境界であり、executor・receipt保全・Job所有・外部pin検証を提供しない。production `run()`からのblob Job接続、compact receipt、worker内Git、実ロード依存、業務異常子孫回収は未実装・未確認のまま。先行4 HEAD/clean Jobや全7役nativeを反復していない。新native/worker/agentは0。

## 焦点検証

4 test moduleの47件を18.398531秒で実行し、fail0/error0/skip0、選択source/test・科学pin9件は前後不変。repository safety PASS。追加8件は、両source loopの正しいrevision/path/pin、既定Git経路、document側/追加generation側のblob不一致、停止exceptionそのものの保持・後続呼出しなし、invalid callbackの起動前拒否、HEAD差替え時のblob未起動、非bytesの比較偽装拒否を確認する。callback失敗時にbare Gitへfallbackしない。

保存rawは `artifacts/preformal-parent-source-blob-callback-20261007-prep/`。

| 保存物 | bytes | SHA-256 |
| --- | ---: | --- |
| focused.json | 1,590 | b802bce93bc57f61002317756c083aff432663849127309b54a8756bd7d5acfb |
| focused.log | 9,921 | c23cffe9aaf4818cd06fcef7b39a7b3c7520804bfd46fad5cc15dd23a9d8d333 |
| source-budget-fit.json | 10,423 | 8d80b715b63b680e1ca1e4f1a7885fa1338ba00ed285655b1afaab8b3aff19f8 |
| code-save-checkpoint.json | 862 | 96e246be20665c021363bc4f1e87fd53b26f0de606b6590985ec79c3f381b238 |

code-save checkerは3 rawの外部pin、9 focus source/test pin、65 selected sourceのworking/Git blobをcode9af4a96へ固定して照合し、当時HEAD=origin・cleanを確認した。保存照合用Gitは測定経路の認証に含めない。

## 既存上限に対する具体的な不足

sourceの現在在庫はdocument44 path /696,879 B、generation65 path /1,109,815 B。重複を含む現在の両loopは、pre/post計218 blob call。source pathの和集合は65。

既存outer leafは1,048,576 B /32 entry /depth2 /reserve131,072 Bのまま。既存owned Gitの1 call=directory＋stdout＋stderr＋receipt（4 entry）で全blobを置換すると、既存4 HEAD/clean callとresult/budgetを含め890 entryとなる。sourceを一度だけ保存しても1,109,815 Bでouter byte上限を超える。この結果は静的保存見積りであり、圧縮率や実行時peakの容量合格ではない。

次の保存単位は、このcallbackへ接続できるbounded compact receipt方式。保存対象を既存の測定root内に固定し、original handle・private Job・shared stopと既存10秒上限を保ち、stdout/stderr/receiptのraw pinと正確なcall順序・phase・revision/pathを再検証可能にする。圧縮/集約しても失敗raw・未回収元handleを保持し、保存/readback/停止失敗で次callやworkerを開始しない。既存上限の緩和や未測定rootへの移動で不足を解消しない。まだこの方式を実装・native確認していない。

## CIと正式残件

新code9af4a96の[CI37568898031](https://github.com/tyaro/banto-ai/actions/runs/37568898031)は保存照合時in_progress。最終結果/rawは未保存。完了後に同HEAD・workflow・run attemptを固定して照合する。先行CI37559835322のsuccessを新codeへ代用しない。

正式gate `s4_acceptance_not_frozen`、`formal_permission=false`、正式credit0、登録holdout観測未読。heartbeat `banto-10` はPAUSEDのまま。[正式受入5残件](anomaly-multiseed-v0.3-preformal-evidence-index-2026-10-07.md)は維持する。実データ範囲は保存済み合成dev8/smoke2のengineering読取り・記述報告まで。
