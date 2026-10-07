# v0.3 worker source callback／stop fence CIの保存照合（2026-10-07）

正式許可false・正式credit0・登録holdout観測未読。CIは各外部HEADに限定した証拠で、後続revisionのnativeや最終S4受入を代用しない。

| CI / 外部HEAD | 3.12 job / 3.14 job / compare job | 各minor件数 | index bytes / SHA-256 |
|---|---|---:|---|
| 37576149693 / `e4cb23aeff8501ab91cfdcf34d804612f856352f` | 112645385920 / 112645386128 / 112656640376 | 3144 | 2783 / `cfdb36fe2b651278ad8b00d35c6a79095f5fb146a762f030b9abaa2c072c0e71` |
| 37578543252 / `01ab74fe479ddfeb46ca781ebbd3db1ccb93c84c` | 112652777551 / 112652777298 / 112663769019 | 3157 | 2783 / `72ce93345566e5c74439debb921165d5e8cfd2778d088a81efb1576c1ea43ed6` |

両runはattempt1・push・全3job success。各minor fail0/error0/skip237/source不変。run/attempt jobs、2journal、comparison/regression、3job logとlocal regressionの10 rawを専用 `artifacts/ci-diagnostic-<run>/` へ保存し、local/remote全回帰一致、共有29fixture/必須28試験を確認。workflow Git blob SHA-256 `1376641c6a394b2f4781bb0ceaa8acfa735f35dfa1799d8503300ba9268815e8` と各外部fullHEAD/run/attempt/job idを固定、各indexは14 raw/control pinを保持する。

runner v2は両方consistent_candidate。37576149693は全job20260927.320.1、37578543252は3.12/compare20261004.327.1・3.14が20260927.320.1。保存済み公式release/README metadata/Git blobとminor journal/logを照合し、20261004版の外部prerelease=trueも一致。VM digest未取得・候補未採択。

追加の選択local CLI/source7 file照合では、`tools/ci_windows_native_skip_ids.py` のworking raw24604 BとGit raw24598 BにCRLF6箇所の差があった。初回all-raw-equalを要求したsidecar照合の失敗は37576149693 rootに保全した。Python sourceのCRLF→LFだけでGit bytesへ一致することを限定確認し、raw一致へ読み替えず両raw pinとrelationを `verifier-source-pins.json` へ明記した。他の選択6 fileはworking/Git raw一致。新しい数値試験/local回帰の再実行は0、この追加source照合は実ロード閉包ではない。

| source sidecar | bytes | SHA-256 |
|---|---:|---|
| 37576149693/verifier-source-pins.json | 2311 | `ae5aa7dd85a6de53388bf2f70b9864b996de6a0d2a10d5ee8366c8e7347b6a02` |
| 37578543252/verifier-source-pins.json | 2311 | `f9a53511457754c5de5b763d5bc2d6f076becb0144b83ddd16226df0b97cbfe7` |

保存後checkerは各14 raw pinと選択CLIのworking pin、channel更新のscience/source11 pin、clean HEAD/origin、doc-only差分を照合する。未保存CIは37581339092（HEADaaca57c、各minor3178予定）と37583002436（HEADe5ff975、各minor3191予定）。doc-only新CI追跡は増やさない。正式受入5残件と実データengineering範囲は変更しない。
