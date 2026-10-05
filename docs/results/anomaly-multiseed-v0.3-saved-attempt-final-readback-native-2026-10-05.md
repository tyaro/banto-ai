# v0.3 保存attemptの終了時照合（2026-10-05）

code保存点 `2d4e378a957f87690a2b908aa1272d1067a9710e`。正式gateは `s4_acceptance_not_frozen`、`formal_permission=false`、credit0、登録holdout40は未読。追加agentなし。

## 修正と確認範囲

[保存reader入口](../../src/banto_ai/anomaly_v03_preformal_saved_row_reread.py)はfresh owned childで保存観測→profile・score→ledger・primary・sliceを再計算する。従来の終了境界はmanifest、旧outer result、invocation、選択source/runtimeの確認までだった。今回は6行の保存後、最初の外部pinのまま最新attemptの22ファイルを固定pathで再読し、保存行もpinで読み戻す。各ファイルの前に生存中budgetを確認し、1ファイルずつ解放する。旧attemptへの代替、payload変更、保存行変更、停止済みbudgetを拒否する。

これは終了時の選択byte照合で、外部root全体のinventory保証や照合後の不変性保証ではない。再照合ではscoreを再計算しない。旧fixture・純粋な系譜出力のfalse flagは変更しない。結果には終了時照合の完了／予算内実行を別項目として記録する。失敗時は既に保存した行・終了receiptを残し、成功扱いしない。

[焦点試験](../../tests/test_anomaly_v03_preformal_saved_row_reread.py)13件がpass（1.012秒）。小さな22実ファイルを使い、latest attempt2、変更・欠損・stopを確認した。既存coverage／保存行系譜15件も別runでpass（2.264秒）。repository safety・diff checkがpass。凍結計画68,889 B／`e7c761f83d4657f39e1b5709fb022ad887a43f166327ff3258a36757d20eadec`、registry10,679 B／`61af9100f8daa96d8200a0d2ab23aa7209cab52f0dd5543f9e35797de7332a70`は不変。

## Windows native

既存の架空g02を保持し、新root `artifacts/anomaly-v03-preformal-saved-row-reread-20261005-final01` で実行した。入力生成revisionは `3be274c59ce4ffa0b5b60ba42993e2aa44a57039`。生成済み22ファイル131,144,119 Bを読み直したもので、今回producerは起動していない。登録seedのidentityはschema markerのみであり、実登録campaignを読んだ証拠ではない。

| 測定 | 保存値 |
| --- | --- |
| reader→6行→22ファイル／保存行再照合 | 54.576292499987176秒／120秒、sample242、passed、sampler終了確認 |
| owned reader | PID2956、50.507041800010484秒、exit0、元handle由来のcreation tokenとchild echo一致、回収確認 |
| reader private最大 | 315,301,888 B／1,073,741,824 B |
| parent private最大 | 49,827,840 B／536,870,912 B |
| 新root標本最大 | 202,997 B／33,554,432 B、7／256 entries、最終receipt用65,536 Bの予約を維持 |
| commit余裕／RAM／disk最小 | 13,556,551,680／11,824,402,432／384,717,070,336 B |
| 選択source/runtime | 15 sourceの前後・disk/Git一致、26H2/build26300/UBR9457・CPython3.14.0一致 |

最新attempt1はcomplete、6評価のoutcomeはすべて正当な `inconclusive`。fresh reader全値は外部pinを固定した旧reader結果と一致し、131,144,119 B／22ファイルと116,085 Bの保存行を終了時に再照合した。外部保存payloadは新rootのdirectory予算外だが、読取り時間・parent資源・全体の空きはこの時計で測定する。samplerは協調停止でありhard quotaではない。

reader予算の終了後、10 control rawを既存consumerへ接続した。coverageは1/480区間・6/2,880評価、seed contributionは1/12 layoutで `cluster_contribution=null`。40 clusterの4入力への変換は `complete ordered saved-row inventory required` で拒否した。後段consumer確認はreaderの120秒予算に含めない。他の479区間を補完したり、6行を40 clusterへ複製したりしていない。

