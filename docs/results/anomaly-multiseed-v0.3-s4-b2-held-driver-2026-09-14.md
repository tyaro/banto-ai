# S4-B2 保持consumerの準備・保存・終了接続

2026-09-14、基準687e563。実装savepoint **fe6f7a8cce80476396ba8eea573a9b1812fc1747**。
[設計](../anomaly-v03-held-driver-design.md)に従い、元handleの読取部品へ新規fixture準備、資源guard、証拠保存、親/祖先の終了を接続した。
新規29＋既存331＝360件pass/0.416秒。初回・最終差分の独立レビューP0〜P3所見0件。
**子の終了が不明なら元root/祖先を保持し、専用worker終了を要求する。**
今回の実行はfake APIだけ。新規実機試行0回、native入口/外側監視は未追加。

## 接続した経路

既存private-evidenceとancestor pinの接続後、source-fixtureの元rootと新規facts.json/marker-pending.jsonを準備する。
各fileはCREATE_NEWで単回write/flushし、元Observationを確認してAcquiredOwnerへ渡す。
SealedFiles/HeldConsumerを開始前に構成し、prepare証拠の保存・照合後だけ元writerをreleaseする。
全sealed fileを保持中の直接読取・前後照合・子close確認を終えてから、収集状態・byte count・hashの証拠を保存する。
保存先seal_payload.jsonは既存sinkのslot名であり、publication journalのseal_payload工程や公開成功を意味しない。
最後のguard/上位停止と子→元root→source祖先→evidence側のcloseを確認した場合だけ局所driver complete。

生のconsumer bytesは外部へ返さず、元部品のconsumer_payloadは常にisolation_unresolvedで拒否する。
準備中のpath確認、sealerの再open、evidenceのreadbackは既存通りで、consumer内の直接readと区別する。
新規source rootは既存WindowsPrivateSinkのCreateDirectoryW/再open方式。単一呼出しdirectory取得部品の保証を組み合わせた結果ではない。
同一user競合、owner/admin権限、既存API内部割当/cleanupの限界は維持する。

## 終了・停止と故障確認

RetainedSinkでbootstrap失敗時の自動finishを保留し、driverが終了順序を決める。
writer release未確認のadopted treeは全体を保持する。既存HandleOwner.finishが子close不明でも親を閉じる経路へ進めない。
新readerのclose不明でも元root/祖先を保持。rootclose不明なら祖先を閉じず、祖先close不明ならさらに上へ進めない。
descriptor/token/bootstrapの未確定状態、lifetime query例外やbool以外の応答も保持側へ倒す。
一次例外はstatus/report callbackから独立して記録し、後発MemoryErrorとgeneration/lease側のresource停止を保持する。
終了コード80(resource)/81(worker終了まで保持)/1(失敗)/0(局所完了)は記録済み状態だけから返す。
報告中の再入や正常returnしたcallbackの停止も検出し、古いcompleteを出力しない。報告生成失敗で元例外を隠さない。

fake Win32 surfaceと実際のprepare barrier・collector・所有部品で、準備から2回のdirect read、証拠保存、rootcloseまで通した。
子/root/祖先close喪失、保存失敗、未release writer、query障害、一次失敗＋後発resource、再入、異常callback応答、report故障を確認。
write/flushは固定2file、各write4096 bytes以下。prepare証拠はdriverで64KiB、収集証拠16KiB、通常report256KiB。
最初の359件pass後、既存barrier上限512KiBとの区別を明確化し、driver側64KiB制限と超過時の保存前停止回帰を追加した。これは手元照合での補強で、独立レビューの指摘ではない。
最終360件はfailure/error/skip/expected failure/unexpected successが全て0。最終根拠はcorrected-checks.jsonl。
独立レビューはread-only、進捗ポーリングなし。最終再レビュー後のコード変更なし。repository safety/diff検査pass。

資源guardは既存処理を使い最大1024点、40秒、private256MiB、working384MiB、空きRAM/disk各2GiB。
point上限、各メモリ/空き容量/時間超過をfakeで確認した。元ancestor ID/SD確認をguardへ接続している。
既存connect/sealing内部の全native呼出しを中断できるわけではなく、実機では専用workerと外側監視が別途必要。
成功/失敗後ともsourceの列挙・再open・hash/copy/deleteを行わない。報告はmetadata bytesを返すだけで、外部書込は今回実装していない。

## 保存と資源観測

60 sourceのraw bytes/Git blob/候補checkout一致。前回held-consumerの57 sourceと10 artifactsは全て不変。
corrected-checks.jsonl261905 bytes/hash4fdff65547449a40072b7ff3df79775ec5037fdf36b7c8774d926513d9c7f41f。
savepoint-evidence.json13498 bytes/hash2ebaa67b936e5e8cfbe969ab46520f13520d644f89fd9be68cea42c619f9e6c1。
ignored artifacts/held-driver-2026-09-14/へ8 artifacts/論理670411 bytes（manifest自身を除く）。初回/修正後の両記録を保持。

保存初期点UTC14:12:23は空きRAM14.29GiB/C117.55GiB/D52.68GiB、最終14:14:26はRAM13.62GiB/C117.50GiB/D51.39GiB。
開始時の軽量観測UTC14:02:30はRAM14.50GiB/C117.56GiB/D52.68GiB（ツール応答のみで保存初期点とは別）。
PC全体の空き量は減少したが原因は未特定。今回の記録量と分けて扱い、長期リーク不在や全期間最大の証明にしない。他processへの操作なし。
build26200.9445/boot2026-09-09T10:43:08.5000000+09:00。Windows Update engineering緩和を維持し、正式pinは変更しない。
既存Python3.14.0を使用。新規worker/監視/checkout/常駐process/実機fixtureを追加していない。
既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保持しcommitから除外。
本流889cfc3 clean不変。旧batch/旧source、S3/D2/production、push/merge/CI、新runtime/account/serviceへ操作なし。

## 次の具体化

新規max1枠を使う専用launcherと外側監視の仕様を固定する。clean revision/入力hash、排他的attempt作成、40秒内側/45秒外側、終了コード80/81時のcontext保持とworker終了確認、stdout単回保存を接続する。
報告やstdout書込の障害でも元の終了状態を失わず、失敗後にsourceを読み直さない条件を先にfake/構文で確認する。
その後、別clean checkoutの新規限定native試験へ進む。旧source/閉鎖済み枠は再利用しない。
親/祖先/全inventoryの共通期間、独立process/token・競合、marker write/renameと全publisher、正式OS/VM digest・B2/S4受入は未完了。
isolation_certified/protected_commit_allowed/future_immutability_proven/formal_permission/execution_authenticated=false、acceptance_status=not_completed。
