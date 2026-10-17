# v0.3 Job子の固定Git 26件を所有した限定試走（2026-10-05）

clean source `899b37c17020e0782e63bcd8be720e6661022453`、Windows 11 Pro 26H2 / build 26300.9457、CPython 3.14.0で、親Git入口の新しい`--own-child-git`を実行した。入力は先行の架空archiveだけで、登録holdout観測の生成・読取り、正式評価creditは0。

v2 invocationは外部policyのpath・raw pinを子へ渡す。子の開始時7件、five-role chainの開始/終了各6件、子の終了境界7件を既存の所有Git sessionへ接続し、計26件の順序を固定した。子はsession manifestの保存・再照合と26件の完了後に応答する。外側は起動前7件・親35件・子26件、**計68件**の別manifestを照合して`verified`。候補profile指定は引き続き拒否する。

| 保存raw | bytes | SHA-256 |
| --- | ---: | --- |
| 外部`policy.json` | 601 | `a6c6ee346f867f5c4eb1e16cecaa7c10fa944ae8ecc1a9d04624dc0e0a5adf6a` |
| 外側`attempt/receipt.json` | 3,333 | `46ea4e30921b93804831235723ab4deec453330a37ff4495b81c5de5e2b42d8c` |
| 起動前7件`git/manifest.json` | 3,393 | `a75ccd93435201ddd28c50483886746a028cab67d900721984b96aa24c272440` |
| 親35件`parent-git/manifest.json` | 14,297 | `d7579dc1ef9eff2b1d6316a274d40598f29a7e2959c208c468081be47a9f8dc0` |
| 子26件`attempt/child-git/manifest.json` | 10,796 | `45aad9dd4d33837f972e29bb2dd38849e7a80551055b3032875cbc4f9b8ccf2d` |
| Job owner `attempt/receipt.json` | 5,904 | `3f6c91e54ea79922bec8dddac9ee6327ba24910f18b20f064a529335ff3907ce` |
| [別実装のraw再hash](../../artifacts/anomaly-v03-preformal-child-owned-git-trial-20261005-a1/audit.json) | 54,545 | `ac83038e412ee4e42d8121fc60fd34389d1874ce99576da7f31cf906175fd556` |
| [Git起動禁止の保存verifier](../../artifacts/anomaly-v03-preformal-child-owned-git-trial-20261005-a1/saved-verifier-no-launch.json) | 406 | `cb01ffe9dac51f629c09f594386f3e484e801b3dd0be56014585697c476324e2` |

policyは`C:\Program Files\Git\mingw64\bin\git.exe`本体4,285,840 B / `6125857e3aab09c5c79b5328e7d55aedb014b3cdbd4cd60aaf47b8e13cda455b`を固定した。保存rootは`artifacts/anomaly-v03-preformal-child-owned-git-trial-20261005-a1/attempt`、外部policyは同じ`artifacts/`直下の別rootである。rawはGit管理外で保持する。

別実装は220 rawのpin、68件の直接processのPID/start token・exit0・元handle終了確認、Git stdout/stderr、5選定sourceのworking/Git blob一致、v2 invocationと外部policyの結合を再照合した。保存verifierはbare Gitと所有Gitの両起動経路を禁止しても`verified_retained`。Jobは計1,080 process・終了時active0、peak Job memory 154,931,200 B。5役の共有標本予算は95.6185093秒、親private peak 118,894,592 B、root最大25,306,877 B / 108 entries / depth4でpass。この予算は5役rootの測定であり、外側のGit工程すべてを含む正式全工程予算ではない。

関連32試験、compileall、差分検査、repository safetyはpass。新規試験では26件の順序、保存manifest完成前の成功応答拒否、policyとjoinの分離、候補profile拒否、68件の保存再検証、v2 invocationを古い経路へ差し替えた場合の拒否を確認した。先行テスト移植修正`51400e8`の[Ubuntu CI 37243400814](https://github.com/tyaro/banto-ai/actions/runs/37243400814)は両minor各2,869件・fail0/error0/skip237と共有fixture比較の3 jobが成功したが、この後続コードのCIへ読み替えない。

`child_fixed_git_owned=true`は固定26件だけを示す。各role内のsource/依存Git約366件、Gitがロードしたコードと子孫、全source/runtime閉包、個別孫exit code、40 seed由来、完全S6、正式同形の全工程予算・容量2倍と契約採択が残る。`inner_v1_git_owned=false`、`source_closure_complete=false`、`runtime_closure_complete=false`、`formal_permission=false`、旧gate `s4_acceptance_not_frozen`を維持する。次はrole内Gitへ所有readerを渡す接続と、各roleの固定/動的在庫を検証する。
