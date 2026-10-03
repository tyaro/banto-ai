# v0.3 正式評価の運用契約・26H2受入改訂案 v2

2026-10-04。状態: **proposal / 未採択 / 正式実行許可なし**。本案は[正式計画 §8–9](anomaly-multiseed-evaluation-plan-v0.3.md#v03-runtime-acceptance)と[運用契約案 v1](anomaly-v03-formal-operations-contract-proposal-v1.md)を置換せず、Windows 11 Pro 26H2への変更を別版で受け入れる場合の条件を提示する。科学仕様、登録済みseed、候補、分母、50,000 draw、gate、選択規則は変更しない。実設備や顧客データの収集は対象外で、登録holdoutの実観測もまだ読んでいない。

同日の[架空50,000 draw算術測定](results/anomaly-multiseed-v0.3-preformal-platform-raw-budget-2026-10-04.md)は主計算と別実装監査が完走したが、登録実保存reader・完全S6・公開を含む全工程予算や5役割の全source/runtime閉包は満たさない。本案の未採択状態と下記の受入順序は変わらない。

### 後続のpreformal証拠による追補（契約は未採択）

[最新の受入見取り図とraw pin](results/anomaly-multiseed-v0.3-preformal-profile-and-saved-attempt-2026-10-04.md)では、clean `e794790` で外部pin付き架空22 fileを所有コピー子→別reader子で実保存・読戻しし、clean `94be9ed` で５役の候補profile必須trial-16と、その保存済みproducerから50,000 draw主算術/別監査のtrial-03を別rootで測定した。各試行の子はexit 0/reap、保存pinの独立照合は不一致0。ただしコピー子は観測を生成せず、登録実観測・正式creditは0で、５役１drawと２算術子の予算を正式同形の全工程予算へ合算しない。完全S6、全source/runtime閉包、最終revisionのLinux CIと正式dev/smokeも残る。

保証Aを**契約改訂の候補**として勧める。26H2限定fixtureでは、単一writer、非上書き、`.complete`前の再照合、writer終了後の別readerと失敗記録に証拠がある。一方、親postflight失敗なら`.complete`が残り得るため、markerだけをattempt成功証拠にせず、外側のverified receipt、writer/readerのexit/reap、全payloadのfresh readを必須にする。保証Aは別主体の並行write/deleteをDACLで阻止した証拠ではない。旧§8の独立read-only tokenに対するwrite/delete拒否を維持する保証Bを選ぶなら、26H2でdirectory/root/markerを含むpublisher、独立tokenのAccessCheck、競合と失敗時を新たに受入れる。どちらも現時点では正式採択せず、旧§8/§9との差を版付き計画へ明記して独立再監査する。

## 変更理由と現在の境界

2026-10-04の[実測・停止記録](results/anomaly-multiseed-v0.3-registered-summary-runtime-change-2026-10-04.md)では、registryが `EditionID=Professional`、`DisplayVersion=26H2`、`CurrentBuildNumber=26300`、`UBR=9457`、`sys.getwindowsversion()` もbuild 26300を返した。registryの `ProductName=Windows 10 Pro` は互換用のlegacy文字列で、edition判定には使わない。CPythonは3.14.0、MSC v.1944、64-bit AMD64。これはその時点の観測であり、S4のruntime受入ではない。この時点のclean revisionでのfixture writer/reader実process試験は、writer起動前に `unsupported engineering runtime` で止まった。この停止試行自体は新しい保存証拠pinを実processで検証した結果ではない。

| 契約 | 許すOS | 現在の26H2の扱い |
| --- | --- | --- |
| 凍結済み正式計画・registry・`formal_runtime()` | Windows 11 Pro 25H2 / AMD64 / local NTFS、`10.0.26200.9168` と固定CPython 3.14.0 | 不一致。旧pinは変更しない。`require_campaign_acceptance()` も常に `s4_acceptance_not_frozen` を返す |
| 採択済みengineering `anomaly-v03-single-writer-v1` | 25H2を固定し、build/UBRのみ各attemptで実測・照合 | release不一致。`validate_runtime()` のbuild緩和を26H2許可と解釈しない |
| 未採択の運用案v1 | 25H2/build26200内でUBR変更をexact tupleとして再受入する候補 | releaseとbuildの両方が範囲外 |
| 本案v2 | **候補**: Windows 11 Pro 26H2 / AMD64 / local NTFS、`10.0.26300.9457`、通常GILのCPython 3.14.0 | 旧engineering入口は26H2を拒否する。新版platform-v2の限定fixture実processのみ別scopeで実施済み。正式S5/S6は契約採択とS4受入まで許可しない |

過去の25H2/build26200/UBR9457で保存したdev/smoke結果は、その時点のsource/runtime/attemptへ結ぶ。現在のOS値で過去のruntime記録を上書きせず、過去の成功を26H2のnative受入に算入しない。

## 新版に固定する契約

提案する正式運用IDは `anomaly-v03-single-writer-research-v2`、26H2のpreformal engineering検証IDは `anomaly-v03-single-writer-platform-v2` とする。前者の正式入口、後者の限定fixture入口、既存の `anomaly-v03-single-writer-v1` は別scopeとする。専用root候補はそれぞれ `artifacts/anomaly-v03-formal-research-v2`、`artifacts/anomaly-v03-engineering-platform-v2` とする。正式rootは採択時に実体pathと不存在を確認し、既存の限定engineering rootは保存済みattemptを保全して新attemptの不存在・非上書きを確認する。attempt ID、schema/wrapper、対象clean commitのfull SHAとraw source pinを版ごとに定める。旧schemaやS1 registryのOS欄を観測値で上書きしない。旧formal root、旧engineering root、過去attemptのcheckpointを再利用しない。

26H2候補のruntime tupleは、OS major/minor `10.0`、registryのedition/release/build/UBR、`sys.getwindowsversion()` のmajor/minor/build、AMD64、local NTFS、通常GILの64-bit CPython 3.14.0、compiler `MSC v.1944`、source tag `v3.14.0:ebf955d`を照合する。この日の直接再読取りでは `python.exe` raw SHA-256が `467014615a5255aca450ae88100dd2caf887da87657f00e3c2171ec44a685aec`、`python314.dll` が `f1722bd369d79fecbc85f3ed2790c30c330b9413fd74332f95b086e60dfacc2a` で旧計画の値と一致した。これは候補観測であり、全runtime閉包の合格を意味しない。両raw hash、stdlib、拡張/DLL/CRT、CPU、起動flag・検索経路は**新版の外部期待値**として独立に照合してからpinする。path名だけを同一性の代用にしない。

運用保証は[案v1の単一writer案 A](anomaly-v03-formal-operations-contract-proposal-v1.md#旧8との保証差と選択肢)を候補とする。同一rootのwriter所有を一つに限定し、終了・回収後に別readerが全payloadを再読込み、hashと意味、receipt、非上書き、失敗証拠を照合する。protected DACLと独立tokenからのwrite/delete拒否は、この案で成立したと主張しない。旧§8の保証を保つ案 Bを採るなら、そのWindows native項目を新版runtimeで別途実証する。どちらの保証を採るかは計画改訂と独立再監査で確定する。

## 受入順序と必要な証拠

| 段階 | 完了条件 | 不合格時 |
| --- | --- | --- |
| 1. 版付き改訂 | 旧§8/§9およびv1との差、選ぶwriter保証、OS exact tuple、Python raw pin、root/schema、対象clean revision、失敗・再登録規則を計画と運用契約の別版に記録。科学pinと旧registryのraw bytesを保持し、新wrapperで版の違いを表す | 旧正式入口の拒否と、現26H2に対する旧engineering入口の拒否を維持する |
| 2. 限定platform fixture | 新版engineering入口だけで26H2を明示照合。旧25H2と別release/edition/FS/Python hash、attempt中の変更を拒否する純粋な契約試験を行う。Windows実機でwriter→終了/reap→別reader、公開後改変・非上書き・失敗証拠、3種類の保存pinのtamper試験を新rootで通す | mockやOS非依存pin試験だけでnative passにしない。失敗receiptを保存し、正式gateへ接続しない |
| 3. platform全体 | 最終対象revisionでUbuntu 24.04 x86_64のCPython 3.12/3.14両jobの共通契約、stdlib回帰、repository safetyをpass。Windows 26H2/CPython 3.14.0で選んだ保証の実Win32 native試験をpass。各jobのpatch/build/image digest、pass/fail/skipを保存 | 必須skip・未実行・不一致はS4不合格 |
| 4. source/runtimeと入力 | producer、analysis、audit、writer、readerの5役割について実行前のclean Git/raw source、Python/DLL/CRTと動的依存、入力・root・予算期待値を外部pinへ固定し、実行中/後のloaded依存、runtime、exit/reapと保存bytesを照合。登録2,880枠を扱える保存形式readerを固定の架空入力と失敗例で検証し、最新attempt・独立した外部終了証拠の照合経路を接続する | 架空summaryや終了後の部分inventoryを正式観測・完全closureへ算入しない。S5前に実holdoutの成功結果を要求しない |
| 5. 固定推論と全工程予算 | 登録holdoutを使わない40架空cluster・**50,000 draw**の主推論と別実装auditを上限付きworkerで測定。producer→readerまでの時間、各process peak private、system commit/RAM最低余裕、出力・staging・失敗保全bytes、volume空き、停止/reapを工程別と全体で固定。正式同形規模の必要容量の2倍以上を開始時に照合 | 既存8/64 draw上限を単に緩めない。旧48時間/32 GiBや240時間/96 GiBを全工程予算へ流用しない |
| 6. S4採択前検証 | 新版の正式dev 8 seed・smoke 2 seedを最終revision/26H2 tupleで全layout・両層・3候補について検証し、独立再監査・文書・runtime inventory・予算・native結果を一つの受入記録へ結ぶ | `formal_permission=false`、`S4_ACCEPTED=no`、`formal_ready=false` のまま。S5、S6、gate、promotionを開始しない |

正式holdoutの2,880評価成功やS6の実結果はS5/S6**後**に照合する証拠であり、S4開始前の循環した前提にしない。S4で求めるのは、登録入力を扱う固定経路、架空/正式dev/smokeによる契約検証、50,000 drawの資源測定と、結果の欠落や失敗を成功にしない証明である。[全工程予算台帳](results/anomaly-multiseed-v0.3-preformal-budget-evidence-ledger-2026-10-03.md)の未測定欄は数値0で埋めない。

## 更新・停止・再登録

- 一つのattemptの開始、各役割開始・終了、公開直前にOS tuple、Python/source、外部pinを照合する。親のruntime観測を子の実観測に代用しない。途中変化、未知のロード依存、未回収ownerはintegrity failureとして停止し、部分証拠を保全して成功receipt/完了印を作らない。
- attempt間でUBRのみ変わっても、`9457以上` のような範囲や自動追認を設けない。新しいexact tupleと影響範囲を版付きで記録し、対象native回帰、5役割profile、必要な独立再監査を済ませてから別attemptを許す。release/build/edition/architecture/FS/Python pinの変更は本v2候補の範囲外で、さらに別版を要する。
- S5開始後のproducer/analysis/audit間のruntime/source変更はformal campaign全体のintegrity failureとして扱う。残りのseedだけ、同じroot/seedの再試行、性能を見た条件変更、既存audit receiptの無条件再利用はしない。必要な再実行は、元証拠を保持し、別version/root/未使用seedを再登録する。

本案は採択済み条件、正式受入、S4完了、実保存holdoutの読み取り、50,000 drawを含む正式同形の全工程完走、S6監査を示す文書ではない。旧 `require_campaign_acceptance()` の無条件拒否、旧formal runtime pin、現行validatorの26H2拒否を保持する。採択判断には新版の実装・試験・独立監査を揃えた最終clean revisionを提示する。
