# v0.3 正式評価の運用契約・受入改訂案 v1

2026-10-04 追記：現在のWindows実測は **26H2/build26300/UBR9457** へ変わった。[今回の停止・確認記録](results/anomaly-multiseed-v0.3-registered-summary-runtime-change-2026-10-04.md)を参照。本v1案の25H2/build26200内でのUBR再受入案には含まれず、正式対象にするなら別版の計画・契約改訂と独立再監査が必要。本案の採択状態は変わらない。

状態: **proposal / 未採択 / 正式実行許可なし**。2026-10-03 の文書保存点 `03f34908ecfb4894d45670e0359f1617c1b51b1b` を基準に、[凍結計画 §8–9](anomaly-multiseed-evaluation-plan-v0.3.md)、[単一writerのengineering採択](anomaly-v03-single-writer-evaluation-proposal.md)、[consumer入出力案](anomaly-v03-consumer-io-proposal.md)、[残件表](results/anomaly-multiseed-v0.3-preformal-acceptance-scope-2026-10-03.md)の差分を判断可能な形にする。科学仕様の候補・seed・生成・分母・50,000回bootstrap・gate・選択規則は変更しない。この文書、既存のengineering成功、保存済みdev/smoke 720評価の要約完了を、S4受入やS5/S6の許可へ読み替えない。

正式運用IDの候補は `anomaly-v03-single-writer-research-v1`。engineeringで採択済みの `anomaly-v03-single-writer-v1` とは別のIDで、現行validatorは受理しない。旧 `run_campaign` の無条件 `s4_acceptance_not_frozen` と正式OS pin・registry・schema・出力rootはこの案では変更しない。正式modeを開くには、別の版付き実装・計画改訂・独立再監査・対象revisionの受入を準備し、契約を採択する必要がある。

## 対象revisionと証拠の境界

| 対象 | 現在の識別と意味 | 正式採択に要る固定 |
| --- | --- | --- |
| 本案の比較基準 | `03f34908ecfb4894d45670e0359f1617c1b51b1b`。`src` treeは `d4d6de6c37b573c740c7c900b5ac679bf2ba87d2` と同じ | 契約・実装・schema・検査を含む最終clean commitのfull SHAとraw bytesを別途指定。現在の保存点を最終受入revisionとしない |
| 保存済みdev/smokeの過去producer | `c01d1c978f78bab51391392d56cdcb7aab5afaab` で生成された合成dev 8 seed / smoke 2 seedの記録 | 新consumerや将来の正式producerの実行sourceへ付け替えない。過去の保存証拠はその時点のrevision・OS・processへ結ぶ |
| 旧正式runtime | Windows 11 Pro 25H2 / AMD64 / local NTFS、build `26200`・UBR `9168`、通常GILのCPython `3.14.0`。旧registry、schema、runtime probeも9168を固定 | 改訂案の採択と受入までは旧pinが有効。今回観測のUBR `9457` は受入済みの正式pinではない |
| 実際に開始する役割 | producer / analysis / audit / writer / writer終了後のreader | 役割別の最終source・runtime profile、起動条件、全入力/出力、process終了・回収、動的依存を最終revisionに結ぶ。既存の一部工程の観測をfull closureとしない |

## 旧§8との保証差と選択肢

