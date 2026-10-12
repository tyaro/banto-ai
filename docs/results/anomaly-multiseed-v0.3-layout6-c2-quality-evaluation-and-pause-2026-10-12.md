# layout6 C2 quality実評価と一時停止（2026-10-12）

人の「つぎで一時停止します」に従い、このC2 quality 1cellを最後のunitとして実評価を終了した。原証拠・この2文書のGit保存後にheartbeat banto-10をPAUSEDへ更新する。実更新結果と保持した設定の照合はFINAL/automation-pause-check.jsonを優先する。人の明示再開まで追加自走・新モデル/試験/CI追跡/追加agentを開始しない。停止を正式受入完了や性能合格へしない。automationのpromptへ詳細結果やPC内pathは転記しない。

## 実評価

同chunk006/seed2486912926863618161/layout6 quality C2、新IDdev-layout6-quality-c2-20261012/manifest5422/75698B/input10→新snapshot→fresh fit/calibration→原結果。元生成C0/実評価C2は別field。元payload書込み生成replayproduction-test変更追加agent0。文書checkout043bf4259f6cc7497c64807b5c9e2b088d59a2ac/計算661b不変/Python3.14.0 Windows AMD64/elapsed34.14200270001311秒/privatepeak207802368B。
機械0/10・sensor9/10・precision9/19・clean0・未対応10全machine窓vibration-only。48calibrated/fit600/cal290/C2state48/14400scores/13796available604不能null-thresholdfalse。primaryphase471/current30/previous10/peer93、非排他的phase480/peer120/current30nonfinite30previous30は重複非合算。missing30/mask18000対応、phase-current重複9・phase-peer重複27を保持。core比利用可能減124、C1quality比減93。480+40-9+120-27=604は原rowsを分類した照合で、未観測予定数ではない。
source28/equipment19/events40/incidents20、sensor9target/support2/onset1秒、検出9delay全1秒/未検出11null補完forbidden。burden10/20原value50.0とclean0別保持。machine10原targetspeed窓score<6/streak0/onsetなし、candidate1 vibration-only/support2/onset1秒→first_candidate_no_target_onset/causalfalse。唯一sensorcycle09start8841score167.2104246166733/1→8842–44current欠測/8845previousreset→8846score1.8034797920242138/0・8847score1.2986798354525788/0、candidate0/no_candidate_in_window/causalfalse/delaynull。8850phaseは対象窓外。全対象窓phase0。
peer3target各40非排他的=120、うちphase重複各9=27、primary各31=93。全不能null/thresholdfalse/streak0。sensor9equipment原current+temperatureの2source各9、machinevibration10、C1source19対C2source28をtarget検出9と別保持。原20incident/全episodes/全machine10 target70rows-vib20support/9sensor/品質reset/window/missing30/peer120/重複を保存。GT/threshold6/persistence2/matching/science変更0、実入力対応保存状態分類の不具合観測なし。
同coreC2・同qualityC1・旧layout0–5qualityC2はmanifest/configだけ9比較、旧8本文再展開再compute0、declared16candidate/compiledconfig一致。同qualityinput10一致/core品質差・別layout差保持。同seed7layoutと同条件比較で9独立seed-dataset0。旧36board/core3候補維持、layout6qualityC0は未実施、全比較未完了、bootstrap/statisticalCI/勝者採択0。

## 保存済み比較

| layout | stratum | candidate | machine | sensor | precision | clean | available/unavailable |
| ---: | --- | --- | --- | --- | --- | ---: | --- |
| 6 | core | c2-phase-conditional | 0/10 | 10/10 | 10/20 | 0 | 13920/480 |
| 6 | quality-stress | c1-phase-level | 0/10 | 9/10 | 9/19 | 0 | 13889/511 |
| 5 | quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 13760/640 |
| 4 | quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 13760/640 |
| 3 | quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 13760/640 |
| 2 | quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 13796/604 |
| 1 | quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 13760/640 |
| 0 | quality-stress | c2-phase-conditional | 4/10 | 9/10 | 13/19 | 0 | 13760/640 |
| 6 | quality-stress | c2-phase-conditional | 0/10 | 9/10 | 9/19 | 0 | 13796/604 |

## 唯一sensor未検出の原target窓

