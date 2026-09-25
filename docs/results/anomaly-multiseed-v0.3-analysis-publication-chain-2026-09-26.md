# 解析証拠から通常公開・別readerまでの接続

2026-09-26 JST。[API](../anomaly-v03-analysis-publication.md)、[source/runtime計画](../anomaly-v03-consumer-source-runtime-plan.md)。

実装f8f20bcf4ac7ade2f20e96f37bc1567328d88a48、OUT artifacts/analysis-publication-chain-2026-09-26。新module/test2本のみ追加し、既存analysis/profile/reader/collector/consumer/LocalPublicationを変更しない。外部result pinで選択したprofile付きanalysisの成功記録・4payloadを再認証し、保存原本との意味・bytes一致を確認して既存single-writer公開へ渡す。writerを閉じた後だけ、別のobserved readerを起動する。

公開物は従来どおり4payload。別directoryのpublication-binding.jsonが解析result/evidence/profile/binding pin、payload pin、公開root/marker、revisionと接続module pinを結ぶ。そのpinとreader result/evidence pinを最終chain resultへ保存し、呼出し側がresult_pinを保持する。公開marker単体は解析証拠の結合を証明しない。

全43試験pass（新14＋既存consumer16＋observed reader13）、failure/error/skip0、75.509秒。誤anchor・payload/evidence改変・reader role・未profile化・入力/出力重複・部分書き込み・writer応答喪失・reader失敗・結合記録改変・未終了ownerの保持を検査。正常時は二度目の公開を拒否し、元入力/公開物を保持する。

保存例reference PID11136→profile付きanalysis PID10040→通常writer PID39840→reader PID16652。全ての子はexit0/reaped。analysisはsource13/Python2file/10入力と依存234fileの事前候補一致、readerはsource10/Python2file/15入力と依存232fileの終了後照合。readerへanalysis候補は流用しない。4payload/5237bytes、marker SHA3837efdce90f6c7070ad0da8b1befa4c306ced1d6afcdebe2d976793e6fa997b。reader監視2.409秒。公開物/両analysis証拠/reader証拠/chain記録を保存し、架空原本だけtemp cleanup済み。

試験harness peak private 53.32MiB、保存例analysis child 37.66MiB、reader child 36.26MiB。資料作成前の空きRAM 10.13GiB、commit余裕 18.56GiB、C/D空き 133.21/345.91GiB。最終値はsave-checks.json。

pc01候補はclean f8f20bcf4ac7ade2f20e96f37bc1567328d88a48、757tracked files/8,567,147bytesのGit/raw一致。旧60code/18data pinとap01/旧候補、実計算checkout/本流/closed、既知CRLF差/既存dirty文書は不変、banto-24 PAUSED。新評価/数値再計算/登録データ読取/実bootstrap/正式gate/holdout/freeze/principal/UAC/ACL/push/mergeなし。

公開成功は架空engineering記述結果の通常公開で、正式文書や独立数値auditではない。formal/promotion/S6/trust/execution_authenticated/full closure=false、document_draft.analysis_consumer=nullを維持。接続moduleのGit/raw一致は確認したが、writer全processの実行証拠や全依存固定を完了したとは扱わない。次は、既存dev/smokeの保存済み記述レポートへこの一連の処理を適用し、外部anchor・解析証拠・公開marker・別reader結果を保存する。720評価は再実行せず、数値の正式受入やholdoutへ範囲を広げない。 正式consumer/文書provenance/独立数値audit/完全資源予算は残る。

## 失敗時と保存点

公開前の入力不一致は出力を作らず拒否。書き込みを開始して戻り値を得られない場合はpublication_status=unconfirmedとし、完了markerの有無を推測して削除・再公開しない。戻り値が得られた公開はcompleted。後続reader失敗時も公開物とpublication-bindingを保全し、全体のstatusはfailed。UnreapedWorkerはchain結果の保存に失敗しても元ownerを保って伝播する。

初回実装9e7b93eの局所確認でcanonical JSON比較にbytes/setを渡す箇所を見つけ、試験前に直接比較へ修正。試験と保存例はすべて上記最終実装で実行した。

前工程manifest25374bytes/SHAd68ceaeefcea0c669456052023346875d9f449a207663157404234a45541abccを起点に照合。今回追加2本を含む62code/18data pin、52件以上の保存artifact、文書revisionとboundaryは最上位savepoint-evidence.json。artifact件数/総bytesは最終inventoryを正とする。旧保存点は書き換えない。
