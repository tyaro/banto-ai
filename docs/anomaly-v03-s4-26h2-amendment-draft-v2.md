# v0.3 S4 運用改訂案 v2: 26H2・単一writer保証 A

2026-10-05追補: [受入範囲の整理案 v3](anomaly-v03-s4-acceptance-scope-draft-v3.md)で、凍結計画の必須条件と追加技術案を分けた。下記のメモリ内コード完全閉包などはv2時点の提案であり、自動的な採択済み条件ではない。v3も未採択で、正式gateは閉鎖中。

2026-10-04。状態: **採択前のreview draft**。これは[凍結計画 §8–9](anomaly-multiseed-evaluation-plan-v0.3.md#v03-runtime-acceptance)をまだ変更しない。[運用契約案 v2](anomaly-v03-formal-operations-contract-proposal-v2.md)と[先行改訂案 v1](anomaly-v03-s4-26h2-amendment-draft-v1.md)の選択肢を、実装・独立監査に渡せる条項へ整理したもの。旧formal入口の25H2検査と `s4_acceptance_not_frozen` は維持し、登録holdout観測はS4採択まで読まない。

比較基準のclean `51fdb5436a28115e5eeba1400187e3f0b18101d1` で、凍結計画のraw SHA-256は `e7c761f83d4657f39e1b5709fb022ad887a43f166327ff3258a36757d20eadec`、S1 registry raw SHA-256は `61af9100f8daa96d8200a0d2ab23aa7209cab52f0dd5543f9e35797de7332a70`。採択時は最終clean revisionで再pinし、scienceや既存registryをこの草案で書き換えない。

## 改訂の対象と保証差

| 現行の凍結条項 | この版で採択を提案する条項 | 未採択の間 |
| --- | --- | --- |
| §8の正式Windowsは25H2 / `10.0.26200.9168` / AMD64 / local NTFS | **別policy ID** `anomaly-v03-single-writer-research-v2`に限り、Windows 11 Pro 26H2 / `10.0.26300.9457` / AMD64 / local NTFSのexact tupleを使う | 旧tupleを新tupleへ暗黙に読み替えない |
| §8の公開後protected DACLと独立read-only tokenからのwrite/delete拒否 | **保証A**: 新rootの単一writerを所有し、そのexit/reap後に別readerを起動。全payload・marker・receiptの保存rawと意味をfresh readし、外側のverified receiptまで成功条件にする | 保証Aは別主体による同時write/deleteの防止を証明しない。DACLと独立tokenの受入をpassedと表示しない |
| §8のLinux image digestを含むrunner同定 | digestが取得できない場合の代替候補は後述のjob log・ImageVersion・release manifestの外部pin。digestそのものの取得とは区別する | 代替規則の計画採択・独立監査までは `runner_image_digest=not_collected` を不合格残件とする |
| §9のS4完了後にのみS5へ進む条件 | A1–A6とS4-1～S4-5の最終revision証拠を、別の独立受入記録で結合する | 旧gateの拒否を維持。部分試行・旧revisionの合算で受入にしない |

科学仕様とS1 registryの登録seed・layout・候補・分母・50,000 draw・180 gate・選択規則は変更しない。既存のengineering単一writer採択は正式保証Aの採択ではない。旧formal rootや過去attemptを新版のテストrootへ再利用せず、登録holdout seedはS4試験に使わない。凍結analysis schemaを科学検証に用いる場合も、旧運用条件の受入証拠へ流用しない。

## 正式policyとwrapperに固定する内容

専用root候補は `artifacts/anomaly-v03-formal-research-v2`。正式のattempt IDはroot作成より前に外部記録へ固定し、rootの不存在・実体path・local NTFSを確認する。新wrapperは凍結した `analysis.json` の科学schemaを変えず、`execution.json`、`coverage.json`、`analysis.json`、`diagnostics.json`、`verification.json` の5 payloadと、それらすべてを列挙する完了markerを持つ。別rootの独立audit、writer・readerの外側receiptを保持する。markerの自己hashを内部に埋めず、外部receiptでmarker raw pinを固定する。

`execution.json` はpolicy ID、wrapper版、attempt、計画・S1 registryのpin、全予定identity、producer/analysis/audit/writer/readerのclean full revisionと役割別source/runtime pin、外部入力pin、段階状態・失敗を明記する。`coverage.json` は480区間・960 dataset・2,880評価の予定と最新attempt、success/failed/not_startedを欠番なしで保持する。`verification.json` はreaderの別process・exit/reap、全保存pin・semantic検査、独立auditとの対応、未確認範囲を区別する。下記の純粋なschema候補は実装したが、実wrapper生成、完全source/runtime inventory、最終clean full SHAの外部固定は残る。候補validatorの通過だけで受入済みとしない。

2026-10-05の[未採択wrapper候補validator](../src/banto_ai/anomaly_v03_formal_research_v2_candidate.py)は、呼出し側が別途認証した外部raw pinと供給bytesについて、5 payload・marker、40 seed/480区間/2,880評価、主slice 1,233行・4系列sidecar 2,835行を検査する。同一revision・同一pathの5役割間byte衝突、各次元の集計とcore+quality-stress=overallのkey別不一致、主表とのrecall/availability/遅延count・mean・min・maxの矛盾を拒否する。[改変を含む12件の試験](../tests/test_anomaly_v03_formal_research_v2_candidate.py)がpassした。返却する正式許可・S4採択・評価creditは常にfalse/0。外部pinの真正性、process/Git/loader、元観測・50,000 draw・独立auditの再計算、primary delay median、event-offset対象外参照とquality依存の元ledgerはこの候補の検査外であり、正式wrapperと独立S4監査の残件である。

runtime照合は `EditionID=Professional`、`DisplayVersion=26H2`、build `26300`、UBR `9457`、kernel `10.0.26300`、AMD64、local NTFS、通常GILの64-bit CPython `3.14.0`、compiler `MSC v.1944`、source tag `v3.14.0:ebf955d` をexactに行う。`python.exe` raw SHA-256は `467014615a5255aca450ae88100dd2caf887da87657f00e3c2171ec44a685aec`、`python314.dll` は `f1722bd369d79fecbc85f3ed2790c30c330b9413fd74332f95b086e60dfacc2a`。開始・各役割の前中後・公開直前に実測を照合し、stdlib、拡張/DLL/CRT、外部program、動的load、in-memory codeの閉包も別証拠で固定する。UBRを範囲指定で許容しない。

sliceは[consumer I/O案 §4](anomaly-v03-consumer-io-proposal.md#4-保存物と正式schemaへの対応)の対応を採択候補とする。`analysis.slices`にはincident recallとscore availabilityを格納し、`diagnostics.json`にはincident recall、score availability、threshold exceedance、signal onsetの4系列を名前付きで保存する。incidentは48 cells/表、scoreは89 cells/表、全9表の本文は1,233行、sidecarは2,835行を予定在庫として検査する。scoreのunavailable行、event-offsetの重複参照と対象外参照、qualityのcurrent/previous依存、分母0のnullを保持する。補助sliceのCIは `not_evaluated`（分母0は `not_applicable`）で、新しいgateや有意差探索に使わない。主指標の50,000 drawと180 gateは省略しない。

## Linux runner同定の代替候補

GitHubは実jobのrunner imageとpreinstalled softwareを、[`Set up job` の `Runner Image` 表示](https://docs.github.com/en/actions/concepts/runners/github-hosted-runners)から調べるよう案内している。[runner-imagesの`main`一覧](https://github.com/actions/runner-images/blob/main/README.md)はimage配備の完了後に更新されるため、実jobの同定元にしない。以下は凍結§8のimage digest要件を改訂するための**代替候補**であり、最終revisionのUbuntu 24.04 x86_64 / CPython 3.12・3.14の実jobで満たすまで受入証拠ではない。

1. 外部受入記録は、3.12 test job、3.14 test job、共有fixture比較jobを**別々のrunner実行**として列挙する。[GitHubのrun/attempt定義](https://docs.github.com/en/actions/reference/workflows-and-actions/contexts)と[attempt別job API](https://docs.github.com/en/rest/actions/workflow-jobs)に従い、各jobのrepository、`run_id`、`run_attempt`、`job_id`、`head_sha`、job名、結論を取得して固定する。両test jobのjournalに含まれるsource revision、run ID、attempt、workflow raw SHA-256、Python patch/build、全pass/fail/skipおよび必須skip拒否を外部値と照合する。source revisionはcheckoutのclean full HEADと`GITHUB_SHA`にも一致させ、比較jobのfixture/journal検証結果のraw pinを結ぶ。異なるattemptのjobやartifactを黙って組み合わせない。
2. 各jobの[`Set up job`生log](https://docs.github.com/en/actions/how-tos/monitor-workflows/use-workflow-run-logs)をjob IDまたは[run/attempt別log API](https://docs.github.com/en/rest/actions/workflow-runs)から取得し、取得URL、raw bytes、SHA-256を外部pinに残す。logの`Image: ubuntu-24.04`、`Version`、`Included Software` URL、`Image Release` URLを照合し、両test jobではjournalの`ImageOS=ubuntu24`・`ImageVersion`がlogのimage/versionと一致することを要求する。比較jobも独立にlogからimage/versionを確定する。部分rerunのlog archiveは再実行されたjobだけを含むので、必要なjobそれぞれの実attemptを[GitHubの説明](https://docs.github.com/en/actions/how-tos/monitor-workflows/use-workflow-run-logs)どおり追跡する。
3. 各jobのlogが示す`actions/runner-images`のtagについて、[release by tag API](https://docs.github.com/en/rest/releases/releases)からrelease ID・tag・本文を取得し、同tagの`Ubuntu2404-Readme.md`のraw bytesと合わせて外部pinを作る。release本文と同tagのsoftware一覧にあるimage versionがlogのversionと一致することを確かめる。release本文・一覧・job logのいずれかが取得不能、URL/tag/versionが不一致、raw hashが不一致ならそのjobは不合格とする。例として[20260927.320のrelease](https://github.com/actions/runner-images/releases/tag/ubuntu24%2F20260927.320)はimage version `20260927.320.1` を表示するが、例のversionを将来jobの期待値に流用しない。

この規則はjobに表示されたimage版、GitHub公開のrelease記録、実行したPython/source/test結果の**由来照合**である。[GitHubが公開するrunner imageのSBOM](https://docs.github.com/en/actions/reference/security/secure-use)やrelease資産のdigestも、稼働したVM image全bytesのdigestではない。`runner_image_digest`を取得済みと表示せず、上記代替規則を版付き計画へ採択して独立再監査し、最終revisionの両test jobと比較jobの生証拠を取得するまでは `runner_image_digest=not_collected`、`S4_ACCEPTED=no`、`formal_permission=false` を維持する。現行CIのjournal検証器とworkflow結線だけでは外部log・release・実runnerの認証は成立しない。

## 失敗・再登録と独立受入

公開前後のsource/runtime・入力pin不一致、未知の依存、未回収process、reader/監査不一致、予算停止はattempt失敗として部分rootを保全する。markerだけでverifiedにしない。S5中のglobal integrity failureではcampaignを止め、同root/seed/attemptの都合よい再実行をしない。再実行が必要なら元証拠を保持し、別version/root/未使用seedを再登録する。

採択前の独立監査は、凍結計画・S1 registryのraw不変、旧formal入口の26H2拒否、保証Aで失うDACL保証の明示、exact tupleの陰性例、wrapperの全予定identity・attempt・slice/sidecar、外部pin対実ファイル、5役割前中後の閉包・exit/reap、単一外側予算と容量2倍、最終revisionのLinux両job・Windows native・正式dev 8/smoke 2 seedを確認する。[先行案のA1–A6](anomaly-v03-s4-26h2-amendment-draft-v1.md#保証-a-の受入項目と現在の証拠)に未了があれば `S4_ACCEPTED=no`、`formal_permission=false`、正式credit 0とする。2026-10-04の[算術→文書・slice連続予算](results/anomaly-multiseed-v0.3-five-role-job-and-contiguous-budget-2026-10-04.md)は部分成功であり、producer→登録保存reader→完全S6→writer→別readerの全工程を測ったものではない。
