# event-aware anomaly evaluation v0.2 結果

実施日: 2026-09-05
コードリビジョン: `15a0f60433703c32a1bfa989f7f779c6828a1096`

## 結論

v0.2 の正式 multi-seed replay と standalone analysis は完了した。engineering gate は matrix／analysis ともに `pass` だったが、performance gate は `fail` であり、baseline は昇格しない。今回の結果は event-aware anomaly baseline の評価であり、TimesFM3 の性能結果ではない。

結果は offline synthetic data のみで得た。顧客データ、ネットワーク、PLC／制御システム、Banto Hub への書き込み、checkpoint／weights は使用していない。

## 評価設定

- validation-only の robust residual profile
- robust z threshold `4`
- persistence `2`
- detection grace `3`
- 10 seeds × 12 layouts = 120 cells
- 1 seed あたり 48 events、10 seed clusters
- bootstrap resamples: 10,000

使用したコードリビジョンの CI は [run 33967921012](https://github.com/tyaro/banto-ai/actions/runs/33967921012) で Python 3.12／3.14 ともに成功した。これはコードの検証結果であり、artifact 自体を CI で生成したことを意味しない。

## 固定識別子

再現性のため、各入力と schema の canonical SHA-256、および bootstrap の固定識別子を記録する。

- matrix config: `3e206fc6c988850953d7ddd739a0504cb8cdd92f6726848b78ce4803461daa26`
- matrix config schema: `fbd081961bfd8a56f3ac24514310f0a17f89c02174db44bfeb3fb6b3911f1c4d`
- matrix result schema: `79acd31482bae6702dcb6bf6145a58342730a0b61c053592a720fa9e01e53326`
- analysis config: `33237908ea60cdfa55a311a2f46157884b9b3564c91e9d6d38218df9ebcc37ce`
- analysis config schema: `550fdde93e7bf25470872bc91f8516226cb843efcd3f42806d65a37f070cef03`
- analysis result schema: `00541b2770c8e682ef1b14d2e3dd354f404b6b3c796c2bbc3995a68913d841b8`
- bootstrap algorithm: `sha256-counter-rejection-v1`
- bootstrap seed: `20260905`
- bootstrap draw digest: `5b311c270aaef7bb942e0c4fbe761e8e225aaa0a1314a8bd2e70875f0fd46548`
- percentile method: `linear_interpolation_n_minus_1`

## artifact の検証結果

### matrix replay

- 120/120 cells success
- engineering: `pass`
- performance: `not_evaluated`
- result SHA-256: `7bc546936c1a99100204d7fe2852b9dd8c500ac0dd2e3c3d7ccbc139c918de31`
- summary SHA-256: `e132b3ea14e06be94b4df0cd4b052b1f270797744ca532fb333f1d0e94e289f9`
- completion marker SHA-256: `cc58b420901c9d31a415a89808d882c5b9a7d2936d0923e4102cee1acce85995`
- inventory: 1,443 files / 245 directories / reparse point なし
- inventory SHA-256: `2a4a62332c1c15c48b077aa59dbbccae01559558df162d5d1484aa1ae345af0e`

D1 erratum: 63桁の転記漏れを、実在庫のread-only再計算に基づき64桁へ訂正した。正式artifact bytesは不変。

v0.2 の summary SHA-256 が v0.1 と同じなのは、aggregate の human-readable summary bytes が同一だったためである。result／completion marker／inventory は別である。

### standalone analysis

- engineering: `pass`
- performance: `fail`
- overall status: `fail`
- result SHA-256: `b32d6f4ce5343322d660dd99e1fe4e63d4c81530ab94875630e721fdd42848dd`
- summary SHA-256: `9e1a04a1ac05ee71d44cf7ccfc233895ccf7ad106fa0a5ceab362a858b3cc755`
- completion marker SHA-256: `a4a7372122fa4614250fc6835b81a24f9af2d969319473be7d089a30f0dac0b7`

slice inventory は incident 34、precision 20、clean 20、signal × mode availability 48 である。独立 read-only audit では P0–P3 の指摘はなく、120 cells 全件を再検証し、bootstrap を再構成し、入力 artifact の不変性を確認した。

## promotion gates

5つの promotion gate はすべて fail した。95% CI は seed-cluster block bootstrap の percentile CI である。

| gate | 結果 |
| --- | --- |
| overall incident precision | `9/235 = 0.03829787234042553`（95% CI `[0.019455252918287938, 0.08928571428571429]`） |
| machine fault recall | `0/120 = 0.0`（95% CI `[0, 0]`） |
| sensor fault recall | `9/120 = 0.075`（95% CI `[0.041666666666666664, 0.10833333333333334]`） |
| clean false alerts / 8 equipment-hours | `222/10.8h × 8 = 164.44444444444443`（95% CI `[73.33333333333333, 280.0]`） |
| target signal availability ≥ 0.95 | `motor/conveyor: motor_temperature = 20460/21600 = 0.9472222222222222` で fail。他の6 target signalsは `20640/21600 = 0.9555555555555556`。 |

検知できた incident は 9件で、overall detection delay は mean／median ともに 0秒だった。これは machine fault recall が 0 であることを補わない。

## 判断と次工程

この baseline は昇格せず、比較用の失敗 baseline として固定する。v0.3 では別の preregistration として、mode-aware calibration または multivariate residual、machine fault sensitivity、false-alert reduction、data-quality dropout と availability gate の扱いを検討する。

TimesFM3 residual／scoring は別途 preregistered な後続候補であり、本結果と混同しない。

v0.1 の正式 artifact は summary integrity bypass のため `REJECT` evidence として保全しており、今回の v0.2 結果で書き換えていない。監査記録は [`anomaly-multiseed-v01-integrity-audit-2026-09-05.md`](anomaly-multiseed-v01-integrity-audit-2026-09-05.md) を参照。
