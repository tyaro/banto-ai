# CARE数値入力と実consumerの支持確認

2026-10-16 JST。計画と固定契約CARE-A-MAINT-20261016-r1に沿って、保全・点検支援向けのFarm A 22ファイル・3信号の数値入力とquality maskを準備した。数量・時点・入力とラベルの境界、固定した窓数と記録時間の支持条件はすべて通過した。これは学習前の入力準備の完了であり、異常検知性能や製品採用の判定ではない。

[具体計画](../research/timesfm-inspired-practical-evaluation-plan-2026-10-16.md)・[固定契約](../research/care-a-maintenance-contract-2026-10-16.md)・[原本確認](care-metadata-contract-2026-10-16.md)を引き継ぐ。開始前の仮説、数値規則、実行範囲、旧文書bytesは[phase記録](../../artifacts/care-numeric-phase-20261016-evidence/phase-before-numeric-read.json)と[最終EvidenceStore](../../artifacts/care-numeric-final-20261016-evidence/root-closed.json)に保存した。対象差替え、追加信号、条件緩和はない。

## 数値入力とquality mask

原本ZIPの全体SHA256と22 CSVのmember SHA256を再照合し、選択3列だけを数値解釈した。1,196,747行、3,590,241値をファイル別32byte little-endian recordへ変換した。内訳はint64のファイル内時刻offset、int64の原row ID、3信号のfinite mask、3byte padding、float32三つである。22 binaryとmanifest/closureの計24ファイル、binary総量38,295,904B、root全体38,356,619B。manifestは原本・契約・member・binaryのhash、信号順序、prefix境界を保持する。

| 信号 | 有限値 | 観測ゼロ | 空欄・NaN・無限値・float32 overflow |
| --- | ---: | ---: | ---: |
| sensor_13_avg | 1,196,747 | 0 | 0 |
| sensor_12_avg | 1,196,747 | 0 | 0 |
| power_30_avg | 1,196,747 | 170 | 0 |

実データのmaskは全行0b111。電力ゼロ170点は有効な観測値として保持し、休業/正常/故障のtruthにはしない。変換器には空欄、NaN、無限値、float32 overflowをcanonical NaN/mask falseへ分ける経路があり、ゼロ・負ゼロ・underflow・不正tokenを含む人工8ケースで確認した。補間・ゼロ補完・clamp・行削除はない。温度の原unit文字列「�C」と電力の匿名scaleを持つ来歴を維持し、数値変換単位の補正はしない。

[数値manifest](../../artifacts/care-numeric-input-20261016/dataset-manifest.json)・[quality集計と原token probe](../../artifacts/care-numeric-preparation-20261016/quality.json)・[converter](../../tools/public-data/care_numeric_prepare.py)。原本v6/DOI/CC BY-SA 4.0、帰属・変更内容・license URLを派生manifestへ記録した。Rustコードや学習済みmodelのlicenseをここで一律認定しない。

## 実consumerの時点とラベル境界

[care_input.py](../../models/mini-transformer/care_input.py)はfoldとroleを固定して読み込み、forwardに渡すPastContextを3×128の過去数量だけに限定する。発行時刻は最後の過去点の記録時刻+600秒。現在温度は独立したThermalObservationとして自身の記録時刻+600秒以降に利用する。現在/未来の値や欠測を変えても発行入力は変わらず、現在値が欠測なら後の残差評価だけを利用不能にする。gapの後は過去128連続点の復帰を待つ。

status0は5 anchorのtrain prefixだけをLSB-first base64 bitsetとしてmanifestに保持する。prefixのfit/選択/校正用の後処理注記であり、数値tensorのチャネルではない。predictionのstatusは保存せず、推論・警報のgateに使わない。train_test、asset ID、event IDもtensor特徴量に入らない。

実consumerで13境界確認を通過し、実数量のcontext [8,3,128]と分離した学習target [8,3,32]のbatch組立・有限値を確認した。model forward/backward/optimizerは実行していない。未来値の非参照はrow access計測でも確認し、現在値の早期利用、testからの学習target取得、foldを跨ぐfile取得、prefixを越える学習target、truth field注入を拒否した。

入力プロセスのaudit hookはlabel/evaluator fileのopenを拒否した（明示的な拒否probe、label bytes読取り0）。別プロセスのevaluatorが、閉鎖済み入力支持とeligibilityのhashを先に保存してから、既に監査済みのevent metadataを支持率計算だけに使った。このrole分離は正規consumerの論理境界であり、任意の悪意あるPythonコードのOS sandboxを認定するものではない。metadataは既読なので正式unknown holdoutとは呼ばない。

初回確認後に、準備manifestの各file情報と固定入力manifestの全field照合、binary path/layout/hash、clock原点、fold範囲の検査を強めた。旧成功root/sourceは保持し、新rootで再確認した。新旧のinput-support/eligibility bytesは完全一致し、先に閉じたevaluatorの支持結果は同じ入力bytesに適用される。[独立検証](../../artifacts/care-input-independent-20261016/support-equivalence.json)には、asset/行数/clock/path/重複file/truth注入/不正foldの9拒否も保存した。

