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


## channel code aaca57cのCI追補

CI37581339092 / 外部HEAD `aaca57c9749fa4970919e2596f6a884b6851d2b5` / attempt1は全3job success。3.12 job112661473486、3.14 job112661473791、compare112674385868。各minor3178件・fail0/error0/skip237/source不変、共有29/必須28。専用 `artifacts/ci-diagnostic-37581339092/` に10 raw、local/remote全回帰一致、runner v2 consistent_candidate、14 pin indexを保存した。index2783 B / `d817666b4ca96baabbb4f6b3ee333c28c90e2a85c3f8773b774a75e2ace7f399`。

3.12/compareは20260927.320.1、3.14は20261004.327.1。保存公式release/README metadata/Git blob・log/journalと照合し、後者prerelease=trueも一致。digest未取得・候補未採択。選択CLI7 sourceは外部HEAD固定、skip一覧1fileだけCRLF→LF差を両raw pinで明記し他6 raw一致。source sidecar2311 B / `37e396bc9213a44b8ca2e864e786ff3324a41b636f0fc2c3de3d0c4e75dfc1d9`。数値/native replay0、後続codeの合格へ読み替えない。


## atomic channel code e5ff975のCI追補

CI37583002436 / 外部HEAD `e5ff97567a62764048576ce10606ce72bb6ab684` / attempt1は全3job success。3.12 job112666729426、3.14 job112666729643、compare112680362863。各minor3191件・fail0/error0/skip237/source不変、共有29/必須28。専用 `artifacts/ci-diagnostic-37583002436/` に10 raw、local/remote全回帰一致、runner v2 consistent_candidate、14 pin indexを保存した。index2783 B / `604389f2c14c42650dfe46cfec933b8515bb4c5274192954411f8e032deecff4`。

全job20260927.320.1。保存公式release/README metadata/Git blob・log/journalを照合、digest未取得・候補未採択。選択CLI7 sourceは外部HEAD固定、skip一覧1fileだけCRLF→LF差を両raw pinで明記し他6 raw一致。source sidecar2311 B / `41e3dce76e4785f929ad1218d5970a5a0372da9772543267e79a9504c0d56667`。後続revisionのnative/最終受入へ読み替えない。


## post-close code3016448のCI追補

CI37585092575 / 外部HEAD `301644854a9e4db7d6915ffda6c9bf8278be54dd` / attempt1は全3job success。3.12 job112673293155、3.14 job112673293337、compare112687473898。各minor3207件・fail0/error0/skip237/source不変、共有29/必須28。専用 `artifacts/ci-diagnostic-37585092575/` に10raw、local/remote回帰一致、runner v2 consistent_candidateを保存した。全job20260927.320.1、公式release/README metadata/Git blobとjournal/log照合済み。VM digest未取得/候補未採択。index2783 B / `0f3263fc3fb405c9f498b59bd88dd10a8efbabc0c0b368f5815665abc4730499`、選択CLI7 sidecar2311 B / `b17584605a44435ddb97ac6432c5244de3e3e33727bf596f04a219d978a8150d`。skip一覧のCRLF6差は両raw pinで明記、他6raw一致。

未保存はCI37587463962（HEAD8faa921/3220、run成功）、37590543104（HEADf0b3d72/3229、進行中）、37592838738（HEAD7da5aa9/3247予定、進行中）。doc-only新CI追跡を増やさない。

## 初版proof code18324bfの失敗保全

CI37592461789（HEAD18324bf）/ attempt1は3.12 job112696985861と3.14 job112696985445がRun unittestでRuntimeError、compare112697079830はskipped。run/jobs/failed log/2journalを `artifacts/ci-diagnostic-37592461789/` に保存した。両journalはtest_started0、成功run_finishedなし。local module discoveryは旧TestCase importで34（新18＋旧16）になり、7da5aa9のmodule参照修正でunique新18を確認した。失敗CIをsuccessへ読み替えず、修正後37592838738を別に追跡する。failure-index842 B / `cb704b22975f573b7b8ef873216ebc2025f7dc5d092b44be8f923e96b3e43adc`、journal-diagnostic2518 B / `a525c616f926ea18cce6a41dc26fb5ff0ba9acddfa0512b5e9d81649977e1604`。正式許可false/credit0/holdout未読、新native0。


## 子keeper code8faa921のCI追補

CI37587463962 / 外部HEAD `8faa921fc5c9e33ebe1a84799b3747c22326f28c` / attempt1は全3job success。3.12 job112680825712、3.14 job112680825951、compare112695061031。各minor3220件・fail0/error0/skip237/source不変、共有29/必須28。専用 `artifacts/ci-diagnostic-37587463962/` に10rawを保存、外部fullHEAD/workflow/run/attempt/jobsを固定したlocal/remote全回帰一致とrunner v2 consistent_candidateを確認。全job20260927.320.1、保存済み公式release/README metadata/Git blobと各minor journal/logを照合した。VM digest未取得/候補未採択。index2783 B / `886f576ab4fd97397a9ac25bd5ea763144eb0b4ca0fec8cd96da4020ac24b63b`、選択CLI7 sidecar2311 B / `9528bb81aa34d0f7cca0a7f96c5b126dbf0e43442aa557fa75d28994349a845b`。skip一覧CRLF6差を両raw pinで明記、他6raw一致。

全helper終了・critical ownerなし・新native0。verification helperのPID38812は先行proof焦点helperと再利用されたため、双方のcreation identity/tokenを各execution.jsonに保全して区別した。PIDだけでは同一process扱いにしない。初版proof CI37592461789の失敗rawは保持。未保存は37590543104（HEADf0b3d72/3229）と37592838738（HEAD7da5aa9/3247予定）、doc-only新CI追跡を増やさない。

実worker接続に向けた選択3 sourceは7da5aa9のworking/Git raw一致。既存parent archiveはverified source_blob専用でpost-close witness、head/status、failed/recovery rawを扱わないため、親の完了部品をworker actorへ流用しない。次は専用opt-in worker archive/raw resolverと元close/recovery eventを小さく固定し、0-job/部分ackの範囲を定めてから実entryへ渡す。source3のpinと静的所見は同CI rootのnext-boundary-notes.json1162 B / `15d03bb0fb9ecc7a4ba6932352da21e00b89620240ac26de192a80d2bff47f5f`。これはruntime閉包/nativeの証明ではなく、正式5残件は変更しない。
