# v0.2 exploratory failure diagnostics plan v0.1

これは、正式な v0.2 event-aware anomaly matrix の失敗要因を、後続 v0.3 preregistration の仮説材料として整理するための post-hoc exploratory contract である。promotion evidence、model／threshold の winner 選択、正式結果の再評価には使わない。

## D1 / D2-A の範囲

D1 は contract、固定 config、schema、config-only validator、`--validate-only` CLI とテストだけを提供する。120-cell artifact の診断実行、result／summary／marker の publish、既存 formal analyzer の変更は行わない。validate-only は filesystem に書き込まず、`run_status=not_run`、`performance_status=not_evaluated` と安全境界だけを返す。

D2-A は API-only の read-only 実装である。artifact revision の regular-file tree／raw bytes／mode、clean replay HEAD、入力成果物の marker／summary／inventory、formal analysis の既存 strict replay helper、台帳から独立再計算するprivate semantic checker、private draft builder、決定的 UTF-8/LF summary renderer を実装する。完成結果の公開入口は `replay_and_build_diagnostics_result` のみで、最終再検査後に発行する `VerifiedDiagnosticsResult` だけをrendererへ渡せる。D2-A は CLI 実行、formal run、publish、marker 作成、control／customer／Banto Hub write を行わない。D2-B でのみ実行・publish境界を別途設計する。

固定 config は [`examples/configs/anomaly-multiseed-failure-diagnostics-v0.1.json`](../examples/configs/anomaly-multiseed-failure-diagnostics-v0.1.json)、config schema は [`schemas/anomaly-multiseed-failure-diagnostics-config-v0.1.schema.json`](../schemas/anomaly-multiseed-failure-diagnostics-config-v0.1.schema.json)、将来 result shape は [`schemas/anomaly-multiseed-failure-diagnostics-result-v0.1.schema.json`](../schemas/anomaly-multiseed-failure-diagnostics-result-v0.1.schema.json) で固定する。diagnostics id は `anomaly-multiseed-v02-diagnostics-v01`、config identity と result identity はそれぞれ `event-aware-anomaly-failure-diagnostics-config` と `event-aware-anomaly-failure-diagnostics` とする。

## 入出力境界と固定来歴

- input: `artifacts/anomaly-multiseed-v02`
- output: `artifacts/anomaly-multiseed-v02-diagnostics-v01`
- input／output の同一、祖先子孫、traversal、absolute path、symlink／junction／reparse point は拒否する。
- expected matrix id: `anomaly-multiseed-v02`
- expected artifact code revision: `15a0f60433703c32a1bfa989f7f779c6828a1096`
- expected matrix aggregate: result `7bc546936c1a99100204d7fe2852b9dd8c500ac0dd2e3c3d7ccbc139c918de31`、summary `e132b3ea14e06be94b4df0cd4b052b1f270797744ca532fb333f1d0e94e289f9`、marker `cc58b420901c9d31a415a89808d882c5b9a7d2936d0923e4102cee1acce85995`、inventory `2a4a62332c1c15c48b077aa59dbbccae01559558df162d5d1484aa1ae345af0e`
- expected cardinality: 120 cells、10 seed clusters、seed あたり 12 layouts／48 events、event rows 480、eligible incident windows 240、pre-event support rows 240、detection-window point rows 1440、combined incident point rows 1680、score-availability source points 172800、availability cell×signal×mode group rows 5760（各 group 30 points）、calibration profile rows 5760、aggregate signal×mode groups 48、clean aggregate rows 94、incident window aggregate rows 16、incident offset aggregate rows 112、clean reconciliation rows 240、availability aggregate rows 48、calibration aggregate rows 48。固定式は `10*48=480`、`10*(48/2)=240`、`240*1=240`、`240*6=1440`、`240*7=1680`、`120*1440=172800`、`120*48=5760`、`120*48=5760`、`8*6=48`、`8+6+48+2+30=94`、`2+2+4+2+6=16`、`16*7=112`、`120*2=240`、`8*6=48`、`8*6=48` とし、各 aggregate signal×mode は `120*30=3600` points。これらは固定 structural cardinality であって診断結果の成否や性能 outcome を表さない。

正式 artifact は read-only で扱い、後続実装では before／after の input snapshot と source hash を一致確認する。出力は formal matrix／analysis root と共有せず、non-overwrite、strict schema、deterministic summary、marker last を必須にする。

