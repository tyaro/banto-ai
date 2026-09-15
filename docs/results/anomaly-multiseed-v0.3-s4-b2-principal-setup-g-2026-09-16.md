# S4-B2 準備gのSACL自動継承状態差

2026-09-16 JST、revision5fe02878bd75911a56878406f081db8c28bc08a6。[仕様](../anomaly-v03-principal-setup-g-design.md)の固定診断を追加。build-01はlabel差の試験で停止し未採用、mandatory labelを含むraw ACL比較を補ったbuild-02で43＋15＋launcher12件pass。独立レビュー指摘0、safety/diff pass。通常load-only PID8836/exit0、command17859文字。
採用DLL26624 bytes/hash56e8c69fa2d0820641b43b6770705258c5e710be308f8345737209c395f810d2。104 sourceをGit/raw照合、前回99不変/4変更/新規1、旧f12公開artifacts不変。UTC15:20:22.9155471Z、SAM2221/free0、新規g root error2。input21107 bytes/hash0d6eb0ef6699ae6673e371ee026c5c310213449902a2873fca48facc9ac24fcb。

Run UTC2026-09-15T15:20:33.6526646Z〜15:20:41.8082263Z、PID10092/exit537209480、Handle/終了/observer解放確認、観測/解放例外なし。launch3458/wait4637/total8146ms。
診断はphase5、kind1 InvalidOperation、step10 exact-policy-comparison、difference136=8(SACL部分)+128(SACL auto flags)。差分類は完了済み。所有者/グループ/DACLと保護bitは比較範囲内で一致し、祖先検査とroot identityを通過した。一方、SACL差はauto flagsとraw ACEを併合するため、labelそのものの一致、AIとARのどちらの差か、実SDDL全体は断定できない。fの過去原因も遡って確定しない。
元の厳密比較で失敗しaccount作成へ進まない。UTC15:22:08.3930654ZのSAM2221/free0でaccount不存在。g rootは再訪せず現在状態unknownとして閉鎖。旧末尾なし/b/c/d/e/f/gの7 rootを閉鎖。release_failed=falseを失敗helperの特権復元/通常teardown成功と解釈しない。

最終savepoint-evidence.json23630 bytes/hash753f2f440a0f8edfb4b9f43668ca2de736fbb634e25c10dce2f8cf20cda95912、14 artifacts/論理135727 bytes（自身除外）。終了後RAM5953048576/C149775142912/D198225760256 bytes、D約184.61GiB。PC全体の容量変動原因や長期リーク有無は未確認。
OS26200.9445/boot2026-09-15T14:30:24.5000000+09:00、Windows Update engineering緩和/正式pin不変。本流889cfc3/clean、既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621保全。
次は[SACL AI状態を明示する新規h](../anomaly-v03-principal-setup-h-design.md)を厳密比較で検証する。全許可flags=false、acceptance_status=not_completed。環境準備/P-U/正式B2-S4は未完了。