stdlibだけの別保存checkerは、22 physical file、外部manifest/outer、rows、invocation/stdout/supervision、後段partial/rejection、15 sourceのdisk/Gitを計53 raw pinで再照合した。これは保存記録の照合で、checkerによる独立score再導出や独立S6ではない。

## 外部pinと保存物

input manifestは `artifacts/anomaly-v03-preformal-generated-pinsets-g02/pins.json` 72,149 B／`22ee6888d731c827162b09ef1332cb61fe6a5542372e3e499ea0088fd214f1ef`。旧outerは `artifacts/anomaly-v03-preformal-registered-attempt-g02/owned-generator/result.json` 10,528 B／`354c8ae043486c8f5ee2a99780ea5ee5a9395ed92daaca790187e8e9ab7c1179`。

次表のnative pathは上記新rootからの相対名。helper pathは `artifacts/anomaly-v03-saved-attempt-final-readback-20261005-a1/` からの相対名。rawはGit管理外のローカル証拠で、文書pushはrawの転送を意味しない。

| 保存物 | bytes | SHA-256 |
| --- | ---: | --- |
| native `result.json` | 9,221 | `0c7dbd95f520111cb192dec878730e8170310685403b9ccf30aafa13bb5c8f16` |
| native `resource-budget.json` | 1,707 | `441ff793ad85180d720286e4d72781f09af12888fcfe9f2fa2108ec0877d71be` |
| native `rows.json` | 116,085 | `134dc17e98dd5ef3ac24431e463436cbcc73a4f869b5262a5428d998d45d66d9` |
| native `owned-reader/supervision.json` | 2,203 | `010a86491c45b402ad6aa4e6c6d9644a886248956fc64835cdb0276d7d4f1c80` |
| native `owned-reader/invocation.json` | 71,855 | `18fd1ea2458bc778265669a2b31e94f8e4d29d5e59eaf43055e3744681cf5695` |
| native `owned-reader/worker/report.json` | 12,854 | `66b3ac764ad06bf6d6e99bf42d9d110a92cb22df92dd4dc9ba47cfd286c1f545` |
| helper `request.json` | 449 | `8c776bd611b4c8ff6c40d0be1167146b2a4532aad4cef0f4605b76b1d332480d` |
| helper `run.py` | 5,558 | `38d431f48a3df54271d3f82b11ebbe61848030e44f7f3c9d466e101713b87d4d` |
| helper `capacity-preflight.json` | 200 | `bec9fd3a73bfc6c63cc1fcb24a344a88a985f35fcac98e244109555362720dbd` |
| helper `execution.json` | 1,190 | `6af362b0c69e1f06cb60a0b9113f3448a16409c4ac9e11da8f2a15fc0d2bdce3` |
| helper `coverage.json` | 3,452 | `34a00e8ed9a7c26ecc416051475eb7191994c1f9136648923e447f9cd755f986` |
| helper `seed-partial.json` | 2,044 | `40f260facc2f98d31bb184a5b4ba2ae5caf8533c29097114c17969686e20bbe4` |
| helper `partial-projection-rejection.json` | 92 | `d158e3730589678115bc1afc5c349e0d3996a94a806abfbf09819cfb6d7ecec9` |
| helper `postcheck.py` | 8,388 | `f8bd0a1d09fac552145a354ea9fb9fd1dcf36678daeb739c7894d248c4deb1c8` |
| helper `postcheck.json` | 11,881 | `b4591d01d0876e01a476549452ed1f5bad0e492a9185835290495785fda4ef00` |

## 残る受入事項

観測再導出は今回の架空1区間について確認した。実producer／保存形式readerから全分母・slice・4入力・50,000 draw・writer/fresh readerへの接続、共通外側予算、smokeに基づく正式同形容量2倍は未了。[受入範囲案v3](../anomaly-v03-s4-acceptance-scope-draft-v3.md)の契約採択、最終source/runtime全在庫、正式dev8/smoke2・両OS・独立受入も残る。先行control-onlyの[280.645秒の証拠](anomaly-multiseed-v0.3-saved-control-budget-native-2026-10-05.md)とは別試行で、両者を連続した全工程実測へ読み替えない。
