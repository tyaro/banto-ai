# v0.3 正式受入残件の更新（2026-10-01）

**架空データの5payload結合、数値計算worker、主集計の独立検算、共有資源監視まで接続済み。次の実装は条件別集計（slice）・補助診断表の独立検算とする。** 正式受入の5まとまりは引き続き開いているが、完了したfixture部品を未実装へ戻さない。この5は残り試験数やPhase2/3全体の残件数ではない。

対象実装は`cf4d9c42c11c202984aacdd71ac5efb0368f22d0`、clean候補は`fb02/banto-ai`。文書保存点の起点は`27e4d746979e9792b61b0017482890d0643565b1`。[前回の残件整理](anomaly-multiseed-v0.3-acceptance-gap-update-2026-09-26.md)を、以降の保存証拠に合わせて更新した。

## 今回の確認と再利用する証拠

保存点7本と小さいreceipt13本、計20file/223,090bytesを既知の外部pinで照合した。現実装72code/18dataのraw pinも一致。11sourceの限定的な静的読取りで、正式入口の無条件拒否、旧公開の4payload限定、primary auditの明示的な除外範囲を確認した。評価・数値再計算・試験・公開processの新規起動は0。旧720評価のpayload全読取りや50,000反復を行った確認ではない。

| 保存証拠 | その時点で確認済みの範囲 | 今回の扱い |
| --- | --- | --- |
| [実レポート公開](anomaly-multiseed-v0.3-saved-report-publication-2026-09-26.md) | 保存済みdev/smokeの7入力→4payload→通常writer→別reader | 通常公開・別reader接続は完了。新5payloadの公開実証とは区別 |
| [wrapper](anomaly-multiseed-v0.3-wrapper-fixture-2026-09-30.md) | 16試験pass、架空の全予定枠・草稿・診断・実行記録を5payloadへ結合 | pure adapterの再実装・再試験はしない |
| [数値worker](anomaly-multiseed-v0.3-fixture-worker-2026-10-01.md) | 15試験pass、架空40cluster/4drawを所有子で計算し5payloadを保存 | 正式40seedの実観測、50,000反復とは区別 |
| [主集計audit](anomaly-multiseed-v0.3-fixture-numerical-audit-2026-10-01.md) | 22試験pass、別算術・別processで9主表/117絶対推定/72対応差/180gate一致 | 主集計は独立検算済み。slice/sidecar導出は対象外 |
| [資源停止](anomaly-multiseed-v0.3-fixture-resource-budget-2026-10-01.md) | 新budget16＋supervisor13＋analysis15＋audit9の53試験pass、共有rootでanalysis→audit成功 | 現候補の限定fixture停止条件は接続済み |
| 旧dev/smokeのslice監査 | 120区間/720評価の記述診断を保存・監査済み | 旧保存点を再利用。新しい40cluster草稿の全mappingを独立検算した扱いにはしない |

試験数は異なるrevision・重複する対象を含むため合算しない。現候補の53試験は全repository回帰や正式受入試験全体ではない。旧primary pure 13試験やwrapper 16試験の記録は、その対象codeが不変であることと併記して保持する。初回資源試験の失敗記録も保全し、成功記録は`tests-2`である。

## 正式化に残る5まとまり

