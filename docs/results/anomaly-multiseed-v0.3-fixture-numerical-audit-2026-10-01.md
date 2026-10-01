# 架空主集計の別実装検算と実行記録（2026-10-01）

前回の数値workerが保存した架空文書を、別の算術実装と所有audit processで検算した。9主表の117絶対推定・72対応差・180gateが一致し、新規22試験も成功した。[APIと範囲](../anomaly-v03-fixture-numerical-audit.md)、[現在の引継ぎ](../current-handoff.md)。

## 保存点と実装

開始revisionは `362cb7544879c2e044423c5a84b13f6c185ca2b3`、実装は `8bd4b67eac5ecaaa72fb139bc12a0bff484448b8`。新しい算術module・audit worker・各testの4本を追加した。旧66code/18dataは不変。clean候補は `C:/Users/TKent/.codex/worktrees/fa01/banto-ai`。元analysisのfw01と旧候補を保全した。

OUTは `artifacts/fixture-numerical-audit-2026-10-01`、成功試験と例は `tests-1/`、audit receiptはその `observed-audit/`。最終文書revision・全artifact/pin・資源はsavepoint-evidence.jsonとsave-checks.jsonを正とする。外部起点の前savepointは27575bytes/SHA-256 `5c0ff3a16f50589daf487a7f58a94a6acc85ae70625c32a97d5631d1c681f17d`。

## 何を別に計算したか

算術moduleは標準ライブラリのfractions/hashlib/json/mathだけをimportする。計算側が用いるdrawの頻度による重み付けと異なり、auditは各drawの40番号を順に展開して加算する。point・type-7 CI・同一drawによる候補差・null回数・profile/readiness・閾値・適格性/C1優先を導出する。effective exposureと検出済みdelayの和集合からの要約、packetと本文の主表対応も検算した。

入力は40個の架空clusterと4draw。元文書1,932,543bytes/SHA-256 `2c20d80e63bf53e662ee722ba48f723285cf08182178036a2410a78d6033c6b1` は変更せず、元のinput/document/result/evidenceの4ファイルを前savepointのpinで保持した。analysis workerや既存720評価は再実行していない。

検算対象は主集計である。slice/診断sidecarの導出、coverage/producer観測、正式登録データは対象外と明示した。別実装の小さい手例が一致したことを、文書全体の独立数値検証・正式S6・全依存受入へ読み替えない。

## 試験と保存例

| 項目 | 結果 |
| --- | --- |
| 新規試験 | 22 pass、failure/error/skip 0、27.521秒 |
| 内訳 | 算術/範囲13、owned audit/binding9 |
| 保存例全体 | 7.506秒 |
| 子監視時間 | 1.532秒 |
| 子PID・終了 | 42012、exit0、reaped、観測error0 |
| 成功要約 | 1185bytes、別に保持した期待pinと一致 |
| selected source / Python / 入力 | 13 / 2 / 5 files |
| 補助依存 | project30、全234files、179modules、native48、前後追加0 |
| 子peak private | 46.54MiB |
| 試験harness peak private | 76.08MiB |

成功要約のSHA-256は `6b78fea2e2863b99513cbf2e967a2ef70de99f0f5146d7762bbaf380c0696d1c`。audit evidenceは7784bytes、子stdout241346bytes、stderr0bytes。親が元Popen handleから得たPID・生成時刻と子自身の観測が一致した。親側の数値検算関数を禁止しても、実際の子auditが成功した。

手計算の比率/分位点/対応差、閾値等号と直外側、ゼロ分母の全draw保持、profile不成立、engineering readiness=falseを試験した。主表のpoint/CI/count/exposure/delay・候補選択・正式主張の改変を検出し、同じ値をpacket/本文の両方で改変しても拒否した。別々に求めたCI端点の差を対応差のCIとして代用した場合も拒否する。

owned childの実試験では、保持文書・analysis receiptを整合するよう再封印しても、主表のCI改変を数値不一致としてexit2で拒否した。role違い、外部referenceの取り違え、元入力pin不一致、未終了ownerと保存失敗、既存receiptの保全も確認した。停止supervisionは模擬応答で、新たな実メモリ枯渇/timeout負荷試験は行っていない。

## 資源・保全と残件

audit子には60秒/private256MiB/stdout+stderr合計1MiB、入力合計6MiB、最大8drawを適用。保存例後の空きRAM8.18GiB、commit余裕12.90GiB、C/D空き111.43/387.12GiB。OSは25H2/build26200/UBR9457。最終保存時の資源はsave-checks.json。旧formal pin9168を変更せず、資源推移だけからリーク原因を断定しない。

成功はstatus=verified、fixture_numerical_audit_performed=true。正式null4欄と元5payloadを保全し、元wrapperのaudit段階を遡って書き換えない。formal/promotion/independent_s6_complete/execution_authenticated/full closure=false。通常writer/reader・公開markerは起動/生成していない。

次は限定したfixture工程のdirectory総量・system commit余裕を含む停止条件を接続する。正式化には契約差分、登録入力のconsumer、slice/sidecar等を含む監査範囲、source/runtime受入、公開/全体予算が残る。新しい資源接続だけで正式gateを開かない。

新評価0、登録データ読込み0、既存評価再実行0。旧実計算c01d1c9、本流6f1285d、closed、dirty文書/CRLF差、旧候補/保存点を保全し、banto-24 PAUSEDを維持。principal/保護root/UAC/ACL、正式gate/freeze/holdout、push/mergeは対象外。
