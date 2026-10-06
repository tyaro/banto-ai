# v0.3 正式受入前の証拠索引・runner由来候補 v2（2026-10-07）

## 現在の判定

`s4_acceptance_not_frozen`、`formal_permission=false`、正式credit0、登録holdout観測未読。これは保存証拠の索引であり、契約採択・S4合格・正式評価開始許可ではない。追加agent0。全7役nativeの反復0、業務workerと既存checkerは終了済み。

実データ作業は保存済み合成dev8/smoke2の120区間・240 dataset・720評価のengineering読取り・記述報告まで。今回も実設備・顧客データを書き換えない。

## revisionと証拠の対応

| 対象 | revision / run | 確認できた範囲 |
| --- | --- | --- |
| [全7役runtime・共通予算native](anomaly-multiseed-v0.3-seven-role-runtime-common-budget-native-2026-10-07.md) | `343c8639b0acfb2be535c02b5aaf4288b8f3d43e` | 7役・14phase、元handle/exit/reap、外部pin、架空1区間22 payload＋479 metadata、outer690.576/1800秒。保存checker57 raw/103 sourceと4974 raw/60 source pass。 |
| 最新native文書保存点のCI | `21d386692398710c050fa5ab3b4a96db73b95be0` / [37547050883](https://github.com/tyaro/banto-ai/actions/runs/37547050883) | 索引作成時はin_progress。完成raw未保存なのでCI合格を宣言しない。 |
| saved-readerの保存済みCI | `3d2ebfbd62a2eb78a0d42976743b021ff78d967e` / [37498814612](https://github.com/tyaro/banto-ai/actions/runs/37498814612) | 全3job success、両minor各3051件、必須28試験/共有29fixture、外部pinと全journalの再照合。全job runner20260927.320.1。 |
| publicationの保存済みCI | `97370f3a355a60c3e8650325a2c1559a7aff1763` / [37485069436](https://github.com/tyaro/banto-ai/actions/runs/37485069436) | 全3job success、両minor各3039件、必須28試験/共有29fixture。test2jobは20260927.320.1、compareだけ20261004.327.1。 |

各証拠は表のrevisionに限定する。先行CIを後続runtime codeや最終凍結revisionの合格へ読み替えない。

## runner由来候補 v2

既存の[候補検証器](../../tools/ci_verify_runner_origin_candidate.py)を拡張した。v1の単一image形式を保持し、v2では外部pin付き `images` / `job_images` で各jobを実版へ結ぶ。保存run/attempt/HEAD、正確な3job inventory・時刻・checkout、各実logのOperating System / Runner Image group、公式release/tag・README metadata/base64/Git blob・raw、各minor journal全記録を照合する。

`gh run view --log` のjob/step prefixと先頭timestamp内のBOMを扱い、別job prefixを拒否する。Image Versionの宣言はrelease/READMEとも単一でなければ拒否する。runner provisionerの別Version行や変更履歴表の文字列をimage版として採取しない。

公式[20260927.320 release](https://github.com/actions/runner-images/releases/tag/ubuntu24%2F20260927.320)は保存時prerelease=false、[20261004.327 release](https://github.com/actions/runner-images/releases/tag/ubuntu24%2F20261004.327)はprerelease=true。v2はこの状態を外部image pinへ明記し、保存応答と一致を要求する。prerelease=trueの候補を記録することは正式採択を意味しない。API通信の真正性、稼働VMの全bytes digest、正式runner代替規則の採択を認証しない。

[保存検証summary](../../artifacts/preformal-runner-origin-verifier-20261007/summary.json)の両runは `consistent_candidate`、`full_journal_verification_status=passed`、`runner_image_digest_status=not_collected`、`formal_permission=false`。

| 保存物 | bytes | SHA-256 |
| --- | ---: | --- |
| 37498814612 candidate-pins | 2567 | `ca9ce19889569c09610357285fb0b47ee34166aaf460328ebcb5dcd06cfe82c7` |
| 37498814612 result | 3064 | `7cbdbc2ff10e4a3818738cdebdaece57491a22c8ee5d8722786d05382b2cb203` |
| 37485069436 candidate-pins | 3462 | `b88d5e60f2c52d3b79899381b0e7466ee6d891c8e8d5d9d213a052041d2b1961` |
| 37485069436 result | 3959 | `22837de0208a8427b9dca34c11351495dda4cdfbc850bd40a5d6d3e938228e57` |
| [証拠索引JSON](../../artifacts/preformal-runner-origin-verifier-20261007/evidence-index.json)（26保存file/source pin） | 5449 | `9a09fb81414bad36feb91bac6738536961e234e19edc97904178b946cf03ffd9` |
| focused.json | 1596 | `b06479a1c76176ba6b8df6791d844e076de5d78d289abbf5fc3576f1fd48860a` |

焦点47件（候補24・回帰9・共有fixture14）、1.548秒、fail0/error0/skip0、対象11 pin一致、safety PASS。47件には先行15/23件の試行が含まれるため加算しない。初回は存在しない比較test module名を指定し34件中loader error1、実33件pass。その指定ミスを `initial-test-selection-failure.json` に保全し、実在3 moduleへ修正した。新nativeや生成は実行していない。

## 正式受入に残る5項目

| 項目 | 残りの完了条件 |
| --- | --- |
| 1. 版付き運用契約 | 現26H2/build26300/UBR9457、保証A/B、root/schema/full revision、slice/sidecar、失敗/再登録、runner代替同定の採択と独立監査。旧25H2正式pinは不一致。 |
| 2. 登録入力/consumer | 登録40 seed・480区間・960 dataset・2880評価の保存形式、latest attempt/由来/終了/欠落重複を固定入力で検証し、全分母・slice・40cluster/50000 draw・全文書へ接続。架空1区間nativeだけでは満たさない。 |
| 3. 実使用依存と終了 | 7役の限定在庫・終了確認を基礎に、最終source/runtime、外部program/Git/helper inventory、異常時の業務子孫回収を最終経路へ結ぶ。完全な閉包は未了。 |
| 4. 最終同revision受入 | Ubuntu24.04/Python3.12・3.14、Windows26H2/Python3.14 native、正式dev8/smoke2全layout/両層/3候補、独立受入。保存済み過去CIを代用しない。 |
| 5. 共通予算・容量 | 正式同形の生成→初期/保存reader→主算術/別audit→staging/writer→fresh readerを同じouter clockで測り、診断等も含むsmoke基準見積りの2倍以上の空きを確認。限定nativeの余裕だけでは満たさない。 |

採択後はS5未使用holdout40 seedを新rootで一回、S6独立raw再導出、S7文書化。S5成功/実S6完了をS4開始前の循環条件にはしない。[範囲整理案v3](../anomaly-v03-s4-acceptance-scope-draft-v3.md)と既存改訂契約案は未採択のまま。

## 次の保存単位

CI37547050883の完成後、run/attempt別jobs・2journal・comparison/regression・3job logを保存し、同HEAD/workflowを固定したlocal verifierとrunner v2を照合する。runner検証器変更後のCIは別HEADとして扱う。全7役native・既存checkerを反復しない。以降は外部program/異常終了の残件を、限定試験と保存済みsourceから小さく整理する。

10:00 JST以降は新しい実行を開始せず、証拠保存・短い引継ぎとheartbeat banto-10の停止を済ませる。
