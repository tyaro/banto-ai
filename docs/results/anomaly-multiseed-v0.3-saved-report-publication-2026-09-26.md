# 保存済みdev/smoke記述レポートへの解析・公開・別reader適用

2026-09-26 JST。[公開接続API](../anomaly-v03-analysis-publication.md)、[前工程の43試験](anomaly-multiseed-v0.3-analysis-publication-chain-2026-09-26.md)、[source/runtime計画](../anomaly-v03-consumer-source-runtime-plan.md)。

既存dev/smokeの保存済み記述レポートに、profile付きanalysis→通常公開→別observed readerを適用して成功。実装f8f20bcf4ac7ade2f20e96f37bc1567328d88a48のpc01と前工程の依存候補を再利用し、source変更・新checkout・新reference起動・試験suite再実行は0。前回43試験の合格記録はcode pin不変を確認して再利用した。

認証した原本7file/7,896,608bytesから4payload/2,755,533bytesを出力。旧published-successの4payloadと2marker、計6fileのbytes/pinが新公開と一致し、原本7fileと旧公開6fileも実行前後で不変。過去の120区間/720評価の記述結果を保存したもので、新評価/数値再計算は0。

analysis PID14244、writer PID22020、reader PID21668。両子ともexit0/reaped、観測error0。全体26.528秒、子の監視はanalysis 2.072秒、reader 2.077秒。analysisの依存234fileは保持候補と前後一致、readerの依存232fileは終了後disk/Git照合。全処理harnessのpeak private 69.38MiB、analysis子 54.05MiB、reader子 52.51MiB。保存準備時は空きRAM 10.81GiB、commit余裕 19.30GiB、C/D空き 133.19/345.92GiB。最終値はsave-checks.json。

## 外部の参照点

- 前工程manifest：29435bytes/SHAe25092c42073f9129615bdb8188789a0eb07933d70dc9faa2f97469b7fb71dd3。
- 元のreader保存点：10053bytes/SHA8e2a647c5539901ce1aa7c5b0924fc98e6b5ed435f1a8a0c9e7fe875d5d92b53。そのpin付きrequestから、保存済みbinding/report/analysis inputの明示pathと外部pinを取得した。
- binding保存点：7032bytes/SHA3d7d53fc00ad90de695d44e128d29c45467318da58e11b8ab3bf9d0571521305。
- report保存点：7932bytes/SHA79364b641f8f7a047298ca73d46fcdc49b1931c23394a043cb8802255392af39。
- 再利用したanalysis候補：111849bytes/SHAa7fea20d81c23455f395650531982d1c8e8fdd9a7989da15e386a7bd7a447b14。別の成功reference由来の候補を事前保持し、今回の返信から候補を採用/更新していない。

## 保存結果

OUTは`artifacts/saved-report-publication-2026-09-26`。`profiled-analysis/`に解析役割の準備証拠と4payload、`published/`に通常公開、`chain/`に公開結合と別reader証拠を保存した。原本のcleanupや既存attemptの再利用は行っていない。

公開marker SHA `97c8bc637328cb173e6c1a678765c7785512fb2ad7b66ed8af15939e819c874e`。内容が同一なので旧公開と同じdigestになる。markerは実行識別子ではなく、各実行のroot/PID/証拠を別のchain receiptで結び付ける。

最終chain result pinは1709bytes/SHAea8b5c8b1185d06de8ae93a2e620191e742214be123fc630b7cc73edc8fc0f0c。publication-binding pinは1828bytes/SHAca6fd667fd9104b23eebb9e42982eed21d7ccb9c4dbc3b529f197671b17bd5aa。この外部pinからanalysis result/profile/evidence、公開root/marker、reader result/evidenceへたどれる。

analysis側はsource13/Python2file・候補込み10入力、reader側はsource10/Python2file・15入力を親が保持した期待値へ結合。実行checkoutはclean pc01 `f8f20bcf4ac7ade2f20e96f37bc1567328d88a48`、757tracked files/8,567,147bytesのGit/raw一致を確認。新checkoutは作成していない。

## 検証範囲と次

実行したのは保存済みレポートへの一連の接続1件、子2processのみ。既存43試験を今回再実行したとは扱わない。元の観測・score ledger・登録holdoutを読まず、保存済み記述結果のbytesと参照関係を検査した。独立数値auditや正式文書provenanceを完了したものではない。

formal/promotion/S6/trust/execution_authenticated/full closure=false、document_draft.analysis_consumer=nullを維持。writer全processの実観測と完全な資源予算も未完了。旧62code/18data、実計算checkout/本流/closed、既存dirty文書とCRLF差は保全し、banto-24 PAUSED。OS26200.9457/CPython3.14.0を記録、旧正式pinやOS設定は変更していない。

次は受入残件表を現在の実装・保存結果に合わせて更新し、正式consumer/本文provenance、独立数値audit、writer実行証拠、完全資源予算の未充足を具体化する。既存720評価は再実行しない。 正式gate/holdout/正式freeze、保留principal/UAC/ACL、push/mergeは開始していない。最終文書revision・全artifact pin・資源と境界は最上位savepoint-evidence.json。
