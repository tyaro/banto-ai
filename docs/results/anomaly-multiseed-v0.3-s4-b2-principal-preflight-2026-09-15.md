# S4-B2 管理者Preflight単独診断の停止

2026-09-15。実装d025f4bbd83a9e928c3b93ecdae373605c47459b、[仕様](../anomaly-v03-principal-preflight-diagnostic-design.md)。通常権限で既存34件＋5 phase限定の9件＋loader10件pass、独立P2一件（Entry後のidentity解放で一次codeを上書き）を修正し残0。最初のloader試験はStrictModeでnull Arguments.Countを参照して停止し、試験側のnull確認を修正した。失敗logも保存し、再確認はpass。
公開DLL24576 bytes/SHA256 e4f6434af6af374e9170781c901ed3e82f802c617d18cf2a87fa20c41b10dbdc。同じ16754文字のcommand/SHA256 e5c36c1d9551efdde8ee41ee3964ae910745697e0447b9d611e0bdbc93e4e08eを通常/管理者で使用した。

| 実行 | UTC開始〜終了 | PID | exit | 起動/待機/合計ms |
| --- | --- | ---: | ---: | --- |
| Control | 05:04:01.6064087〜05:04:04.4532608 | 41156 | 41 | 117/2693/2845 |
| Run | 05:04:11.3386840〜05:04:18.5345770 | 39304 | 66882 | 3951/3198/7192 |

両processのHandle取得・終了・observer解放成功、観測例外なし。Controlは固定U SID/非昇格のみ確認。Runはphase1/error1346で停止し、Preflight成功やtoken3個の明示close/watchdog joinは確認していない。診断process終了と明示close成功を混同しない。後続作成phase/準備Entry、SAM、protected root、祖先handle、OS設定変更は呼んでいない。両guard閉鎖、旧root3件にも再訪なし。
97 sourceをGit/raw照合、前回92 source/4 artifacts不変。input19859 bytes/hashdc3d2083e7fca80967a2290bfc32957da5fc2211166356e6a3be0fce6134c0e8、input時11 artifacts不変。
artifacts/principal-preflight-diagnostic-2026-09-15の最終manifest21180 bytes/hash **46fa0a7d1e4a882d4d8e31d2fcdb43ed305057a7956d1bcaa406a52c3fe405c4**。17 artifacts/論理75892 bytes（最終manifestは集計外）。
UTC05:03:46 RAM6130712576/C148311093248/D219493842944 bytes→05:05:55 RAM5630140416/C148313010176/D219493822464 bytes。build26200.9445/boot2026-09-09T10:43:08.5000000+09:00、Windows Update engineering緩和/正式pin不変。本流889cfc3/clean、既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621保全。

次は[識別用token診断](../anomaly-v03-principal-identification-diagnostic-design.md)。個別API名は未観測で、要求levelを用途に合わせて下げる変更を新規診断枠で検証する。環境準備/P-U/正式B2-S4未完了、全許可flags=false、acceptance_status=not_completed。