| まとまり | 完了として保持する部分 | 正式開始前に揃えるもの | 正式実行後に確認するもの |
| --- | --- | --- | --- |
| 1. 運用契約 | engineeringの単一writer、終了後reader、OS更新の状態記録 | 科学条件を変えない契約差分、slice mapping採択、対象revision、失敗時の再登録規則。予約IDはdraftのまま | 採択条件と実際のattempt・環境・終了状態の一致 |
| 2. 登録consumer | 旧720評価の集計部品、架空40clusterの推論・5payload・主集計audit | 登録40seed/480区間/2,880評価のcoverage・全入力・終了記録を認証して推論へ渡す入口、正式50,000反復と完全文書の接続をfixtureで検証 | 登録データの全入力/集計、固定反復数、完全文書の検証 |
| 3. 役割とsource/runtime | reader・保存結果準備・架空数値analysis/auditの所有子、選択source/依存観測・外部期待値との対応 | 数値analysis/audit/writer/readerの最終役割仕様と候補profile、動的依存・外部programを含む不足範囲、clean固定元・必要な最終回帰 | 各実processの前後source/runtime、入出力、終了・エラーと外部期待値の一致 |
| 4. 公開・読取り・独立検算 | 旧4payload通常公開と別reader、架空5payload生成、主9表の独立検算 | slice/補助表の別実装検算、新5payloadとwriterの実行証拠・公開receipt・reader・auditの対応 | 同一の実解析結果が保存・公開・別読取りされ、全対象が独立検算された証拠 |
| 5. 全工程予算 | 小さいfixtureの共有時間・directory・親/子メモリ・system commit監視と停止/reap | producer、正式推論、全範囲audit、公開と保存を含む予算、計測根拠、停止・再登録条件の採択 | 実消費量、停止条件、記録保全・終了の適合 |

開始前には実装・契約・固定方法とその検証を揃え、実行後には実際の成功/失敗証拠を確認する。**正式実行後にしか得られない成功receiptを、正式実行を開始するための前提へ循環して要求しない。**

## T01〜T12の対応更新

| 項目 | 現時点の確認範囲 | 残る境界 |
| --- | --- | --- |
| T01 mode | fixture/engineeringの区別、formal入口の拒否 | 正式契約の採択とaccepted入口。`require_campaign_acceptance`は引き続き無条件拒否 |
| T02 入力pin/配置 | 外部pinと固定inventory、保存済み7入力、fixture入力の対応 | 登録producerの全payloadと終了証拠を受け取る契約 |
| T03 coverage | dev/smoke 120区間/720評価、架空2,880予定slotの欠落拒否 | 宣言だけでなく、登録40seed/480区間/2,880評価の実出力からの認証 |
| T04 attempt/失敗 | partial/failed/not_startedを成功にせず、inconclusiveも区別 | 正式失敗時のversion・root・未使用seedによる再登録と結合 |
| T05 観測・score・ledger | 旧720評価の独立生成/score/ledger監査 | 新しい登録入力から監査記録までの入口 |
| T06 集計 | 既存seed集計部品、fixtureのratio-of-sums等を独立検算 | 登録全入力の認証と完全なcoverageを結ぶadapter |
| T07 推論 | 架空paired draw/type-7 CI/zero分母/主gateの計算と別実装検算 | 正式50,000反復の入口・完全文書への結合・予算。workerは最大8draw |
| T08 slice/診断 | fixture本文1,233行・補助4系列2,835行・詳細9表のmapping、旧dev/smoke診断監査 | この40cluster草稿のmappingを別実装で検算。正式mapping採択と登録観測からの導出はさらに別段階 |
| T09 実行証拠 | 数値analysis/auditの実子まで親保持期待値と対応 | writerを含む最終役割仕様、最終profile、完全source/runtime固定の不足 |
| T10 保存/公開 | 5payload生成・保存、旧4payload公開・別reader | 新5payloadを公開writer/reader/audit receiptへ接続 |
| T11 停止/保全 | partial/unconfirmed/応答喪失/reader失敗に加え資源停止・reap | 正式全工程の状態・receipt・再登録規則と予算の結合 |
| T12 独立検算 | 9主表/180gateを別算術・別processで検算 | slice/sidecar、登録入力、正式完全文書、公開・readerとの結合。S6全体は未完了 |

正式草稿の`status / provenance / analysis_consumer / bootstrap`はnull、`ready=false`を保持する。4欄は「あと4試験」の意味ではない。条件付き主表の一致から正式合格・候補昇格・完全closureを推定しない。

## 次の実装単位：架空slice/補助表の独立検算

現在のprimary audit receiptは`slice and diagnostic-sidecar derivation`を明示的に対象外としている。既存slice adapterは計算側の`anomaly_v03_slices`・`anomaly_v03_descriptive_report`等を呼ぶため、そのadapterを再実行して一致させるだけでは別実装にならない。

