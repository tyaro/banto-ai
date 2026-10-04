# v0.3 架空 `inconclusive` 50,000 draw 算術検算（2026-10-05）

S4-2の算術境界を限定的に確認した。`budget.invented_clusters()` の40 clusterのうち control/core の1 cellを `inconclusive` にした架空入力を使用し、凍結bootstrap index 50,000行（SHA-256 `e375bf3feacb2f04bf5e1d40b141c1cfc5f69fa5437ea2704e323fd7523b22e5`）で主計算と別実装監査を実行した。`status=invented_primary_numerics_matched`。`inconclusive`を`calibrated`へ読み替えていない。

| 無視対象の保存raw (`artifacts/preformal-inconclusive-draw-probe-2026-10-05/`) | bytes | SHA-256 |
| --- | ---: | --- |
| `input.json` | 155,145 | `5bc8fd3a1fc6bac5e4b6678b0d39aef26ff35c08946b0dca243b313d357c9431` |
| `calculation.json` | 74,808 | `ecd692faec28119471a7d3973baceddaefbed76dd7e9a893eca54f4c0bd171f3` |
| `audit.json` | 566 | `9e1a123acb17499c5db9b4d5de3233d4f33db6cdce82dd1460d346a1a96dbcb4` |
| `receipt.json` | 1,561 | `8c0a3f599f96d33ebbee71e9e6017c1571a5c0ffb17ca62b461e0a0906751266` |

保存後の独立再読で4 rawのpin、監査から主計算へのhash結合、閉鎖flagを照合した。9表・主推定117件・対応差72件のうち、表2件、主CI 26件、対応CI 48件、gate 72件が `inconclusive` となり、その他のCIは主91件・対応24件で `complete` だった。保存を伴う再実行の所要時間はdraw生成4.38秒、主計算77.27秒、別監査180.47秒。関連統合57試験とrepository safetyはPASS。

これは発明40 clusterの算術検算で、共通campaign保存6行を40 clusterへ結んでいない。`artifacts/`はGit管理外であり、この試行はclean revisionのsource/runtime閉包や正式の単一全工程予算の証明ではない。`formal_permission=false`、`campaign_evaluations_credited=0`、S5未開放を維持する。次は新規架空campaignで厳密なreader source pin付き保存6行を同一wallで実測し、40 cluster入力までの系譜を接続する。
