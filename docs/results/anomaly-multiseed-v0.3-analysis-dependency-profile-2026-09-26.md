# analysis専用の事前保持依存候補への接続

2026-09-26 JST。[API](../anomaly-v03-analysis-evidence.md)、[source/runtime計画](../anomaly-v03-consumer-source-runtime-plan.md)。

実装140e91de93e2cc43c45fab9efb9a7cbc6ece43c7、OUT artifacts/analysis-dependency-profile-2026-09-26。analysis専用のprepare_profileを追加し、別の成功した未profile化referenceと外部result pinから新規候補を保存する。format/role/operation/採取境界を固定し、reader候補の流用を拒否する。後続analysisは親が起動前から保持した候補のraw bytes/pinと依存集合へ前後一致を要求する。

全43試験pass（新規20＋既存analysis15＋reader候補の純粋検査8）、failure/error/skip0、145.715秒。誤pin、file hash改変、module欠落、子の再封印、保存copy差し替え、reference payload改変、候補の自動更新を拒否。source13/Python2file、候補を含む10入力を証拠へ結ぶ。依存source30/全234file/179modules/48images、47,606,116bytesが前後一致した。

保存例reference PID24184→後続PID8184は別process、双方exit0/reaped。後続監視2.123秒。候補111843bytes/SHA6502078885a3f42c7a356f0057a23f45ad24c384719380980cc4c4b0302b78ab。4payload/5237bytesはreferenceと後続で一致。原本の架空入力はcleanup済み、両実行のpayload/期待値/観測/監視と候補を保持する。試験harnessのpeak private 52.97MiB、保存例childのpeak 37.61MiB。資料作成前の空きRAM 9.77GiB、commit余裕 17.74GiB、C/D空き 125.89/346.17GiB。最終値はsave-checks.json。

ap01候補はclean 140e91de93e2cc43c45fab9efb9a7cbc6ece43c7、754tracked files/8,535,094bytesのGit/raw一致を検査。旧ao01/rp01/rd01、実計算checkout/本流/closed、元70b0の既知CRLF差と既存dirty文書を保全。banto-24 PAUSED。数値再計算・新評価・登録データ読取・実bootstrap・正式gate/holdout/freeze・principal/UAC/ACL・push/mergeなし。

candidate-not-acceptedであり、正式source/runtime固定やmemory codeの証明ではない。analysisの対象は保存済み記述結果の認証・準備だけ。numerical_analysis_performed/published/formal/promotion/S6/trust/execution_authenticated/full closure=false、document_draft.analysis_consumer=nullを維持。次は、照合済みの4payloadを既存のsingle-writer公開処理へ接続し、writer終了後の別readerまでを小さな架空入力で通す。公開時に解析証拠と保持pinを結合し、数値再計算や正式採択へ範囲を広げない。 正式consumer/文書provenance/独立数値audit/完全資源予算は残る。

## 資源と保存

検査前後のresource実値はstart.json、verified-stats.json、save-checks.jsonに保存。子の上限30秒/private512MiB/監視output1MiB、依存候補512KiB、依存file最大512・合計256MiBを維持。元の評価上限やOS設定は変更しない。候補checkoutの追加量は約8.1MiB、記録の最終総量はsavepoint-evidence.jsonのartifact inventoryから確認できる。

前工程manifestは21155bytes/SHA5a539a6d5c9f1479fd357d7867a7f61c46d0c0fdc9d761f0136cfe22bcc57f5b。旧58code pinのうち意図したanalysis実装/試験2本を更新、新module/test2本を追加し、残り56codeと18dataは一致を確認。reader/collector/consumer本体は変更していない。最終文書保存revision、60code/18data pin、境界、artifact全件pinは最上位savepoint-evidence.json。

この検査の依存一覧は別実行の観測を基準化した候補であり、正しい依存集合を独立に証明したものではない。disk bytesと実行中のmemory code、既存cache候補と実使用bytecodeは区別する。OS更新後は実値を記録し、旧候補を置換せず別候補で確認する。旧正式pinは維持する。
