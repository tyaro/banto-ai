# S4-B2 公開状態モデルの設計・検証結果

日付: 2026-09-11。基準f9f3ea5、実装savepoint e42a8e55768278ad10388b8f4017a308aa74ebd8。

**実機接続前のpureモデルを作成し、16 testsと関連3 testsがpass。独立レビュー2回の新規P0〜P3は0件。**
公開APIや実機publisherは追加していない。実機受入・正式試験の許可には数えない。

## 今回確認したこと

[設計書](../anomaly-v03-publication-model-design.md)に、prepare / verify_prepared / seal_payload /
rename_payload / verify_final / commit_markerの6境界と、別扱いのteardownを固定した。
native adapterが操作を始める前にintentを記録するためのpure journalであり、操作自体は実行しない。

- 途中失敗で既成功・失敗/不明・未着手を分け、後続操作や同一attemptの再試行を拒否する。
- mutationの成功応答がない場合はunknown。commit応答喪失を「未公開」と決めつけない。
- commit成功後にteardownが失敗した場合は、commit confirmedを残したまま全体はstopped。
- 順序違反を握り潰しても停止状態を解除できず、早い完了印・二重開始・未開始の成功通知を拒否する。
- 最初の失敗原因を残し、後発resource stopは別flagを昇格する。snapshotは独立したコピーを返す。
- toy markerはexternal digest、source revision、全payload bytesからexact再構成して照合する。
- case alias、親directoryの表記違い、file/ancestor衝突、traversal、型違い、超過入力を拒否する。

payloadは最大8 files、各64KiB/合計256KiB、path128文字、marker16KiB。
JSON payloadの意味や実native操作の実行をこのbyteモデルで証明しない。
trusted inputとexternal pinを両方交換した場合、独立した意味検査が別途必要なことを反例試験でも明記した。

16 testsは0.009秒、failure/error/skip0。6操作それぞれへの通常失敗/resource failure、型違い、
自己申告の受入flag、marker再hash、late failure、copyの改変、停止後の誤操作を含む。
これらはpure/fault試験であり、native競合・DACL・AccessCheck・独立childを実行した数ではない。

SourceCollectorTests 2件とD2 exact historical/current inventory 1件も3/3 pass、11.024秒、skip0。
historical 88 pathsとcurrent-only 32 pathsを保持。src/科学schema/config/registry/正式OS pinは変更なし。
正式入口の無条件拒否、未受入flagも維持する。repository safety / 最終diff-check pass。
最初のdiff-checkがtest末尾の空行1行を検出したため除去。試験後の変更はその1行だけで、
保存時に元のraw hashとの関係を照合した。試験結果を得るための繰り返し実行はしていない。

独立レビューは、モデルと設計書、および追加した親directory alias拒否と16 testsに分けて実施。
両方で新規P0〜P3指摘0。担当の試験・native・ネット・編集なし。進捗ポーリングなし。
レビューはcallerの自己申告から実行/意味検査を証明できない限界を保持した。

## 保存した小さな記録

保存先は新規ignored rootの artifacts/publication-model-2026-09-11/。

| 記録 | bytes | SHA-256 |
| --- | ---: | --- |
| local-checks.json | 3372 | 7071316a99db3707d7cbbd0b3e6ba2b5a968907a711b53c1610a6beef8740fb4 |
| source-boundary-checks.jsonl | 2423 | 21627daa2d53c0c6cd93eb34e52a3fd76337ba9df54f8615233b3d0ced7fdf5c |
| model-examples.json | 8995 | 7653246ed5743ecad9b682383b3accc2df5a4b207da90c26fa086181926ca587 |

local-checksは最初の16件のconsole結果とそのID/source hash、関連3件の実行結果を区別して保存。
model-examplesは正常モデル、6工程の各失敗、commit後teardown失敗の計8例であり、実機証跡ではない。
savepoint-evidence.jsonに確定commit、最終source hash、空行1行だけの整形差と記録hashを保存した。
今回の結果を前回のLinux CI成功に足し込まない。今回のprototypeはローカルWindows3.14.0でのみ検証した。

## 資源と次の境界

開始UTC01:12:08Z RAM空き8.32GiB/C105.51GiB/D75.36GiB。
最終UTC01:28:35Z RAM8.38GiB/C105.56GiB/D75.36GiB。
build26200.9445、boot2026-09-09T10:43:08.5000000+09:00を記録した。
C空きは今回開始前に前回終了時107.67GiBから減っていた。原因は未調査で、この作業への帰属やリークを断定しない。
今回の試験・記録processは終了し、常駐処理なし。新runtime導入、別project、既存失敗fixtureへの操作なし。

本流889cfc3は変更なし。候補をローカル保存し、今回のpush/merge/CI起動はしていない。
次はnative adapterに必要な保持handle、marker/親directoryの保護、競合・flush/close失敗時の証跡を具体化する。
B1必須受入と正式OS条件、VM image digest、runtime closure/consumer凍結も残る。
終了済みB1 native試行枠を流用しない。formal_permission/execution_authenticatedは常にfalse。
