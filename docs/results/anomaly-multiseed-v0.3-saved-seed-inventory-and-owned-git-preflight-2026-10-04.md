# v0.3 保存seed在庫と5役Git事前確認（2026-10-04）

この保存点はS4受入前の架空データ技術試行である。登録holdout観測は読んでおらず、正式評価creditは0、gateは`s4_acceptance_not_frozen`のまま。実行結果のrawはGit管理外の`artifacts/`に非上書きで保持する。

## 保存seed在庫の限定結合

clean source `88711500ab7b483496dca40d88b24362724ca9a2` で、[collector](../../src/banto_ai/anomaly_v03_preformal_saved_seed_collector.py)と[c001/c011試走入口](../../tools/preformal_saved_seed_collector_trial.py)を実行した。[保存result](../../artifacts/anomaly-v03-preformal-saved-seed-collector-c01-trial-01/result.json)は4,040 B / SHA-256 `d2eb7940decd32565d918bf2875a5a809b040d260112490fb4ad075639e0feff`。外部固定pinset 4,079 B / `9af50430de87c2a2e080d5b60bd74a0844a28157572221cbaee857dfcbb720b9`、先行1-seed result 3,302 B / `69abe6325db344796b8014a42ce7c3a62e6d957a88971cbbfd25c8d0393f03be`、20 control rawを独立に再hashした。2件のmanifestは同一の歴史的recipe/source/registry宣言を持つ。

結果は**1/40 seed、2/480 chunk、12/2,880評価**。欠番はseed 1–39とchunk 2–479。`cross_seed_manifest_anchor_consistency_checked=false`、`unanchored_40_seed_contribution=null`、最上位`clusters`/`diagnostics`/`slice_source`はnull、campaign認証・正式許可はfalse。collectorの40 seed合成試験は入出力形状と算術を確認しただけで、実40 seedの由来やproducer実行を認証しない。元の保存reader行をこのcollectorで再読取・再計算していない。clean HEAD確認はPATH上の未pin Gitによるもので、所有Git境界の証拠に足さない。

## 5役の直接Git事前確認

[wrapper](../../src/banto_ai/anomaly_v03_preformal_five_role_git_anchor.py)は既存5役Jobの**前**でGit `HEAD`と`status`を各1回、外部pin付き実行ファイルと固定環境で所有して保存する。既存5役内部のGit呼び出しや動的load、Job外process、個別孫exitは対象外。保存再照合はGit事前確認と5役Jobを再実行しないが、既存owner verifierがsource照合のため読取Git subprocessを起動する。

| 実行 | clean source・policy | 保存結果 |
| --- | --- | --- |
| `trial-01` | `afb2517ced5fe0460a83b48b71ccf00155f1f2c7`; policy 581 B / `29a3f6d4273b8b69ab5bad2959aa44891c147db378c1fddcfbc1398d86e7fddf`; `C:\Program Files\Git\cmd\git.exe` 46,480 B / `54194a1af7cfb6730448ce14b8f2c1dddd9f950b7f995dc351c1ed16eb179249` | [outer receipt](../../artifacts/anomaly-v03-preformal-five-role-git-anchor-20261004/trial-01/receipt.json) 1,681 B / `4f4773634351786fe4f6f829222d76f5c8d2ac8d250aa3ab1192f917e8569f80`。read-only別実装で28 rawのpin一致 |
| `trial-02` | `18692678eda77481d1d5f2ca07a04667981d5b6e`; [policy](../../artifacts/anomaly-v03-preformal-owned-git-policy-20261004-03/policy.json) 601 B / `f76f4c4a3897832286af2b6afc58b1f90ec00c2ebd3e0942b8f5de6af6a5d59c`; `C:\Program Files\Git\mingw64\bin\git.exe` 4,285,840 B / `6125857e3aab09c5c79b5328e7d55aedb014b3cdbd4cd60aaf47b8e13cda455b` | [outer receipt](../../artifacts/anomaly-v03-preformal-five-role-git-anchor-20261004/trial-02/receipt.json) 1,681 B / `8ca254ef04be0ace14eeffc2aa3bc7aead14cc74122efff566d9442f735420b7`。保存verifierと、別実装による28 rawの独立pin照合がpass |

`trial-02`の直接Git `HEAD` receiptは2,343 B / `73bf78461a31b53869ed95899e74c51d9817894414e38d0754a2900fd827e6b5`、`status` receiptは2,348 B / `f2200471088e4daf6b2a064a8d0d614b20737c4e3c786bbf6c8582351c803d94`。両方別PID・exit 0で、前者は指定HEAD、後者は空stdoutを保存した。内側[owner receipt](../../artifacts/anomaly-v03-preformal-five-role-git-anchor-20261004/trial-02/attempt/receipt.json)は5,900 B / `3771789d809f7bdd39c2f2165fe0a295cb2649388b9fe8ef1a7b7333cc2931bd`、Job root exit 0、合計1,080 process、終了時active 0、Job wall 71.114秒、peak Job memory 154,849,280 B。5役内の共有予算は69.589秒/262標本でpass、外側policy準備やGit事前確認はその時計に含まれない。候補profileは未指定、旧a3 joinの保存入力を再利用した。`formal_permission`、`source_closure_complete`、`runtime_closure_complete`、`execution_authenticated`はいずれもfalse。

`policy-20261004-02`は実行環境がPython起動時にPATHを元に戻したため`policy-01`と同じ`cmd\git.exe`を選んだ未使用の準備結果で、main binary試行へ加算しない。明示path指定を追加した後、`policy-03`と`trial-02`を新しいclean sourceで行った。

## 受入への残距離

- S4-2: 上の2区間は同一manifest宣言を持つが共通producer/campaign由来は未認証。40 seedの保存行→全slice→正式文書への単一系譜は未成立。
- S4-3: 5役前段のGit 2呼び出しだけが新たに所有された。5役内の多数のbare Git、外部program/動的load、個別孫とJob外processを最終source/runtimeで閉じる必要がある。
- S4-5: producer→保存reader→40 cluster/50,000 draw→完全S6同形監査→writer→別readerを一つの外側予算で測る必要がある。今回の5役予算と旧join、collector試走を足し合わせない。
- S4-1/S4-4: 26H2保証A/Bの版付き採択と独立監査、最終revisionのUbuntu 3.12/3.14両jobとrunner同定、Windows native/dev8/smoke2は残る。

CI取得の観察点（2026-10-04時点）: 当時のlocal branchにはupstreamがなく、制限付き実行ではGitHub CLI設定を読めずremote runは未確認だった。2026-10-05に承認済み実行で`gh`認証を確認し、branch pushと[Ubuntu予備CI初回2 run](anomaly-multiseed-v0.3-preformal-ubuntu-ci-triage-2026-10-05.md)を行った。`.github/workflows/ci.yml`はpush/PRで3.12/3.14と比較jobを起動し、`workflow_dispatch`はない。最終sourceを固定してから同一`head_sha`/`run_id`/`run_attempt`の3 jobとraw artifact・log・runner同定を取得する。journalの`runner_image_digest`は未収集で、[runner同定代替案](../anomaly-v03-s4-26h2-amendment-draft-v2.md)の版付き採択と独立監査が残る。

上の保存verifierはclean HEADの完全一致を要求する。後続文書commitのHEADで`trial-02`を再検証する場合、元の絶対pathでclean `18692678eda77481d1d5f2ca07a04667981d5b6e`に戻す必要がある。raw pinの独立再hashは別revisionからもできる。S5の未使用登録holdoutはS4独立受入まで開かない。
