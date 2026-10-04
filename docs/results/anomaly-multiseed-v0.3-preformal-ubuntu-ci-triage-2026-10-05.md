# v0.3 正式評価前の Ubuntu CI 初回実行（2026-10-05）

`gh` 自体は利用できる。通常の制限付き実行では `GitHub CLI/config.yml` の読取りが拒否されたが、承認済み実行で `tyaro` の認証を確認した。`codex/preformal-acceptance-scope` を新規 push し、upstream を設定した。

| run | source | 結果 |
| --- | --- | --- |
| [37224544937](https://github.com/tyaro/banto-ai/actions/runs/37224544937) | `c08f6fdce999ba83104000c4a02956d78b73c9c7` | 3.12/3.14 とも unittest discovery で同じ9 IDを二重収集し、テスト本体前に失敗。比較jobは未実行 |
| [37224759890](https://github.com/tyaro/banto-ai/actions/runs/37224759890) | `79b28353e8beb952abd7b7fb9922bc2e3d98d5eb` | 二重収集を修正後、両 minor とも2,796件収集・2,784件実行、fail 19/error 65/skip 231。`run_finished` は存在し、`source_unchanged=true`、unittestは不合格。失敗 ID と例外 class の集合は両 minor で一致。比較jobは依存ジョブ不合格で未実行 |

2回目の保存 journal は3.12が3,185,777 B / SHA-256 `21e2f8b4305a589e743e7f79d30b7526640286d577ff38984dcd76b9dd654504`、3.14が3,185,532 B / `430aa0ab234222cfd34540432c861b19c8da64182f8e9f691234a09cc5dac792`。保存job logは3.12が782,305 B / `a5833869360be149a5df62a6e9d979f894d09b0f9d069907015c69a17d42f476`、3.14が809,908 B / `74d31f5f8c9a7784f6b287f635ef903419494c77f04bc1a40017eb7b4412ccac`。これらのrawはGit管理外の`artifacts/ci-diagnostic-37224759890/`に保全した。

失敗はLinux仮パスをWindows限定のfixtureへ渡したもの、生成テストの長いcheckoutパス、2件のbare test import、unittest mockの新しい引数、Linuxにない`CREATE_NO_WINDOW`、旧D2 provenance fixtureに現在のv0.3追加sourceが混ざったものが主である。Windows所有子を要するreader 6件はUbuntu上で明示skipとし、保存payloadのサイズ・request pinを検査する純粋reader試験を残す。次の候補ではこれらを原因別に修正する。次回の実Ubuntu両minorと共有fixture比較が通るまでは予備CI合格と記録しない。

これはS4-4の最終凍結revisionの証拠ではない。runner image digestまたは採択済みの代替同定、Windows 26H2 native、正式dev 8 seed/smoke 2 seed、保証契約の採択と独立監査は残る。登録holdoutは開かず、正式credit 0、gate `s4_acceptance_not_frozen`を維持する。