| sample | score | available | primary | streak |
| ---: | ---: | --- | --- | ---: |
| 8839 | 0.6261271339085038 | True | None | 0 |
| 8840 | 0.06059578380180556 | True | None | 0 |
| 8841 | 167.2104246166733 | True | None | 1 |
| 8842 | None | False | current_target_quality | 0 |
| 8843 | None | False | current_target_quality | 0 |
| 8844 | None | False | current_target_quality | 0 |
| 8845 | None | False | previous_target_quality_or_nonfinite | 0 |
| 8846 | 1.8034797920242138 | True | None | 0 |
| 8847 | 1.2986798354525788 | True | None | 0 |
| 8848 | 1.1125728230300715 | True | None | 0 |
| 8849 | 0.8186914619519514 | True | None | 0 |
| 8850 | None | False | mode_recipe_or_phase | 0 |

## 入力と結果のpin

入力manifest: C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\006\attempt-0001\result\payload\manifest.json

dataset: anomaly-v03-dev-seed-2486912926863618161-layout-06-quality-stress

| 原保存 | bytes | SHA256 |
| --- | ---: | --- |
| observations | 9600508 | 7fbb3b5e7f74e65677a557c875fe3b0b180138012a682834294f1e5dd8ae6a64 |
| configuration | 5518 | be800e88c6aecba2f11fba3ed86e708a605190f2b5e88c849e201fb9d4597c82 |
| manifest | 8055 | 4735a59dec342116968af1497ed663a9cb4a4e625fad3aa2127f1b64ea43382c |
| evaluation | 25174439 | 285c3b57ee26f03a24d4dc252dbb9b50571f932687bc23e1c4254c5e8b066a1f |
| numerical | 25168841 | 1b22845689c040affc15ab568f230cbda196a4e00251658ea3ed04553ef4a616 |
| machine/sensor proof | 118992 | 473dbe4204709f87b27744361f8d36168751f4978b89a88c64e08d631ff66b24 |
| quality/overlap proof | 55413 | 7ac7c7612b05fb6826b3d7974779f3b92849326b65ba70322149f9657d9b08b3 |
| peer proof | 72644 | 513875baa72f64e002bcb6248c2beaf2bb7b0e170fef4898ab7a71398d1b245a |

## 保存範囲と上限

MAIN representative-layout6-quality-c2-20261012-prep、POST representative-layout6-quality-c2-post-20261012-prep、FINAL representative-layout6-quality-c2-final-save-20261012-prep/post-save.json・owners-after-save.json・automation-pause-check.json・root-closed.jsonを最終保存参照とする。DATA {'files': 19, 'bytes': 38222088, 'manifest_pin': {'bytes': 2264, 'sha256': '9b73a9b4c67c77756ed3cd4818e6aa22a0a6aa55792f91ce3e90ef38802e3c3e'}}、EXTRACT {'bytes': 349709, 'files': 10, 'manifest_pin': {'bytes': 1461, 'sha256': 'a98e61ea7a32c7b50cbbbfaad30b39ac82b54d34466e2c54f361e7fbf74c561b'}}閉鎖。117science・旧171root count-byte-closurepin・frozen35容量false・C2cache補足を保持。前C1文書準備foreground0/最終inspection KeyError1は原FINALへ別保存、元helper11failedを書換えない。今回docs準備時foreground0、元191helpers11failed180passed/fullidentity一致/CIM同original不在/repositoryhelper0。foreground fullcreation/fullstdioNone、selectedCLIを全process logへしない。PID単独/native回収claim0。
metadata512KiB32entry/reserve128KiB/single128KiB/recursive/Python-B、script・失敗・閉鎖を含め新書込み前容量確認。docs/proofはPOST初保存、owner/停止設定/最終metadataはFINAL初保存。閉鎖/外部固定root追記・raw整理移動削除・上限緩和0。
同種合成dev結果・ユーザー名PC入力path・同GitHub送信先と今後の同種報告のリスク通知後、人の「進めてください」による継続承認範囲でhandoff/report2を https://github.com/tyaro/banto-ai.git へ直接一回[skip ci] commit/push。原返値・HEAD/upstream/GitHub ref/clean/docpinsはPOSTに保存。Git512KiB16entry/stdout1MiB/累積30秒/preflight別量。
CI381385/4130保存維持、CIquery/download/verifier/doc-only追跡0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了/create_native早期拒否/全7役reader禁止/元caps-unknown原owner-stop/追加agent禁止。engineering900秒2GiB/output1GiB/single32MiB/files32はcheckpointで、blocking中断/full runtime/native/global容量証明ではない。処理successを性能合格/採択へしない。