次工程は以下を一つの完了単位とする。既存5payload・数値workerを作り直さず、保存済みの架空入力と文書を使う。

1. **入力を固定する。** 40clusterのprimary入力、slice用raw count、保存文書、対応する外部pin/analysis記録を受け取る。audit側でslice入力pinを新たに保持・照合し、別の入力への差替えを拒否する。旧primary-only receiptはそのまま保全し、新しいscopeを識別できるreceiptにする。
2. **別の計算で検算する。** 計算側のslice集計・mapping関数を呼ばず、固定key inventory、class/equipment/modeの周辺・結合表、target/mode、histogram、分母・省略・null規則を検証する。cluster→stratum→overallの加算、primaryとの対応、本文1,233行、補助4系列2,835行、詳細9表を独立導出して比較する。数が同じだけの別ラベル・別割当も拒否する。
3. **意味のある改変試験を行う。** 正常例、本文だけの改変、補助表だけの改変、合計を維持したcell再割当、欠落/重複key、ゼロ分母・null、histogram/profile/primary不整合を対象にする。文書とhashを再保存して整合して見せても、数値・意味の違いを検出する。
4. **既存所有auditへ接続する。** 必要な入力・選択source・依存期待値の変更を記録し、所有子の終了/reapと限定資源停止を維持する。元analysisを再計算せず、保存例を1回だけ別auditへ渡す。変更箇所に関係する試験を実施し、旧保存点・失敗記録を残す。
5. **範囲を明記して保存する。** 成功しても架空countからのslice/sidecar検算に限る。raw登録観測の導出、登録coverage、正式50,000反復、正式mapping採択、writer/publication、S6/closureは別の残件として保持する。

仕様・入力の不足で作業範囲を広げる必要が出た場合は、その不足と具体案を記録する。既存の最大8draw/時間/容量条件を自動で引き上げない。

## 資源と契約の境界

fixtureの既定は共有時間120秒、親private512MiB、directory32MiB/256entries/深さ8、commit/RAM余裕各2GiB、disk余裕5GiB。子は60秒/256MiB/stdout+stderr合計1MiB、従来の起動前RAM4GiB/disk20GiBも残る。親と子のprivate上限は別で、合計512MiBではない。共通monitorを渡したrootと呼出しだけが共有対象。sampling/協調checkpointであり、hard quotaや任意のnative処理の即時停止ではない。[詳しい限界](../anomaly-v03-fixture-resource-budget.md)を維持する。

今回の開始時はRAM空き約7.62GiB、commit余裕約12.29GiB、C/D空き約126.13/387.12GiB、確認processのpeak private約20.37MiB。OS Professional25H2/26200/UBR9457を観測した。旧正式pin9168を更新したものではない。終了時の資源は`save-checks.json`に保存する。

正式規模は40seed×12layout×2strata＝960dataset、3候補で2,880評価、480区間。従来のproducer概算約59.91GiB/累計178.17時間、および240時間/96GiB等の予算案は未採択。fixture例23.623秒/約11.26MiBを正式50,000反復や全監査の必要資源へ比例換算しない。登録推論・全監査・公開/保存を含む根拠を別途揃える。

単一writer案`anomaly-v03-single-writer-research-v1`は予約draft。科学条件・既存設定/schema/registryは変更せず、正式gate、holdout、principal/UAC/ACLや同時書換え作業を起動しない。Windows3.12を追加必須にしない。

## 保存と再開

- `artifacts/acceptance-gap-update-2026-10-01/savepoint-evidence.json`に文書revision、72code/18data、確認記録のpinを保存する。
- [証拠確認記録](../../artifacts/acceptance-gap-update-2026-10-01/evidence-review.json)には20fileのpinと静的読取りの範囲を保存する。既存評価・過去試験の再実施を意味しない。
- 実計算`c01d1c9`、本流clean`6f1285d`、control000010のclosed、既存dirty文書は不変。`banto-24`はPAUSED。push/mergeなし。
- 次回は上記slice/sidecar検算の実装へ進む。今回の残件表を再整理するだけの工程や、同一の公開/reader試験を繰り返す工程へ戻さない。