D1 erratum: inventory SHA-256 の63桁の転記漏れを、実在庫のread-only再計算に基づき末尾 `e` を含む64桁へ訂正した。正式artifact bytesは不変。config/schemaの依存canonical/raw hashも再固定し、`.gitattributes` の `* text=auto eol=lf` でcheckoutのLFを固定する。既存checkoutを強制変換せず、正式確認は訂正commitのcleanなLF checkoutで行う。

`exploratory_only=true`、`promotion_eligible=false`、`performance_status=not_evaluated` を固定する。schema の `additionalProperties=false` により、promotion gates、代替 threshold 探索、winner 選択のフィールドは持たせない。

## 固定 ledger contract

1. incident window: event start sample を基準に offset `-1` を pre-event support、`0..5` を detection-window points とする。window の unique key は `cell_id, seed, layout_id, layout_index, event_id`、point の unique key は同じ window key と `offset` である。window row には event identity／`[start,end)` bounds／canonical `detected`／matched alert onset／delay／最大連続 exceedance／`pre_event_support`／`event_causal_support_qualified`、point row には timestamp、quality、actual／previous、residual、availability、exact exclusion reason、score、threshold exceedance、persistence streak、alert episode id を保存する。`event_id` は cell-local であり、canonical な検知結果は既存の `detected`、探索用の因果性補助判定は別フィールドとする。aggregate は Cartesian product ではなく marginal rows を出し、window は event_class 2、event_type 2、incident signal 4、equipment 2、operating mode 6 の計16 rows、offset は各 marginal の7 binsで計112 rowsとする。dimension identity は `dimension_name`／`dimension_value` を分離し、denominator は順に class/type 120、signal 60、equipment 120、mode 40。run distribution は run length 0..6 を全て持ち、window count の合計と一致させる。
2. causal support: `event_causal_support_qualified = detected is true AND matched alert onsetから persistence_points 個を sampling interval で後方追跡した全 support rows が available=true、exceeds=true、連続、同一 signal/mode/profile で、全 timestamp/offset が event_start 以降（offset>=0）`。undetected、unmatched、missing alert onset は false。canonical `detected` は変更せず、後続の in-window run で canonical onset を置換しない。
3. clean false alert: source alert episode の unique key は `cell_id + source_alert_episode_id`、equipment merged episode の unique key は `cell_id + equipment_episode_id` とする。aggregate は source alert episode を count unit とする signal 8、mode 6、signal×mode 48、mode-entry offset 0..29の30 rows、equipment merged episode を count unit とする equipment 2 rows、計94 rowsを固定 domainから各一度ずつ出す。signal×mode の dimension value は `{signal_id, operating_mode}` の object、mode-entry offset は source onset から containing generator regime start までの aligned integer sample offset 0..29とする。source rows に merged equipment count は混ぜず、equipment row の attribution rule は `equipment_episode_count=count of cell-local merged equipment episodes whose equipment_id equals dimension_value, each episode counted exactly once` とする。`[start,end)` interval と `source_alert_episode_ids` を突合し、`merge_size=len(source_alert_episode_ids)`、`source_count=sum(len(source_alert_episode_ids)) within each cell/equipment` を exact reconciliation する。reconciliation grain は cell×equipment の240 rows、source IDs は同一 cell/equipment 内で exact once、interval merge は canonical `[start,end)` replay とする。cross-cell join はしない。
4. availability: grain は cell × fully-qualified signal × mode で、canonical signal domain は `motor-01.motor_current`、`motor-01.motor_temperature`、`motor-01.conveyor_speed`、`motor-01.vibration_feature`、`conveyor-01.motor_current`、`conveyor-01.motor_temperature`、`conveyor-01.conveyor_speed`、`conveyor-01.vibration_feature`、mode domain は `stopped`、`startup`、`low_speed`、`nominal`、`high_load`、`cooldown`、equipment domain は `motor-01`、`conveyor-01` とする。equipment_id は signal_id の最初の dot より前の prefix と一致させ、各 cell は8×6 pairをexactly once（missing／duplicate／unknownなし）とする。各 group は30 sample points、aggregate/reconciliation は各 signal×mode について120×30=3600 pointsとする。available points、total points、exact exclusion reason counts を保存し、available points + exclusions = total points を要求する。quality dropout、mode boundary、gap、event overlap、profile inconclusive、その他を別 family とする。これは structural denominator であり性能 outcomeではない。
5. calibration: unique key は `cell_id, seed, layout_id, layout_index, equipment_id, signal_id, operating_mode`、5760 profile rows とする。availability と同じ canonical 8 signal×6 mode domain、equipment prefix rule、各 cell の8×6 pair exact-onceを適用する。point count、center、MAD、scale、status、excluded counts、reason を保存し、signal×mode の48 groupsごとに10 seed summaries、各 summary は layout index 0..11の12 profiles、group totalは120 profilesとする。numeric distribution は `total_count`、`non_null_count`、`null_count`、`min`、`max`、`mean` を持ち、合計整合を要求する。reason distribution は reason category（nullを含む）と count を保持し12 profilesに一致させる。profile `excluded_counts` は `event_overlap`、`nonfinite`、`quality_non_ok`、`residual_unavailable` の4 keysだけとする。現行 calibration は既に equipment×signal×operating_mode であり、単に mode 条件付きとは呼ばない。