## 固定した支持条件

| asset | anchor event | fit origins | 選択 origins | 校正 origins |
| --- | ---: | ---: | ---: | ---: |
| A:0 | 0 | 44,775 | 1,017 | 12,348 |
| A:10 | 3 | 38,824 | 817 | 12,794 |
| A:11 | 25 | 48,025 | 1,020 | 15,431 |
| A:13 | 14 | 47,603 | 1,002 | 15,561 |
| A:21 | 13 | 38,664 | 746 | 14,873 |

各anchorの下限fit4,096・選択256・校正512を全件通過した。数量finiteによる追加除外はなく、既存のstatus/時点だけの支持値と一致する。fit/選択は160点全3信号・status0・600秒連続、校正は過去128点全3信号と現在温度2信号・status0を条件とする。

22 prediction区間の固定分母は50,593行。過去だけで発行可能な入力は47,851点、現在温度とcadenceを含む共通評価支持は47,834点。各fileの支持床70%を全22件通過し、最低はevent22の892/1,148=77.7003%。一方、lagged powerと現在温度だけで利用可能なbaseline native支持は50,560点で、共通支持より2,726点多い。128点warmup/gap復帰によるbaselineの可用性優位を隠さず、後の性能評価でも別に報告する。

labelを扱う支持preflightでは、異常12区間がすべて70%以上・非空を満たし、最小はevent84の824/1,005=81.9900%。正常asset別の共通支持記録時間はA:0=839.167h、A:10=971.167h、A:11=1,131.667h、A:13=707.500h、A:21=597.167hで、24hの床を全5assetが通過した。匿名fileを跨いだunique物理equipment-hourとはせず、各利用可能recordの[availability, availability+600s)を合計した時間である。

[入力支持](../../artifacts/care-consumer-check-provenance-20261016/input-support.json)・[区間と正常時間の支持](../../artifacts/care-evaluator-support-20261016/event-and-normal-support.json)。この支持成立から、負荷binのpair数、校正閾値、検知性能の成立までは推定しない。

## 独立検算と実行記録

全1,196,747 recordのlayout、padding、maskと有限値の対応を読戻し、prefix-sumを再利用しない逐次run-length法で全fileの共通/native支持と5 anchorのfit/選択/校正数を検算した。原tokenからnative C float32への変換286点をbinary bytesと照合し、すべて一致した。固定JSONは開始前bytesと不変。新旧closed rootsは書換えない。

| 実行 | 親観測秒 | sampled footprint B | child peak RSS B | exit |
| --- | ---: | ---: | ---: | ---: |
| care-numeric-input | 11.457 | 22,331,920 | 30,998,528 | 0 |
| care-consumer-check | 9.721 | 185,811,760 | 240,435,200 | 0 |
| care-consumer-check-provenance | 6.066 | 183,255,832 | 239,697,920 | 0 |
| care-evaluator-support | 0.614 | 54,460,968 | 66,781,184 | 0 |
| care-input-independent | 1.877 | 29,360,656 | 41,844,736 | 0 |

全unitが親900秒/子870秒、Mac physical footprint/peak RSS各2GiB以内。consumer自身のcheckpointでの最大footprintは186,975,024B、wrapperの最大child peak RSSは240,435,200B。資源上限はサンプリング/自己観測でありOS hard capではない。stdio/exit/source/phase/quality/支持/closureを各fresh rootへ保存した。学習stateは生成しておらず、実行stateと入力closureを保存した。

データ/集計rootはartifact上限内。初回phase snapshotはartifact Files形式で、名前にevidenceを含むがEvidenceStore形式ではなかったため、元rootを残して最終EvidenceStoreへ同じbytesを256KiB以下のpartとして再保存した。最終EvidenceStoreは16MiB/512fileとfailure reserve2MiB/16fileを維持する。

Mac Python3.14.8の共通入力経路とMac資源観測はpass。Windows native機能およびOS依存包括test suiteは未実行。Xcode license警告が変換wrapper起動時に一度表示されたが、入力処理と資源観測はexit0で終了し、license/設定/依存を変更していない。

## 次の工程

数値入力と時点/role/窓支持の準備は完了した。次は同じtrain anchorから一度ずつの尺度/MADと負荷binのpair支持を固定し、全foldのbatch scheduleを保存してから、固定5foldの有限CARE実学習へ接続する。今回CAREの学習・model forward・予測・閾値校正・性能採点は0で、固定JSONのcan_launch_learning/predictions=falseを変更していない。metadata監査や同じ境界人工確認を目的なく反復しない。

最優先用途は保全・点検支援（異常の予兆）。最終目的は学習も含めたRustの前処理/forward/backward/optimizer/checkpoint-resume/警報stateとbanto API/job/model管理である。32byte recordとquality maskはその共通参照だが、Rust実装の成立は未検証。需要の2015再評価停止、2014以前だけの調整、同休業mean28、四季平均の過小量/過大量非増加と観測のみ・欠測0仮定の分離、heartbeat PAUSEDを維持する。今回、新取得・外部研究data送信・Git push・本番採用・追加agentはない。
