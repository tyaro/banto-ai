# S4-B2 公開側と通常peerの権限分離案

2026-09-15 JST、基準1185287。設計savepoint **60ac6c45c737c0785540f976de1dfb16abb4d7f0**。
[権限境界案](../anomaly-v03-principal-boundary-design.md)を作成し、独立P0〜P3所見0件で保存した。
**専用の標準local accountと保護された新規rootを使う案を、環境準備の判断対象とする。OS変更・native試行・新workerは今回0。**

## 設計で具体化した点

親shareだけの保護は[直前のpath追加成功](anomaly-multiseed-v0.3-s4-b2-namespace-readonly-2026-09-15.md)で不足が確認された。
同一userへの既存allowを残したままrestricted token/AppContainer ACEを追加するだけでは、通常peerからの変更を排除できる根拠にならない。
Microsoftの二段判定の説明を使った設計上の推論であり、AppContainerの一般的な隔離機能を否定する実験結果ではない。[公式説明](https://learn.microsoft.com/en-us/windows/win32/secauthz/implementing-an-appcontainer)。

公開側P、現userの通常peer U、管理者側bootstrap B、consumer Rを分けた。
外側祖先/code/runtime、root、writer、sealer/rename、marker、公開後、evidence/IPCごとに必要権限・禁止操作・保持期間を一覧化した。
別SIDだけで成立とはせず、共通group ACE、owner/MIC、既取得handle、process/thread/tokenの権限、初期SDと資格情報の露出、code差替えも条件に含めた。
通常peerの名前操作を非目標へ外さず、ownerによる意図的DACL変更という既存非目標と区別している。

候補account **BantoS4Publisher**、候補root **C:\ProgramData\BantoAI-S4B2-principal-20260915**。
UTC2026-09-14T16:09:00Zの読取確認で、どちらも未存在。C:\ProgramData/既存Python3.14.0の利用可能性を出発点にするが、Pからの実行権限やruntime closureは未検証。
通常userのworktree・旧fixtureのACLを変更せず、常駐service/task・別VM・新runtimeは初回案に含めない。
管理者承認、新accountの資格情報・起動、有効/無効状態の運用が増える。秘密を会話/引数/ログへ保存する方式は採用しない。
account無効化をtoken/handle失効と読み替えず、作成したprocessの終了を別途確認する。account/rootの自動削除はしない。

初回harnessはPによる新規root/空file作成と、別U workerの読取control/変更要求/path CREATE_NEWだけを検証する案。
Pが成功しUが拒否されたという差と、実SD/token/起動/終了の条件を揃える。作成失敗や不明応答ではP/B側の親を保持してU終了を確認し、失敗名へ戻らない。
要求mask/SDDL、保護された起動、code配置、IPC、複数processの不明所有は実装前の残件。既存単一workerを無変更で証明に流用しない。
P/U合計メモリ上限と40/45秒、出力/記録上限を提案したが、まだ実装・強制された上限ではない。

既存frozen親内rename拒否、最後のatomic marker renameと未採用の空marker予約方式の選択は、専用accountだけでは解決しない。
環境案への同意に、これらの正式契約変更やB2/S4受入を含めない。まず生成前からの権限分離だけを確認する。

## 照合・保存・資源

独立レビューは案の一次資料調査と設計レビュー、read-only/進捗ポーリングなし。新規P0〜P3=0。
文書だけの変更のためunit test/nativeは再実行していない。前回401件passの対象を含む72 sourceのraw bytesとGit blobが不変であることを確認した。
新設計を加えた73 sourceをsavepointへ固定。前回namespace-readonlyのmanifest/13 artifactsも不変。repository safety/差分/設計の相対リンク検査pass。
ignored artifacts/principal-boundary-2026-09-15に5 artifacts/論理6400 bytes（manifest自身を除外）、10件のMicrosoft一次資料URL索引と読取事前確認・資源記録を保存。
savepoint-evidence.json15459 bytes/hash59c213c693f4a3f9f78f052f12da812c66d78ae18e7f8309ff62522c807b04ec。

UTC16:09:00 RAM15287701504/C125320380416/D45614538752 bytes、16:15:06 RAM15147569152/C125313695744/D45614526464 bytes。
D空きはこの記録間で12288 bytes減、約42.48GiB。前工程の約8.83GiB減少という履歴を取り消さず、全体変動の原因は未特定とする。
新しい常駐監視/VM/worker/実機checkoutはなし。長期リーク不在の主張はしない。
build26200.9445/boot2026-09-09T10:43:08.5000000+09:00、Windows Update engineering緩和/正式pin不変、Python3.14.0。
既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保持しcommit除外。本流889cfc3不変。
旧source/枠の再open/列挙/hash/copy/delete、push/merge/CI、他project/processへの操作は行っていない。

## 次の作業の判断

このPCに専用標準accountと新規rootを追加する方式で検証環境の準備へ進むか、ユーザーの判断を受ける。
理由は、新規accountというPCに残る設定と管理者・資格情報運用が増えるため。skillや自動承認審査による停止ではなく、この変更範囲を明確にする判断である。
選択後はbootstrap/試験の具体的な実装・故障確認・レビュー・savepointを進める。旧fixtureを使った試行や既存設定の流用は行わない。
環境未承認、isolation_certified/protected_commit_allowed/future_immutability_proven/formal_permission/execution_authenticated=false、acceptance_status=not_completed。