## D2 semantic verifier contract

D2 の verifier は schema shape の検証に加え、composite key uniqueness、固定 structural counts、incident offset `-1=240`／`0..5=各240`、incident aggregate marginal coverage、clean aggregate 94 rowsの固定 domain exact-once、clean cell×equipment 240 rowsの source ID／merge／interval replay、availability 48 groupsの各30 pointsと aggregate/reconciliation各3600 points、`available+exclusions=total` の exact reconciliation、calibration 48 groups×10 seeds×12 layouts、availability/calibration の8×6 exact-cartesian coverage（unknown／missing／duplicate reject）、equipment prefix、seed values／layout inventory、canonical detection／causal support の整合を検証する。検証対象の source／artifact revision は D1 の safety boundary 内で read-only に扱い、D2 は formal exploratory run 前に freeze する。

incidentの各cellは、固定layoutごとにmachine_fault/jam_or_slipとsensor_fault/spikeを1件ずつ持つ。machine signalはmotorのmotor_current／conveyorのconveyor_speed、sensor signalは各equipmentのmotor_temperature。event IDは固定layout_idに `-machine-fault`／`-sensor-fault` を付けた値（low-speed/high-load表記を保持）へexact照合する。global category countとmarginal denominatorもclass/type=120、signal=60、equipment=120、mode=40を固定し、観測した件数で分母を再定義しない。canonical matchingはoffset -1の継続episodeを除外し、0..5にある最初の新規onsetからdetected/matched/onset/delayを独立再生する。後発episodeへの置換、検知の隠蔽、途切れたepisode IDの再出現を拒否する。

## 既存結果との扱い

現 v0.2 の 9 sensor detections は全件 pre-event exceed support である。diagnostics は正本の `detected` を変更せず、event-causal-support-qualified を別記する。この観測は read-only の exploratory observation であり、promotion evidence ではない。

availability gate では、mandatory dropout と mode boundary が同じ denominator に入り、現行の温度 signal は `0.94722` の ceiling に衝突する。v0.3 では core detection と data-quality stress を分離し、単純な threshold 緩和は行わない。

次の calibration 仮説は、既存の equipment×signal×operating_mode profile と区別して、phase、recipe-step、time-since-mode-entry、conditional-level、longer clean calibration、multivariate residual を別候補として preregister する。

## Revision safety

既存の `anomaly_matrix_analysis.py`、`anomaly_matrix_runner.py`、`anomaly_evaluation.py`、generator、formal config／schema は変更しない。revision compatibility は artifact revision `15a0f60433703c32a1bfa989f7f779c6828a1096` の `src/banto_ai`、`schemas`、`examples/configs` 配下にある全 regular file の同一 path bytes／git blob が current workspace と一致することを要求し、missing／modified／link／reparse は fail-closed とする。D2-A は artifact tree を capture してから読み取り、after snapshot と source／replay revision を再検査する。artifact revision と clean replay HEAD は分離し、`semantic_source_path` ごとの artifact blob SHA／current raw SHA と、current-only の5つの D2 digest を記録する。artifact revision tree は88 regular files、current workspace は fixed current-only 4 filesを加えた92 filesのexact setとする。D2 policy は code audit 後、formal exploratory run 前に freeze する。formal analyzer の current-HEAD 一致規則は緩めない。

## D2-A 検証範囲

単一API `replay_and_build_diagnostics_result(root, replay_head=...)` は固定schemaを内部でcaptureし、正式helperの結果とcapture済みbytesを一致確認してからprivate draftを組み立てる。draftは `status=draft`／`run_status=not_run`／`engineering_status=not_evaluated` であり、private semantic checkの成功はlive replayの証明ではない。凍結result schemaの検査用に内部で作る一時的なcomplete-shape projectionも公開・発行しない。構築・検証後にartifact全体、matrix sources、diagnostics/analysis configとschema、source treeとclean HEADを再確認し、成功後だけcomplete/passを付与してモジュール内sentinel付きで `VerifiedDiagnosticsResult` を発行する。呼出側によるschemaやcollectorの差し替え引数は設けない。