| 境界 | 旧§8のまま維持する案 B | 推奨案 A: 通常権限の単一writer |
| --- | --- | --- |
| writerとreader | protected DACLで公開先のwrite/delete・子追加等を制限し、独立process/tokenのAccessCheckで拒否を確認する。実Win32 publisher、競合、非上書き、失敗証拠を受入 | 同一rootではwriterを一つだけ所有し、終了・回収を確認してから別readerを起動する。排他的な新root、非上書き、全payload再読込・hash/意味検査、最後の完了印を受入 |
| 保証できる範囲 | 旧計画に記した独立tokenからの書換え拒否を、対象fixtureとruntimeで実証する必要がある | **同時の別principalや同一利用者processによる敵対的書換えの防止は主張しない**。完了後の新規reader検査と独立auditで改変・不一致を検出し、証拠保全と失敗停止を保証範囲にする |
| 未実施試験の扱い | 旧Windows nativeの全必須項目がpassするまでS4不合格。現UBR9457は旧pin不一致で、DACL試験だけの追加でも開始不可 | 旧DACL/独立token試験をpassに書き換えない。版付き改訂で新しいS4受入範囲・失う保証・根拠を明示し、その範囲の通常権限native試験を最終revisionでpassさせる |
| 実務上の前提 | 専用principal/tokenの起動・運用、DACL publisherの完成と独立した検証、OS pin差の解消が要る | 既存のengineering単一writer/別reader実績を利用できるが、登録入力・正式consumer/S6・全役割のruntime closure・全工程予算は別途必要 |

推奨は **案 A**。これは先に採択されたengineering運用と一致し、保留中のprincipal準備を正式評価の必須経路に持ち込まない。ただし旧§8と同じ保護を得たという主張はしない。案 Bを選ぶ場合もUBR9168との差は別途解消し、旧Windows native試験、Linux 2 jobs、完全runtime inventory、正式dev/smokeを最終revisionで満たす。どちらを選んでも、元の凍結文書やregistryの値を黙って置換せず、変更理由と保証差を版付きで公開し、独立再監査を通す。

## OS更新とattemptの規則案

ここで「attempt」は単一の所有process群・入力pin・出力root・契約版に結ばれた試行、「formal campaign」はS5 producerからS6 analysis/auditの完了までを指す。OSの実測値は各役割の開始・終了時に採り、親processの値で子の値を代用しない。CPython 3.14.0のbuildとexe/DLL raw pin、AMD64、NTFS、Windows 11 Pro 25H2は候補案 Aでも維持する。

| 変化 | 提案する処理 | 証拠・再開始条件 |
| --- | --- | --- |
| 同一attempt中のOS build/UBR、Python/source、主要依存の変化 | integrity failureとして停止。部分結果と終了状態を保全し、成功receiptや完了印を付けない | 同じattempt ID/rootを再使用しない。停止後の環境だけを事後pinとして成功に変更しない |
| S5開始前、attempt間で同じbuild `26200` のUBRが変わる | 更新を妨げないが、**新UBRを自動許可しない**。新しい完全なOS/runtime tupleを版付き受入記録へ登録してから別attemptを開始 | 変更後の実機で対象native/通常権限試験、役割別runtime inventory、必要な共通回帰・独立再監査を完了。観測UBR9457は現時点ではこの候補にすぎない |
| S5開始前にbuild・release・edition・architecture・filesystem・Python pinが変わる | このv1候補の許容範囲外。別版の計画/契約改訂まで正式開始を止める | 影響するregistry/schema/runtime pinと全受入対象を明示し、独立再監査・platform試験・正式dev/smokeを新しい対象revisionでやり直す |
| S5開始後、producer/analysis/auditの**役割attempt間**でbuild/UBR等が変わる | 旧§8のglobal integrity failure規則を維持。同一formal campaignを継続・成功化しない | 途中の結果を保全する。性能を見て環境や条件を選び直さず、必要なら別version/root/未使用seedで再登録する |

許可済みtupleを無期限の「Windows 11」範囲やUBR下限として表現しない。採択時にexactな組を新契約の版付き運用registryへ列挙し、現在の実値、Python raw pin、ロードしたDLL/CRT等を証拠へ結ぶ。旧S1 registryのUBR9168を書き換えたり、旧schemaを通過したと表示したりしない。Linux CIのPython 3.12/3.14は共通契約の検証であり、Windows 3.12を正式必須に戻さない。

## 採択前に準備する実装・受入証拠

