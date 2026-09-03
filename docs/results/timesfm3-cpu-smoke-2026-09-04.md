# TimesFM 3 CPU smoke結果（2026-09-04）

## 位置づけ

これは、TimesFM 3.0の推論経路と再現性を確認するための、単一の小規模synthetic windowによる正式CPU smoke記録です。cold processで2回測定していますが、実設備の代表性や一般的なモデル性能を示しません。製品採否、顧客PoC、本番shadow採用の根拠には使いません。

入力はcontext 64点、horizon 8点、2 target、past-only covariate、known-future covariateです。非線形の決定的な生成式を使い、held-out actualと比較しています。

## 正式CPU smoke実測値

| 項目 | Run 1 | Run 2 |
| --- | ---: | ---: |
| OS | Windows 11 | Windows 11 |
| Python | CPython 3.14 | CPython 3.14 |
| device | CPU | CPU |
| package | timesfm 3.0.0 | timesfm 3.0.0 |
| checkpoint revision | `43046b85ec22d584a13f8098c2ed39c889e129c2` | 同一 |
| context / horizon | 64 / 8 | 64 / 8 |
| target数 | 2 | 2 |
| elapsed | 4.726521799981128 s | 4.38183120000758 s |
| Peak RSS | 2,887,393,280 bytes | 2,887,266,304 bytes |
| model.safetensors SHA-256 | 一致 | 一致 |

elapsedの中央値は4.554176499994354 s、範囲は4.38183120000758～4.726521799981128 sです。Peak RSSの中央値は2,887,329,792 bytes、範囲は2,887,266,304～2,887,393,280 bytesです。中央値は2回の観測値の算術中央値として記載しています。

## 予測・指標の一致

2回のrunでinput fingerprint、predictions、metricsは完全一致しました。共通の集計値は次のとおりです。

| 指標 | TimesFM 3 | LastValue |
| --- | ---: | ---: |
| aggregate MAE | 0.6195372578526972 | 2.3322758318821113 |
| aggregate RMSE | 0.7602938833568439 | 2.3462443334359544 |
| mean p90-p10 width | 5.171777367591858 | — |

TimesFM 3とLastValueの絶対差は、MAEで1.7127385740294141、RMSEで1.5859504500791105です。改善率はMAEで0.7343636419913763、RMSEで0.6759528099771976です。これらは同一synthetic window内の比較値であり、外部データや実設備での改善を意味しません。

## Safetyと再現状態

2回ともartifact safetyは`offline_env_enforced=true`、`local_files_only=true`、`network_fallback=false`でした。checkpoint SHAは一致しています。`HF_HUB_OFFLINE=1`および`HF_HUB_DISABLE_TELEMETRY=1`をrun内部で強制し、呼出側環境に依存しないことを確認済みです。

出力artifactには、TimesFMのtarget別／aggregate MAE・RMSE・quantile幅、LastValueのtarget別／aggregate MAE・RMSE、両者の絶対差・改善率を記録しています。baseline値が0の場合、改善率は`inconclusive`として扱います。

これは単一synthetic windowかつcold processのsmokeであり、実設備の挙動を代表しません。性能採否、製品昇格、Phase 2完了を判断するものではありません。研究用途、non-production、read-only評価に限定し、Banto HubやPLCへのwriteは行いません。
