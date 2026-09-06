# event-aware anomaly multi-seed evaluation v0.3 S1監査結果

- 監査日: 2026-09-06
- S1基準: `0b40e7295cfa20f32889005ceca2d29d29ca340c`
- S1初回監査対象: `0368769acf12a0279c84f30c6435e853208386e9`
- S1修正・再監査対象: `d6ca0f9ee85172caae3b658bdb105287f8e43141`
- 科学仕様revision: `4b02201f95e8ffa3a243be716872d95815a554bd`
- 科学計画: [v0.3実装前preregistration](../anomaly-multiseed-evaluation-plan-v0.3.md)
- S0監査: [v0.3計画監査結果](anomaly-multiseed-v0.3-plan-audit-2026-09-06.md)

## 結論

初回S1実装`0368769acf12a0279c84f30c6435e853208386e9`の独立監査は
`P0=0`、`P1=0`、`P2=6`、`P3=1`だった。修正commit
`d6ca0f9ee85172caae3b658bdb105287f8e43141`を再監査し、7件すべての解消を確認した。
修正後判定は`P0=0`、`P1=0`、`P2=0`、`P3=0`で、S1を完了・採択する。
candidate stackはmainへ未統合であり、S2は未着手である。

| 判定 | 結果 | この判定が示す範囲 |
| --- | --- | --- |
| CONTRACT_CORRECT | yes | 凍結S0に対するS1 config、schema、pure validatorの宣言・相互整合 |
| SCHEMAS_STRICT | yes | v0.3のclosed shape、typed ordered literal、full-string ID/hash、result roleの分離 |
| PURE_VALIDATOR | yes | caller-supplied value／bytesだけを扱い、I/O・score・bootstrap metric・性能判定を実行しない境界 |
| TESTS_ADEQUATE | yes | S1契約と既知の監査反例をS2開始前に検出する保存試験の範囲 |
| LEGACY_PROVENANCE_PRESERVED | yes | v0.2の旧88 semantic Git blobsと固定provenanceを変更せず、S1の17 pathsをexact current-onlyに隔離した範囲 |
| S1_READY | yes | S1文書・config・schema・pure semantic validator・registry・testsのsavepointとして完了 |
| INTEGRATION_READY | yes | candidate stackをmain統合レビューへ送れる状態。main統合済み、実験可能、製品利用可能という意味ではない |
| S2_START_READY | yes | S2 scorer／matching実装を開始できる契約入力が固定済み。S2の実装・合格を意味しない |

この監査はS1契約実装の監査であり、dataset生成、profile fitting、scoring、episode形成、
matching候補の完全列挙、bootstrap metric／CI再計算、runner、formal artifact、性能、promotion、
ACL／native publicationを検証したものではない。`yes`をrun成功や性能達成へ読み替えない。

## 監査対象inventory

S1の科学入力は5 configs、契約は9 schemas、pure実装は3 modulesである。

| 区分 | path |
| --- | --- |
| config | `examples/configs/synthetic-anomaly-v0.3.json` |
| config | `examples/configs/anomaly-candidates-v0.3.json` |
| config | `examples/configs/anomaly-multiseed-v0.3.json` |
| config | `examples/configs/anomaly-multiseed-analysis-v0.3.json` |
| registry | `examples/configs/anomaly-v03-freeze-registry.json` |
| schema | `schemas/synthetic-anomaly-config-v0.3.schema.json` |
| schema | `schemas/anomaly-candidates-config-v0.3.schema.json` |
| schema | `schemas/anomaly-multiseed-matrix-config-v0.3.schema.json` |
| schema | `schemas/anomaly-multiseed-analysis-config-v0.3.schema.json` |
| schema | `schemas/anomaly-v03-freeze-registry.schema.json` |
| schema | `schemas/anomaly-evaluation-result-v0.3.schema.json` |
| schema | `schemas/anomaly-multiseed-matrix-result-v0.3.schema.json` |
| schema | `schemas/anomaly-multiseed-analysis-result-v0.3.schema.json` |
| schema | `schemas/anomaly-multiseed-audit-result-v0.3.schema.json` |
| module | `src/banto_ai/_anomaly_v03_contract.py` |
| module | `src/banto_ai/_anomaly_v03_schema.py` |
| module | `src/banto_ai/anomaly_v03.py` |