| 順序 | 具体的な成果と検査 | この案の時点で未充足のもの |
| --- | --- | --- |
| 1. 版付き改訂と入口 | 旧§8/§9との差、正式ID・対象revision・新root・失敗状態・slice mappingを固定。旧schemaのruntime欄不足は新wrapperで表し、科学identityを改名しない。正式modeは採択/受入まで読取りや出力claimより前に拒否 | 新契約の採択、正式adapter/入口、最終schema・plan改訂、独立レビュー |
| 2. 固定fixture | 予定2,880枠の欠落/重複・候補間入力差、最新attemptと外部pin、本文slice 1,233行と4系列sidecar 2,835行の在庫/値、50,000 draw、null/失敗を検査。過去の架空4drawや保存済みdev/smoke 720評価を正式実行として加算しない | 開始前に残るのは登録入力を受ける最終consumerと50,000 drawの固定入力検証。登録40 seedの実bytesとその独立導出・正式50,000 drawの成功証拠はS5/S6後に照合し、開始前に成功receiptを要求しない |
| 3. source/runtime | 最終producer/analysis/audit/writer/readerごとにclean Git/raw source、起動flag/検索経路、stdlib・extension・DLL/CRT・外部programと動的依存、process前後・入力/出力・exit/reapを外部期待値と照合。旧producer revisionと新consumer revisionを別に保持 | [source/runtime計画](anomaly-v03-consumer-source-runtime-plan.md)の最終役割profileとfull closure。部分的な選択source/終了後観測だけでは不足 |
| 4. platformと公開 | Linux Ubuntu 24.04 x86_64のPython 3.12/3.14両jobで共通fixture・stdlib回帰・repository safety、patch/build・CI image digestを保存。選択案のWindows native試験を正式候補のCPython 3.14.0/runtimeで実施。公開は全payload再検証、非上書き、writer終了後別reader、独立数値auditを別rootへ | 案 Aの新S4試験の定義と実証、旧B2全項目をどう扱うかの改訂。S6の実結果再計算はS5後の証拠であり開始前に成功receiptを要求しない |
| 5. 全工程予算 | producer、50,000 draw、独立audit、staging/公開/readerの時間・bytes・private memory・system commit・空き容量、停止/reap、失敗証拠を上限付きで固定。smoke実測から正式同形規模を推定し、計画所定の2倍以上の空き容量を照合 | [残件表](results/anomaly-multiseed-v0.3-preformal-acceptance-scope-2026-10-03.md)の予算は未採択。旧240時間/96GiB/空き32GiB案を全工程予算に代用しない |

正式S5で一部が失敗した場合、成功した区間だけで性能・昇格を判定せず、全予定枠と失敗証拠を保持する。**同じseedの都合のよい再試行はしない**。旧§9どおり、昇格証拠としての再実行には別version/root/未使用seedによる再登録を要求する。S5後のanalysis/audit再開や既存監査報告の再利用も自動許可せず、入力全hash・契約・source/runtime・対象範囲・報告pinを確認する別の再開契約が採択されるまで停止する。

## 最終的に人が採択する事項

| 判断 | 提示する確定材料 | 未決のままの扱い |
| --- | --- | --- |
| 案 Aの単一writer保証へ改訂するか、案 Bの旧DACL/独立token保証を維持するか | 失う/残す保証、正式IDとroot、最終実装revision、選択案のnative試験と独立再監査 | 旧§8を緩和したことにせず、正式入口は閉じる |
| OS更新をどこまで許すか | 同一attempt内停止、S5以降の一貫性、S5前の同build/新UBRをexact tuple再受入する案、build変更時の新version条件 | UBR9457を9168の代用にせず、旧pinのままの正式実行は不可 |
| 完成した契約・source/runtime・全工程予算でS4を受け入れるか | 最終clean revision、Linux/Windows受入、正式dev/smoke、独立レビュー、実測根拠と停止条件 | `formal_permission=false`、`S4_ACCEPTED=no`、`formal_ready=false`。正式40 seed、S6、gate、promotionは開始しない |

利用者判断を求める前に、版付き改訂、formal modeを閉じたfixture実装、対象revisionの検査、予算見積りをレビュー可能な形まで揃える。採択後もS4の全受入が終わるまではS5を開かない。
