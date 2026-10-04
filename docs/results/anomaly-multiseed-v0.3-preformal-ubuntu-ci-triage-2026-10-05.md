# v0.3 正式評価前の Ubuntu CI 診断（2026-10-05）

`gh` 自体は利用できる。通常の制限付き実行では `GitHub CLI/config.yml` の読取りが拒否されたが、承認済み実行で `tyaro` の認証を確認した。`codex/preformal-acceptance-scope` を新規 push し、upstream を設定した。

| run | source | 結果 |
| --- | --- | --- |
| [37224544937](https://github.com/tyaro/banto-ai/actions/runs/37224544937) | `c08f6fdce999ba83104000c4a02956d78b73c9c7` | 3.12/3.14 とも unittest discovery で同じ9 IDを二重収集し、テスト本体前に失敗。比較jobは未実行 |
| [37224759890](https://github.com/tyaro/banto-ai/actions/runs/37224759890) | `79b28353e8beb952abd7b7fb9922bc2e3d98d5eb` | 二重収集を修正後、両 minor とも2,796件収集・2,784件実行、fail 19/error 65/skip 231。`run_finished` は存在し、`source_unchanged=true`、unittestは不合格。失敗 ID と例外 class の集合は両 minor で一致。比較jobは依存ジョブ不合格で未実行 |
| [37227450486](https://github.com/tyaro/banto-ai/actions/runs/37227450486) | `7042019e6d6e9ab6b6c2e17128a1500f2b738574` | Linux fixture移植後、両 minor とも2,811件実行、fail 0/error 1/skip 237。唯一の同一例外は controller receipt試験のLinux checkout長によるWindows実測path上限。予定test ID、skip行、共有fixture 29件は両minorで一致。`source_unchanged=true`、比較jobは未実行 |
| [37228978376](https://github.com/tyaro/banto-ai/actions/runs/37228978376) | `24c8d200a368f8d0f00dd26f3055226a64aff553` | 該当試験だけPOSIXのcheckout長を許容する修正で再実行中。製品のpath上限は変更なし |

2回目の保存 journal は3.12が3,185,777 B / SHA-256 `21e2f8b4305a589e743e7f79d30b7526640286d577ff38984dcd76b9dd654504`、3.14が3,185,532 B / `430aa0ab234222cfd34540432c861b19c8da64182f8e9f691234a09cc5dac792`。保存job logは3.12が782,305 B / `a5833869360be149a5df62a6e9d979f894d09b0f9d069907015c69a17d42f476`、3.14が809,908 B / `74d31f5f8c9a7784f6b287f635ef903419494c77f04bc1a40017eb7b4412ccac`。これらのrawはGit管理外の`artifacts/ci-diagnostic-37224759890/`に保全した。

3回目のjournalは3.12が3,196,752 B / SHA-256 `acc2fa14a4735c38245c5d43df796dccb90a5c6bab2e24912f55bb8d9aee927d`、3.14が3,197,042 B / `d948c7b5bda8f51f55656fcc5b879ba87f3cd3cef03a625176c27bcc29e58a90`。保存job logは3.12が635,352 B / `98788b878a3360940d9ab36069693f0457df8ec58cf7ed81cd9319609d8e5610`、3.14が635,874 B / `530284d56c4a837f5bce91314e41e7ce23bd25734ca50bfd1d8e2b4716b28f75`。Git管理外の`artifacts/ci-diagnostic-37227450486/`に保全した。両job logのUbuntuは24.04.5、runner image `ubuntu-24.04` / `20260927.320.1` と表示されたが、image digestは未取得である。

初期失敗はLinux仮パスをWindows限定のfixtureへ渡したもの、生成テストの長いcheckoutパス、2件のbare test import、unittest mockの新しい引数、Linuxにない`CREATE_NO_WINDOW`、旧D2 provenance fixtureに現在のv0.3追加sourceが混ざったものが主であった。`7042019`で原因別に修正し、Windows所有子を要するreader 6件はUbuntu上で明示skip、保存payloadのサイズ・request pinを検査する純粋reader試験を残した。残るcontroller receipt試験のPOSIX checkout長は`24c8d20`でそのテストだけ修正した。4回目の実Ubuntu両minorと共有fixture比較が通るまでは予備CI合格と記録しない。

これはS4-4の最終凍結revisionの証拠ではない。runner image digestまたは採択済みの代替同定、Windows 26H2 native、正式dev 8 seed/smoke 2 seed、保証契約の採択と独立監査は残る。登録holdoutは開かず、正式credit 0、gate `s4_acceptance_not_frozen`を維持する。