`VerifiedDiagnosticsResult` はread-only Mappingで、ネストした値も防御的コピーを返す。通常のconstructor呼出し・subclass・deserializeによる発行は認めない。`render_summary(result)` はこの型だけを受理し、任意Mapping、private draft、書き換えたcomplete Mapping、外部schemaを拒否する。D2-Bも内部でこの型をexact確認し、保存したMappingからは再replayなしに信頼済み型を復元しない。これは通常の公開APIの境界であり、同一process内の悪意あるreflection／monkeypatchingに対するsecurity sandboxとは主張しない。

専用テストは合成fixtureによる改変拒否、正式v0.2と同じfield shapeでの抽出、formal helperを明示的に代替した120-cell adapter、構築後の変更検知、write/network trapを検証する。これは実artifactの正式replay成功の証拠ではない。正式matrix/analysis suite、実artifactの診断実行・生成・publishは本変更では行わず、親側の固定commit確認に委ねる。

## D2-B: 固定出力の公開境界（正式診断run未実施）

D2-B publicationは当面Windows-onlyとする。Linuxを含む非Windowsでは、公開APIとCLI `--run` をfresh replay・path検査・staging／output claimより前に拒否する。エラーはWindows-onlyであることと、`--validate-only`／D2-A read-only replayは利用可能なことを示す。D2-Aの読み取り専用APIとvalidate-onlyにはこのplatform制限を適用しない。

公開APIと責務を次のように分ける。

- `validate_diagnostics_config(config_path=固定値, root=...)`: D1のread-only検査と従来のvalidate-only出力を維持し、replay／publishは呼ばない。
- `replay_and_build_diagnostics_result(root, replay_head=...)`: D2-Aのread-only API。sealed結果だけを返し、出力を確保・作成しない。
- `run_and_publish_diagnostics(root, replay_head=...)`: Windows-onlyのD2-B。明示した40桁lowercase clean HEADで新規replayし、公開後のpath／hash receiptだけを返す。result／schema／output／renderer／callback／recoverの引数は持たない。古いsealed objectを直接publishする公開APIはない。

両replay入口はprivate `_replay_and_build_with_context` を共有する。publisherだけがfreshなverified contextと最初のdraftから作ったcanonical payload bytesを保持する。private semantic checkerの成功はlive replayの証明ではない。rendererは今回auditした固定source bytesのhashを照合してcacheを使わず読み込み、callerによる差替えや古いimport／pycへ依存しない。

公開先は `artifacts/anomaly-multiseed-v02-diagnostics-v01` のみで、準備中はこの固定pathを作らない。親の `artifacts` は既存のregular directoryであることを要求する。既存targetはfile／directory／link／junction／reparse／markerlessを含めて全て拒否する。準備先は同じ親の `.anomaly-multiseed-v02-diagnostics-v01.staging-<UUID4の32桁lowerhex>`。このprefixの既存entryは残置物としてrun前に拒否する。新規stagingは一回のexclusive createで暫定予約し、guard取得後の非空directoryも拒否する。Windowsは `CreateDirectoryW` の作成時点で保護されたprivate DACLを指定し、Python 3.12／3.14のmode処理差に依存しない。各fileをexclusive createで書き、flush＋fsyncする。resultはsealed payloadのcanonical UTF-8 JSON（sorted keys、compact、末尾改行なし）、summaryはrendererのUTF-8/LF。

完了markerは固定type `event-aware-anomaly-failure-diagnostics-complete`、schema_version=`0.1`、result_sha256、summary_sha256のexactな4 fieldsを持つstrict canonical JSONとする。staging内に `result.json`、`summary.md`、`.complete` を準備し、bytes・identity・exact inventoryを検査する。`.complete.pending` は使用しない。stagingにmarkerがあっても「準備済み」であり、公開成功ではない。ファイルとdirectory inventoryをread-onlyに固定し、その後、入力artifact、diagnostics/analysis configとschema、matrix sources、revisionを再検査する。sealed payloadと初回draft bytesの再比較、出力再照合、strict marker検査、receipt計算もcommit前に終える。

唯一の最終commit点は、staging directory全体を固定公開先へ一回で移すatomic no-replace renameである。Windowsは保持したstaging directoryのDELETE-capable handleをsourceにし、[`SetFileInformationByHandle` / `FileRenameInfo`](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_rename_info)（class=3、ReplaceIfExists=FALSE、RootDirectory=NULL、固定absolute destination）を使う。準備中に別actorが固定公開先を作れば、空directoryやforeign markerの場合もoverwriteせず失敗する。非Windows platformはreplay／claim前、filesystemの未対応や競合はcommit前にfail-closedとし、overwrite fallbackはない。