freeze registryは自己hashを内部へ入れず、13 leaf（先頭4 configs＋9 schemas）のraw／canonical
SHA-256を固定する。registry自体はpure moduleの外部定数でpinし、循環を作らない。

| 固定対象 | SHA-256 |
| --- | --- |
| seed-list canonical | `fa072f5299132fc22cce471c94ca189ddfc0f3acd27c2c5201bc31a2a9287505` |
| bootstrap 2,000,000 accepted indices raw | `e375bf3feacb2f04bf5e1d40b141c1cfc5f69fa5437ea2704e323fd7523b22e5` |
| freeze registry raw | `61af9100f8daa96d8200a0d2ab23aa7209cab52f0dd5543f9e35797de7332a70` |
| freeze registry canonical | `2d6fb5072c9e15e0efdbcc35488fb148a8b6911bbe84c616e071e2ecab9205a3` |
| science-plan raw | `8eef3a6dc094e9d48a321fe526e85c75e6876caf6023730c005381da4e762bc5` |
| post-audit-status-plan raw | `15e97cfa798618d6822664fc13e53a05279633dde1b0514fc52f6367d073e0c1` |

全50新seed、role順、counter、旧10 seed除外、replicate 0／1／24,999／49,999の
各40 golden indices、全accepted-index streamを再照合した。科学計画、5 configsの科学値、
seed／bootstrap算法・golden、圧縮plan snapshotは修正で変更されていない。

## 初回7指摘と解消根拠

| 初回指摘 | 修正後の契約・保存試験 |
| --- | --- |
| P2-1 ordered literalがschema shapeだけで、split／bootstrapの順序・重複を許す | 全4 splitとbootstrap object全体をtyped ordered equalityで照合。reverse／degenerate split、反復index、重複replicate、逆interval／draw、bool indexを拒否 |
| P2-2 analysisのcomplete／pass／qualified／selection宣言が疎 | 3候補×core／quality-stress／overall、各8 full-target availability、全180 required absolute／paired gates、固定母数、raw-count arithmetic、overall加算、CI状態・bounds・null count、profile状態、qualification、C1優先を照合。C1のみ、C2のみ、両方、no-promotion、inconclusive、C0 zero-alert precisionも保存試験化 |
| P2-3 delay集計とproducer／analysis／auditのsource識別が不足 | closed `delay_summary`にcount／median／mean／min／max、`causal-detected-only`、miss-zero-fill禁止を固定。producer、analysis consumer、input analysis、audit consumerを別descriptorとし、caller-supplied revision→source bytesのinventory／length／raw hashをpure照合 |
| P2-4 regexがsearch＋`$`依存で末尾改行を許す | v0.3専用schema traversalと`re.fullmatch`でSHA-256、full 40 commit、strict IDの全体一致を検査。historical共通validatorは変更しない |
| P2-5 incidentのreported candidateがevent equipment／半開窓に拘束されない | 全reported candidateについて同一dataset／equipmentと`event_start <= onset < window_end`を照合。候補の完全列挙はS2へ残す |
| P2-6 source episodeとscoreのbacklinkが片方向 | onsetの第2 support scoreからsourceへの参照と、reported interval member scoreから正しいsourceへの参照をdataset／candidate／equipment／target／mode／recipe／profile／timeで照合。onset前の第1 supportには参照を強制しない |
| P3-1 seed／bootstrap rejection境界の保存coverageがない | bootstrapの`T-1`受理、`T`／`2^256-1`拒否、counter増加、次positionのcounter 0 reset、seedのsmall／旧seed／新seed衝突retryを保存 |

初回`0368769...`へ最初の14監査testsを適用した実測は22 subtest failuresで、P2の抜けを
再現した。typed bool indexは初回実装でも拒否されていた。またP3の2境界testsは初回実装でも
通過し、算法不具合ではなく未保存だったcoverageの指摘だった。この例外を修正前failとは扱わない。

analysis validatorが確認するのは**報告値同士と凍結閾値の整合**である。raw observationsから
profile、score、episode、CIを再計算せず、bootstrap replicateを生成してperformanceを確定しない。
source bytes照合も、callerがfull revisionから取得したとするbytesとの一致だけであり、Git真正性、
完全なsource inventory、実行されたcode、analysisの独立性を証明しない。これらはS2〜S6のI/O／監査境界で行う。

