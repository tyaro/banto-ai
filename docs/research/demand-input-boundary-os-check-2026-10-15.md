# 文書検証のGit実行環境と保存した初回失敗

2026-10-15 JST。モデル/契約コードの23fixture・migration・独立原snapshot照合はcomplete。文書閉鎖初回のgit diff --checkだけがexit69で起動できず、stderrにXcodeライセンス未同意と出た。初回doc-recordsをfailedのまま保存した。ライセンス同意やXcode設定変更は行っていない。

利用可能な同梱runtimeのGit 2.53.0を明示して同じgit diff --checkを実行し、別doc-records-v2で閉鎖する。これはGit起動環境の切替による文書検証で、model/入力/label/変換/scoreの再生成ではない。旧failed rootは改変・削除しない。

共通Mac契約検査・独立原データ照合と、OS環境による既定Git起動失敗を分けて報告する。Windows固有/nativeとOS依存包括suiteは未実行、2015新内容参照・再評価/新fit/予測/scoreは引き続き0。
