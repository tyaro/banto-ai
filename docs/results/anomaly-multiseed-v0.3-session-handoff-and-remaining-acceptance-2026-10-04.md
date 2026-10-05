# v0.3 次セッション引き継ぎ・正式受入までの残件（2026-10-04）

最新（2026-10-05）: clean `e7432e7` の [producer Git所有native試走](anomaly-multiseed-v0.3-producer-owned-git-native-2026-10-05.md) が成功。計156直接Git・536 rawを別照合し、Git起動禁止の保存verifierがpass、Job active0。producer88件を追加したが、analysis / audit / writer / reader 内Git、全source/runtime閉包は残る。初回a1の外側失敗も保全した。先行 `400e370` の [Ubuntu CI 37246057077](https://github.com/tyaro/banto-ai/actions/runs/37246057077) は両minor各2,874件と共有比較の全3 job成功で8 raw保存・ローカル再検証pass。今回の後続codeへ読み替えず、下表の正式同形全工程予算・容量2倍、40 seed由来、契約採択・最終回帰・S6と正式gateは継続する。

最新（2026-10-05）: テスト移植修正`51400e8`の[Ubuntu CI 37243400814](https://github.com/tyaro/banto-ai/actions/runs/37243400814)は全3 job成功、両minor各2,869件・fail0/error0/skip237と共有fixture/必須試験の再検証pass。後続clean `899b37c`では[子の固定Git 26件を含む計68件のWindows試走](anomaly-multiseed-v0.3-child-fixed-git-native-2026-10-05.md)と220 rawの別照合、Git起動禁止の保存verifierがpass。S4-3の次は各role内Gitと全source/runtime閉包。共通campaignの40 seed由来、正式同形全工程予算・容量2倍、契約採択と最終回帰を含む下表の残件は継続する。以下は先行保存点の履歴。

2026-10-05追記: `b39e595`の[Ubuntu CI 37237626121](https://github.com/tyaro/banto-ai/actions/runs/37237626121)は新規wall-rowテストのWindowsパスfixture解釈2件で両minor不合格。製品コードは変更せずテストfixtureを修正し、Windows対象9試験pass。Ubuntu再試験が残る。native試走の保存rawは固定revision `b39e595`の証拠であり、修正版のCIと混同しない。正式gateと下表の残件は変わらない。

この文書は、架空登録形式campaignの最新保存証拠と、正式評価のS4採択からS7結果文書までの残件を引き継ぐ。正式評価の許可や受入判定ではない。科学仕様と正式手順の根拠は[凍結計画](../anomaly-multiseed-evaluation-plan-v0.3.md)、受入5群の起点は[2026-10-03の範囲整理](anomaly-multiseed-v0.3-preformal-acceptance-scope-2026-10-03.md)である。

2026-10-05追記: S4-1の[正式v2 wrapper純粋候補validator](../../src/banto_ai/anomaly_v03_formal_research_v2_candidate.py)とS4-4の[Ubuntu runner由来候補検証器](../../tools/ci_verify_runner_origin_candidate.py)を追加した。関連27試験・compileall・repository safetyはPASS。後者は`a5deb31`の予備run `37230362806`で、3 job生log・release/README・両journal全行を外部pinへ結び`consistent_candidate`を返した。正式wrapper実行・外部pin真正性・完全source/runtime閉包・旧25H2条項の26H2改訂採択・最終revisionの受入はまだである。[公式runner raw pinと検証境界](anomaly-multiseed-v0.3-preformal-ubuntu-ci-triage-2026-10-05.md)を参照。下表と正式gateは変わらない。

2026-10-05追記: S4-2の共通campaign接続を再調査した。既存の[単一wall envelope](../../src/banto_ai/anomaly_v03_preformal_campaign_wall_envelope.py)は架空区間0のprepare→生成→保存reader→completed journalまでで、[保存6行bridge](../../src/banto_ai/anomaly_v03_preformal_campaign_saved_row_bridge.py)は別工程だった。先行`g001`の6行は全て定義どおりの`inconclusive`である。新しい[wall-row入口](../../src/banto_ai/anomaly_v03_preformal_campaign_wall_row_envelope.py)は両者を一つの協調wallに接続し、journal・checkpoint・10保存raw・6行を外部pinで再読する候補とした。旧`4aacbee4`のplanはreader必須source 15件中9件しか固定していないため、新しい厳密なsource結合で拒否する。clean revisionの新rootで実測が必要。[50,000 draw bound bridge](../../src/banto_ai/anomaly_v03_preformal_bound_draw_bridge.py)と[別監査](../../src/banto_ai/anomaly_v03_preformal_draw_audit.py)は正当な`inconclusive`を保持する算術へ拡張したが、発明40 clusterの検算であり保存campaign 6行を40 clusterへ結ぶ入力系譜は未完成。一区間は1/480区間・6/2,880評価の部分由来で、S4-2全体とS4-5の全資源予算ではない。

2026-10-05追記: clean `b39e595`で[新rootのwall-rowと親Git所有native試走](anomaly-multiseed-v0.3-preformal-wall-row-parent-git-native-2026-10-05.md)が限定成功した。新campaign `7aed7840` はreader source 15/15を含む48選定source、外側746.079/900秒、保存6行全て`inconclusive`、23 rawと48 sourceの独立照合がpass。別rootの親Gitは起動前7件・親直接35件を所有し5役Job active0。これらは40 seed由来、Job内Git/全source/runtime、正式同形全工程予算、S4採択を満たさず、旧gateと正式credit0を維持する。

2026-10-05追記: `gh` は承認済み実行で利用できる。`24c8d20`の[Ubuntu予備CI 37228978376](anomaly-multiseed-v0.3-preformal-ubuntu-ci-triage-2026-10-05.md)はPython 3.12/3.14と共有fixture比較の3 jobが成功した。両minor各2,811件・fail0/error0/skip237、共有29 fixture一致、必須28試験pass。後続clean `a5deb31`の[所有Git 7件→5役Jobの架空Windows小試行](anomaly-multiseed-v0.3-five-role-owned-source-native-trial-2026-10-05.md)は保存pinと独立監査が一致したが、所有GitはJob前の7件だけで全閉包ではない。同revisionの[Ubuntu予備CI 37230362806](https://github.com/tyaro/banto-ai/actions/runs/37230362806)も両minor各2,821件・fail0/error0/skip237、共有fixture比較を含む3 jobが成功した。ただしrunner image digest/代替同定の採択、Windows正式native、最終凍結revisionのS4-4判定は残る。下のS4-1～S4-5の残件と正式gateは変わらない。

2026-10-05追記: [選定source Git 7呼び出しの限定試走](anomaly-multiseed-v0.3-owned-source-git-seven-call-trial-2026-10-05.md)をclean `fdaf5eec58d110b5f048c703c740c8e10664fc07`で保存した。`owner._source`1回のHEAD/status/選定5 source blobを外部pin付きmain Gitと別process receiptへ結び、結果1,654 B / `3c68e0577385c3693a5819970e096a3b297e8c8fdf87ea9c0da97d5e9891b2cc`を独立再hashした。既存v1 Jobや保存verifierのbare Gitは未置換で、S4-3の全閉包は未完了。正式gateは変わらない。

最新追記: [保存seed在庫と5役Git事前確認の保存点](anomaly-multiseed-v0.3-saved-seed-inventory-and-owned-git-preflight-2026-10-04.md)を参照。clean `8871150` の外部pin付きc001/c011在庫結果は1 seed/2 chunk/12行、欠番39 seed/478 chunk、40 cluster寄与null。clean `1869267` のGit main binary明示policyと5役`trial-02`は、前段HEAD/statusの所有receiptと内側Job終了・共有予算を結んだ。保存raw28件の別実装照合もpass。ただし前段2呼び出し以外のbare Git、共通producer、40 seed、正式同形の全工程予算は未認証。S4の採択条件と下表は変えず、正式credit0、`s4_acceptance_not_frozen`を維持する。

追記: 架空campaignの最新技術保存点は[共有wall・Jobメモリ付きの `4aacbee4`](anomaly-multiseed-v0.3-slot-wall-and-job-memory-2026-10-04.md)、固定source `772ee3d6e2ea5f02c6c53a72bae6d4daf6942d29`、外部wall receipt 2,230 B / SHA-256 `91714388f56d14649db5ad700e71dc2a6d3a0be41fcc80188c7c6a5ef7d6b38e`。後日read-only verifierで保存chainを再照合済み。その前の[Windows Job所有campaign `5cd8e989`](anomaly-multiseed-v0.3-campaign-job-ownership-2026-10-04.md)は固定source `a1c8461f7ead4f9867ae2c0b48dca367618401f5`、[子anchor照合campaign `72f754b3`](anomaly-multiseed-v0.3-child-echo-campaign-2026-10-04.md)は`2e10c6723df9f00999c90416954a806329546dde`。以下の `486f28cd` のpinと再検証手順は先行campaignの履歴であり、これらを合算しない。

後続追記: clean code `3f708f60cd6d8a1b571e5298effa47893c18f955` の[架空5役割Jobと50,000 draw連続予算の保存点](anomaly-multiseed-v0.3-five-role-job-and-contiguous-budget-2026-10-04.md)を追加した。同revisionの外部候補profile必須5役はJob内で全process終了・read-only再照合まで成功し、receipt 6,580 B / SHA-256 `404147a5744cd34061ab7f8af6f5990668606afcd8cf9ee1055ea57dc074bbea`。主/別算術から文書・sliceまでの先行2試行はsystem commit余裕下限で安全停止したが、後続のclean `51fdb5436a28115e5eeba1400187e3f0b18101d1` のtrial-03は同じ上限・同じ外部入力pinで330.364秒/1,272標本の連続予算を完走し、terminal result 8,048 B / SHA-256 `585a701be5bb0be1fa7ede71c44a8906ac1b2be18643d2be9e0cbd1ff4f23480`を保全した。前述のcampaign、5役、算術試行は入力系譜・予算rootが別であり、合算して正式同形の全工程としない。正式gateと下表の残件は変わらない。

後続code保存点 `5289634b7561e535d84fe65b8b600f0cc5f49467` では、[先行`g001`のjournal・owner receipt・保存行を結ぶ読取専用bridge](../../src/banto_ai/anomaly_v03_preformal_campaign_saved_row_bridge.py)を追加した。旧sourceへHEADを切り替えず、外部固定のplan/両checkpoint pinと2件のowner receipt・22保存出力pin・10 control rawを結ぶ。現workspaceの実保存rawでも1/480区間・6/2,880評価、欠番1～479を照合したが、40 cluster・diagnostics・slice sourceはnull、過去processと131 MB payloadをこのbridgeで再認証していない。5役Jobの保存予算検査も版・root・上限・役割pin/PID・禁止状態を強化した。[CI journal検証器](../../tools/ci_verify_regression_journals.py)は外部run ID/attempt、必須28 test ID、未知skip拒否を追加し、workflow比較jobに接続した。関連統合123試験、compileall、repository safetyはPASS。ただし対象最終revisionの実Ubuntu両job、runner image digest/代替同定、Windows正式nativeは未取得である。26H2保証Aの[採択前改訂案v2](../anomaly-v03-s4-26h2-amendment-draft-v2.md)は正式契約へ反映していない。

clean `ab6fd0469056160931b7f7468702ac7a44782f9a` の[非上書き読取専用postcheck receipt](../../artifacts/anomaly-v03-preformal-campaign-saved-row-bridge-20261004-01/result.json)は5,288 B / SHA-256 `e747697b04f40d0bf3808ed5c7e48c24af38e8b5f290ade04f7c9142b3ddb71e`。外部固定のplan 95,584 B / `88ccc0d87c773b7dd14c95f4fe4522c979824b9b1a17cc21490ace31b2fa8183`、started checkpoint 839 B / `4d6fba71c3076f12e7c81519e1bf51be968cee1e6e0adf0d5da80f52823d5d6d`、terminal checkpoint 1,190 B / `06fec99585e7721aca882f13d192dbf9e533d73336a54a348484f5cad6ad87f0`を入口に、旧保存rawを再照合した。別のread-only確認でもreceiptのraw/source pin、1/480・6/2,880、479欠番、正式flag falseが一致した。このreceipt自体も過去実行の再認証やcampaign全体の完成を示さず、`artifacts/`内でのみ保持する。

後続code `7afb100d69dbdf4c3b96b666e54c83d7aaeb21dc` と直起動修正 `40235b2346dc16a6fb8c5c01457a2fc2ccfa8e07` では、[12 layoutの保存reader行を1架空seed寄与へ集約する純粋境界](../../src/banto_ai/anomaly_v03_preformal_saved_seed_contribution.py)、[所有Git起動helper](../../src/banto_ai/anomaly_v03_preformal_owned_git.py)、[c001/c011読取専用trial入口](../../tools/preformal_saved_seed_contribution_trial.py)を追加した。合成72行では1 seed寄与のcount・delay・slice整合を確認し、不完全・旧attempt・identity不一致は拒否した。所有Git helperは実Gitと偽PATH・非zero・実行ファイル変化/消失を試したが、既存5役へ未接続で `integration_pending=true`、完全閉包false。レビューで見つけた停止失敗時のhandle保持とWindows開始identity再照合も修正した。関連36試験、CI journal検証器9試験、compile、repository safetyはPASS。clean `40235b2` の[実保存c001/c011 trial結果](../../artifacts/anomaly-v03-preformal-saved-seed-contribution-c01-trial-01/result.json)は3,302 B / SHA-256 `69abe6325db344796b8014a42ce7c3a62e6d957a88971cbbfd25c8d0393f03be`。外部pinset 4,079 B / `9af50430de87c2a2e080d5b60bd74a0844a28157572221cbaee857dfcbb720b9` と20制御rawの再hash一致、2/12 layout・12/72行、`cluster_contribution=null`、正式flag false。trialのclean HEAD検査には未pinのPATH上Gitを使い、新helperによる実行handle認証は行っていない。元の2区間は共通campaign由来が未認証で、登録実観測と全40 clusterの証拠にはならない。[S4改訂案v2](../anomaly-v03-s4-26h2-amendment-draft-v2.md#linux-runner同定の代替候補)にはjob別log/releaseのrunner同定候補も追加したが、版付き採択と実CIの取得は未了である。

上記Git helperの停止・identity修正はcode保存点 `a06281396b129cefe7f7ca8eb9a23ede4123179a` に固定した。先行trialは `40235b2` の実行bytesに結び、後続helper修正を当時の実走結果へ読み替えない。

## 先行campaign `g001` の保存点（履歴）

| 項目 | 引き継ぐ値 |
| --- | --- |
| 作業場所・branch | `D:\develop\banto-ai` / `codex/preformal-acceptance-scope` |
| 先行`g001`の固定source revision | `e9107d7323ea6eda2bad8baf1ebd432a879ec4b5`。開始時はcleanで、計画内のselected source raw pinと一致 |
| campaign / 区間 | `486f28cd` / slot 0・attempt 1・path code `g001`、架空固定recipe `hand-normal-v1` |
| 完了宣言 | 480区間中1、2,880評価中6。残り479区間は未実行。40 clusterと正式50,000 drawには接続していない |
| 外部terminal checkpoint | `artifacts/anomaly-v03-preformal-campaign-control-486f28cd/checkpoint-000002.json`、record count 2、head `57a8bd4705be06a4e4817bdb2098c2ec01b391c3ed47b32ae11582b0bb0350e1` |
| 権限・認証 | `invented_only=true`、`actual_registered_observations_read=false`、`campaign_coherence_authenticated=false`、`launch_authorized=false`、`resume_authorized=false`、`formal_permission=false`、`campaign_evaluations_credited=0` |
| 正式gate | `s4_acceptance_not_frozen`。26H2の[運用契約案v2](../anomaly-v03-formal-operations-contract-proposal-v2.md)と[改訂案v2](../anomaly-v03-s4-26h2-amendment-draft-v2.md)は未採択 |

この文書のcommitは固定source revisionより新しいHEADになる。`tools/preformal_campaign_completion_store.py verify`を含むcampaign storeは、計画のsource revisionと**現在のHEADの完全一致**、選定source raw、固定rootを検査する。したがって引き継ぎ文書のHEADで旧campaignを再検証すると拒否される。再検証が必要な場合は、まず引き継ぎcommitを記録し、同じcheckoutを使う別セッションや所有processが動いていないこととclean statusを確認する。その後、**元の `D:\develop\banto-ai` で**cleanな `e9107d7323ea6eda2bad8baf1ebd432a879ec4b5` に一時的に切り替え、保存pinを渡してread-only `verify`を実行し、元branchへ戻す。別pathのworktreeでは計画に固定した絶対pathとroot検査が合わない。source照合や正式flagを緩めて過去の成果を通さない。

`artifacts/` は `.gitignore` の対象で、下記のraw証拠はGit commitには入らない。同じ作業場所でセッションを引き継ぐ。別マシンや別pathへ移る場合、commitだけでは証拠を再現できず、絶対pathを含む計画をそのまま検証できない。

## 先行campaign `g001` の保存証拠（履歴）

次のpinはファイルの**bytes / SHA-256**である。外部control rootは `artifacts/anomaly-v03-preformal-campaign-control-486f28cd/`、campaign rootは `artifacts/anomaly-v03-preformal-campaign-486f28cd/`。証拠は両rootを分け、既存ファイルを上書きせず保持する。

| ファイル | bytes | SHA-256 |
| --- | ---: | --- |
| campaign `plan.json` | 95,584 | `88ccc0d87c773b7dd14c95f4fe4522c979824b9b1a17cc21490ace31b2fa8183` |
| control `checkpoint.json` | 348 | `a71d5f1fce08cbee963bf7a69f7a4b9b84b9aafcbfc5f11a7ce97d8485db7c0f` |
| control `preflight-intention.json` | 1,598 | `c87db0fd95cce1fa00da4f228425126a7a25e4bc4bf58c323e4d2ae9cd8ebbcc` |
| `artifacts/anomaly-v03-preformal-campaign-prepare-486f28cd/receipt.json` | 2,179 | `af2ff24736052d7ab21aaa528a2d7876218238ad7780b8f3e2ad165430fddf14` |
| `artifacts/anomaly-v03-preformal-generated-pinsets-g001/pins.json` | 72,150 | `dfafb87bd6f40c59ab202dc37ae7a2245bc50f50ae1ab727a22073ffc38af26d` |
| campaign `journal/000001.json` (`started`) | 1,244 | `5e1102a23282dcbc48972662f61ddc306edeacb1590eb773768e4376ef20324a` |
| control `checkpoint-000001.json` | 839 | `4d6fba71c3076f12e7c81519e1bf51be968cee1e6e0adf0d5da80f52823d5d6d` |
| campaign `intents/0001-run-budget.json` | 1,540 | `9fe726f12112cdcf452cbf6a1fd47d50a5dd44dfa271d7c8dd6328c5714300d6` |
| `artifacts/anomaly-v03-preformal-campaign-run-intent-486f28cd/request-pin.json` | 1,661 | `a9974b714adeecfc2785fc57c3732fced939ef465b6cca571750913c007095b3` |
| campaign `control/000-1/run-budget/receipt.json` | 6,928 | `3a10f795c6540c927509ffbde564bd42cc82d14e9b6c15ebf692c044f235205f` |
| campaign `intents/0001-saved-reread.json` | 1,854 | `aa93848e4f84a4bdc0437426e3cbd34610528af5fdc40448ab131e5d9e717eba` |
| `artifacts/anomaly-v03-preformal-campaign-reread-intent-486f28cd/request-pin.json` | 2,119 | `3910d9901c828f757aec9075d1f3fff16a91b29ef7cd88239a7e0f8b248073e5` |
| campaign `control/000-1/saved-reread/receipt.json` | 2,470 | `d67777f8677a92674cef979534549944e8f4afdafe4bcd5dd84006c5d75eaa96` |
| `artifacts/anomaly-v03-preformal-saved-row-reread-g001/rows.json` | 116,085 | `8d03146c324bd534dc07633c835a1cb49e7c330e222932e111a8f3aa1c41aba5` |
| campaign `journal/000002.json` (`completed`) | 6,641 | `57a8bd4705be06a4e4817bdb2098c2ec01b391c3ed47b32ae11582b0bb0350e1` |
| control `checkpoint-000002.json` | 1,190 | `06fec99585e7721aca882f13d192dbf9e533d73336a54a348484f5cad6ad87f0` |

独立read-only監査でmanifestの22保存raw、合計131,144,120 Bを実ファイルから再hashし、22/22一致した。両owner receiptは`verified`で、保存された監督証拠内の直接CLI 2件と内側3 processのPID・開始token・exit 0も整合した。生成側の共有予算は193.594秒・752標本・最大root 131,337,574 Bで上限内、fresh再読取り側も6行・共有予算内である。ただし両者は**別予算**で、prepare、40 cluster/50,000 draw、独立監査、公開まで含む単一外側予算の合格ではない。子孫全体の強制停止・wait/reapも未証明である。`journal/000002.json`の保存raw pinは、後続の照合元とする。

先行campaign `ba59beff` はprepareのみ、`61ac0ac8` は`started`とrun-budget verifiedまでで`completed`がない。失敗した`0d3648ed`、別系譜の`c001/c011`も保持する。どれも`486f28cd`へ足さず、共通campaignのcoverageに算入しない。固定source `e9107d7`で関連統合77試験とrepository safetyがPASSした。文書更新後にその試験を新revisionの受入証拠へ読み替えない。

## 正式受入までの残件

| 順序 | 残る受入・作業 | 完了を判定する証拠 |
| --- | --- | --- |
| S4-1 契約採択 | 旧25H2/build26200/UBR9168の§8–9に対し、現26H2/build26300/UBR9457のOS/Python exact tuple、root/schema、source revision、失敗・再登録、slice/sidecar mappingを版付きで決定。通常単一writer保証Aか、旧protected DACL/独立tokenを保つ保証Bかを選び、独立再監査する。5 payloadの純粋候補validatorは実装済みだが、正式wrapperや実行認証ではない | 改訂した計画と運用契約、選択保証のWindows native試験、旧contractとの差分と独立監査。v2 proposalと候補validatorのままでは不合格 |
| S4-2 登録入力・consumer | 凍結した40 seed/480区間/2,880枠の入力と実保存readerを、観測→profile/score/ledger→全slice/sidecar→50,000 draw→正式文書へ、架空の固定入力で接続する。実holdout成功receiptはこの段階で要求しない | 予定/実行identity、最新attempt、保存rawと終了、全分母・全条件別在庫、文書の固定経路と失敗拒否を照合 |
| S4-3 5役割の閉包 | producer/analysis/audit/writer/readerの最終clean source、動的load・外部programを含むruntime依存、起動前/中/終了証拠、異常時の子孫停止・回収を固定する | 最終revisionの外部pin、各役の実process証拠と独立再照合。現campaignのselected source pinや親の子申告だけでは全閉包にならない |
| S4-4 対象環境・最終回帰 | 最終revisionでUbuntu 24.04 x86_64のPython 3.12/3.14両job、選択保証に応じたWindows 26H2/CPython 3.14 native、正式dev 8 seed・smoke 2 seedの全layout/両層/3候補を受け入れる。予備runの外部log/release候補照合は完了したが、代替規則の採択ではない | CIのpass/fail/skipとrunnerの版付き同定。未取得の`runner_image_digest`は取得するか、計画で同等の同定方法に改訂する。Windows 3.12は追加必須条件ではない |
| S4-5 全工程予算・容量 | producer→登録形式保存reader→40架空cluster/50,000 draw全文書→完全S6同形audit→staging/writer→別readerを、一つの外側予算と停止・回収で測る。工程別内訳と計画所定の容量2倍検査を採択する | wall/容量/private memory/system commit、失敗停止、全process終了、公開後fresh readを含む実測。独立の部分予算を加算して代用しない |
| S5 正式実行 | **S4採択後のみ**、未使用の登録holdout 40 seedを凍結clean revision・新rootで一度実行。性能を見た条件変更や既存root/seedの再利用をしない | 480区間・960 dataset・2,880評価の実bytes、全attempt、環境・終了・保存pin、欠落0。失敗は保全し再登録規則に従う |
| S6–S7 独立監査・報告 | S6で保存raw観測からprofile/score/episode/ledger、全分母、50,000回CI、gate/選択とsliceをread-onlyで独立再導出し、別rootへ公開してfresh reader照合。S7で3候補×core/stress/overall、全gate、失敗・制約、producer/analysis/auditのSHA・hash、昇格なしの場合も監査に沿って結果文書へ記す | 独立数値一致、全payload/sidecar/receipt/reader一致、結果文書とS6 pinの対応 |

S4前の追加技術作業として、[campaign controller案](../anomaly-v03-preformal-campaign-controller-next-v1.md)にある子へのanchor echoと子孫の所有回収、登録行から40 clusterへの由来、全工程予算を詰める。ただし**架空480区間の完走を新たなS4必須条件に自動追加しない**。現campaignの`resume_authorized=false`は次区間の自動続行権限を意味しない。次の小試行が必要なら、範囲と固定sourceを決めた新しい非上書きrootで扱う。

最新の`4aacbee4`では一区間の共有wall 503.798/900秒と3外側Jobのピークメモリを保存した。これはS4-3/S4-5の部分証拠であり、5役割閉包、正式同形の全工程予算、容量2倍はなお未了である。

## 実データの境界と次の着手

保存済みの「実データ」は合成信号を実際に生成したengineering dev 8 seed・smoke 2 seed、120区間・240 dataset・720評価であり、[新readerからの要約・記述報告](anomaly-multiseed-v0.3-real-saved-summary-report-2026-10-03.md)まで実適用済み。実設備・顧客データではない。先行`g001`と最新`l001`は架空recipeの技術試行で、ファイル名にholdout seed identityがあっても**登録holdout観測ではない**。未使用40 seedの実観測はS4採択前に読まず、正式creditは0。正式文書のnull欄を「残り4試験」と数えない。

次セッションはまず `git status --short --branch`、引き継ぎcommit、冒頭の後続保存点と各source revisionを確認する。上表とpinは先行`g001`を旧verifierで再検証する場合だけ用いる。新bridgeは保存rawを外部固定pinから現HEADでも読取照合できるが、当時のprocess・payloadの実行認証を再発行しない。5役割Jobのnative旧試行はclean `3f708f6` と元の絶対path、trial-03の連続予算はclean `51fdb54` へ結び、後続revisionの成果へ読み替えない。次は26H2契約と保証A/Bの採択、登録保存readerを含む共通入力系譜、**producerから別readerまで**の全工程単一予算、完全S6同形audit、最終revisionのLinux/Windows・dev/smoke受入を進める。旧gateと旧artifactを変更せず、S4の独立判定を得てからS5へ進む。