## test・独立監査結果

| 検証 | 結果 | 境界 |
| --- | --- | --- |
| S1 contract／audit repair tests | 65 tests、全pass、26.699秒 | v0.3 pure contractと監査反例。実runなし |
| S1＋legacy revision関連 | 79 tests、全pass、44.395秒 | 上記65＋D2／legacy保全14 |
| repository全suite | 551 tests、549 pass、2 skip、0 failure／error、765.786秒 | Windows CPython 3.14.0 |
| 修正後独立監査 | 68/68 checks pass | code／schema／config／test／docs／境界のread-only確認 |
| in-memory compile | 98 Python sources pass | bytecodeを生成しない構文確認 |
| repository safety | pass | 登録済み安全境界 |

全suiteの2 skipは既存のローカルToto artifactがない場合だけの条件付き検査である。

- `test_controlled_artifacts_are_verified_when_available`: `artifacts/toto2/ctl`不在
- `test_event_slice_local_artifacts_are_checked_when_present`: `source_matrix`、`event_result`、`generated_summary`不在

Python 3.12はローカルに存在せず未実行である。Linux CPython 3.12／3.14、Windows native
publisher／DACL／AccessCheckおよびv0.3 formal runtime acceptanceは未実施である。

## v0.2 legacy provenanceの保全

v0.2 failure diagnosticsのartifact revision
`15a0f60433703c32a1bfa989f7f779c6828a1096`に属する旧88 semantic Git blobs／modesは不変である。
既存4 current-onlyにS1新規3 modules／9 schemas／5 configsのexact 17 pathsを加え、合計21 pathsを
明示allowlistにした。wildcardやprefix単位の許可は追加していない。独立fixtureは旧88のexact
path／mode／raw hash集合を保持し、extra、missing、historicalとのoverlap、mode／link／raw改変、
同件数での差替えを拒否する。

過去のformal artifacts、formal result文書、`FORMAL_RAW_PINS`、artifact revision、D2 identity、
output root、ACL契約は変更していない。current-only保守により現行diagnostics module／config／schemaの
hashは更新されたが、この新moduleでv0.2 formal runを再実行したとは扱わない。

Windows作業copyの旧88 pathsには既存のCRLF差が68件あり、Git LF blobsとの差はすべて改行だけだった。
これらは書き換えていない。runtimeのworking bytes exact検査も緩めていないため、この作業copyを
formal replay可能またはnative受入済みと読み替えない。保存fixtureのGit LF照合と実機formal replayは別である。

## 残る工程と利用境界

S1完了後も次は未実施である。

- S2のgenerator／scorer／profile／source episode／equipment episode／matching実装と境界fixture
- S3以降のmaterializer／matrix runner／analysis／independent audit、実seedでのdataset生成
- bootstrap metric／CIの実計算、formal artifacts、ACL／native publication、性能判定、候補選択、promotion
- Linux CPython 3.12／3.14、Windows native publisher／DACL／AccessCheckの正式受入
- mainへのcandidate stack統合

S1は研究契約を実装・固定したsavepointである。製品利用、PLC／control write、Banto Hub write、
顧客データ利用、model採用、性能保証を許可しない。現在状態の入口は[文書索引](../README.md)、
[研究roadmap](../research-roadmap.md)、再現手順は[evaluator README](../../tools/evaluator/README.md)を参照する。

## 統合後のliving status

本監査resultのS1実装・docs stackは、`3e7474ee7e9e25dc462e2e8daa3c4e7d6d77b09f`でmainへ統合済みである。
GitHub Actions [Phase 1 CI run 34013082980](https://github.com/tyaro/banto-ai/actions/runs/34013082980)はsuccessで、
Python 3.12 jobは7m56s、Python 3.14 jobは7m25sだった。両jobでcompile、unittest、manifests＋naive smoke、
synthetic generation＋quality、benchmark、safetyがpassした。

これはS1のCI／統合確認であり、v0.3 formal run、性能評価、promotion、Linux正式受入、Windows native／DACL／AccessCheck
受入を実施したことを意味しない。S2以降は未着手である。凍結計画と過去formal result本文の歴史的状態は遡及修正していない。