Windowsのguardはrepository root／artifacts／自分のstagingだけで、上位のdrive root等はlockしない。repository rootとartifactsはwrite sharingを許可してdelete sharingを拒否し、無関係なsiblingのrename／writeを許す。stagingはwrite／delete sharingを拒否し、初めからDELETE／READ_CONTROL／WRITE_DAC権限を保持する。directory sharingだけではchildの追加や変更を防げないため、3 filesもidentity-bound handleでwrite／delete sharingを拒否してpinし、既に開かれたwriter／deleterがいれば失敗する。その状態で[`SetSecurityInfo`](https://learn.microsoft.com/en-us/windows/win32/api/aclapi/nf-aclapi-setsecurityinfo)により、3 filesは通常のwrite／deleteを、stagingはadd-child／delete-child／write／deleteを拒否するDACLへ固定する。変更対象はこの4つのheld objectsだけで、owner／groupやrepository／artifactsのACLは変更しない。初期staging DACLにもfreeze DACLにも継承ACEを設けず、既知3 filesはprotectedにする。直前に紛れ込んだ未知のsubtreeのアクセス権を剥がさないことも実機テストする。

Windowsでは子fileのhandleが開いたままだとdirectory renameが拒否されるため、最終検証後、freezeを維持したまま子handleを解放してからdirectory handleでcommitする。解放errorもcommit前の失敗とする。別processがこの直前にstagingの実pathを知っていても、通常のfile overwrite／replacement／rename／unlink／pending名やextra childの追加は拒否される。外部readerがrenameを妨げる場合も成功receiptを返さず残置する。ただしWindows ownerはWRITE_DACで意図的にfreezeを解除できる。特権・permission再変更・敵対的な同一userのあらゆる操作を隔離するsecurity sandboxとは主張しない。

旧Linux publisherの `renameat2(parent_fd, staging_name, parent_fd, fixed_name, RENAME_NOREPLACE)` 経路は削除した。source directory fdを保持しても、この呼出しはsourceを名前で再解決する。stagingを0500へchmodしても、名前のrename／置き換えは親artifactsのwrite／execute権限で可能なため、最終検証後に同一userがstagingを別名へ退避し、元の名前へ空directoryを作るだけで別objectが公開され得る。これは既存writerやpermission再変更を必要としない通常操作であり、chmodだけでは不十分である。将来のLinux publisherには、検証したsource identityそのものへcommitを結び付け、source-name swapを許さない設計と別process回帰テストが必要になる。その設計が成立するまでLinux公開は有効化しない。

成功時には固定公開先に3つのregular filesだけが同時に現れ、staging名は消える。成功後にはreadback／入力再検査／hash計算／削除／permission復旧を行わず、計算済みreceiptを返す。残りのhandle解放だけをbest-effortで行い、そのOS errorでcommit済み公開を失敗扱いにしない。consumerは固定公開先にあること、非link／非reparse regular fileのexact set、strict canonical markerのexact fields／type／version、result／summaryのraw SHA-256を必ず検証する。staging内のmarkerやreceiptだけで公開成功と判断しない。directory metadataの電源断耐性や特権actorによる公開後の変更防止は保証しない。

自動cleanup／recoverは全面的に行わない。claim前の失敗では自分の出力を作らず、claim後の失敗では空directoryやread-only状態も含めてstagingを残し、その名前とmanual inspectionが必要な旨を返す。競合相手の固定outputやmarkerも削除しない。公開先・staging prefixの残置物は次回も拒否する。作成成功とidentity／guard取得はatomicではなく、同一userによる空directory交換を確実には検出できないため、identityにかかわらずunlink／rmdirは行わない。出力は成功時もread-onlyであり、手動の撤去には内容と対象を確認したうえでownerによるDACL／modeの復旧が必要になる。ツールに復旧オプションはなく、テスト用一時ディレクトリの権限復旧・削除はfixture teardownだけで行う。

CLIは `--validate-only` と `--run` を明示的に排他とし、runはfull `--replay-head` 必須。seed／layout／limit／output／recover／schema overrideは設けない。run成功時だけpublished pathとresult／summary／markerのSHA-256を表示し、失敗は非zeroで簡潔に返す。D2-Bの実装確認は合成fixture・一時ディレクトリ・mockのみであり、正式artifactの診断run/build/publishはまだ実施していない。network、customer、control、Banto Hub、既存formal処理／config／schemaは変更しない。
