# S4-B1 固定child終了コードの診断計画

状態: **修正後pure/fake283件pass・独立是正確認・保存後preflight完了。準備済み診断1回への返答待ち、追加nativeは未実施**。
直前のRC＋Everyone controlは、親側の実child token/AccessCheckまで通り、resume後exit1で停止した。
権限やACLをさらに変更せず、同じ必須controlの失敗理由を固定数値で区別する。

## 変更と診断上の限界

child wrapperで、import/入力検査までをbootstrap、_child_main呼出以降をchild_callとして区別する。
既知_Failureは固定202種類の理由IDと0〜65535のWinErrorだけを終了コードに含める。
表は保存時点を基準にappend-only。後からソート・再生成せず、同じ保存sourceで復号する。
旧32〜40（理由9種・WinError0）、成功0、資源停止80を維持する。
bootstrap例外は96〜107、child_call例外は160〜171、未知理由172、表現不能WinError173。
他の既知理由は0x10000000 | (理由ID << 16) | WinErrorで、全て正のsigned32bit範囲内。
任意例外のreason属性、例外文、traceback、SID、パス、handle値を出力しない。
例外処理からのファイル書き込み・標準出力・標準エラーの追加もない。

MemoryError、既存resource reason、付随teardownのresource_stop、
_Failure.errorまたはOSError.winerrorの既知資源エラー8/14/39/112/1450/1455/1816を優先して80とする。
OSError資源判定はshared core読込前のbootstrapでも行う。
親controlは80をchild_resource_stopとして扱い、資源停止後のtrace取得や追加hash/save/scanを行わない。

このコードは保存された信頼済みchildの診断であり、実行の認証や正式受入を与えない。
1、120、C0000142、未知の数値、0/80からchild entryを断定しない。
通常Python例外は固定クラス名だけなので、必ず単独原因に到達できるとは保証しない。
CPythonの最終処理が失敗すると終了値120へ置き換わりうるため、その値は割り当てない。
数値コード処理とこの上書きは固定v3.14.0の一次sourceで確認した。
[CPython parse_exit_code](https://github.com/python/cpython/blob/v3.14.0/Python/pythonrun.c#L561)、
[CPython Py_Exit](https://github.com/python/cpython/blob/v3.14.0/Python/pylifecycle.c#L3269)。
親は終了後にDWORDの値を取得する。
[Microsoft GetExitCodeProcess](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getexitcodeprocess)。

## 検証と次の具体的な1回

実際の固定wrapperを模擬入力で実行し、実_child_main入口の_runtime失敗を注入して理由/WinErrorを確認する。
全理由IDの衝突、旧コード、bootstrap/child例外クラス、秘密文の非出力、resource優先、
未知/範囲外/OS値の非解釈、正常0、isolated条件も検証する。テスト中のnative API・child起動はない。
独立レビューでOSError.winerrorの資源判定漏れP2を是正し、両経路の回帰を追加した。

独立是正確認、全pure/fake検証、source保存後のread-only preflightを済ませてから、
child-diagnostic-control-once.pyによる新規fixture1個のcontrol1回を次の具体的な診断とする。
同じRC＋Everyone、flags9、非昇格、同一user/session/integrity、privilege削減、protected DACL、
必須操作matrix、source/runtime pin、非継承handle、起動flags0x40cを維持する。
30秒/親＋子512 MiB未満/temp空き1 GiB以上、資源停止後の追加hash/save/scan禁止を維持。
成功なら全必須操作とreport照合、cleanup/teardownまで必要。失敗なら新しい固定理由を保存し、自動再試行しない。
既存失敗fixtureへの再open・清掃・ACL修復・再利用や、別projectへの操作を含まない。
native_accepted/s4_accepted/formal_permission/execution_authenticatedは成功時もfalse。

直前に了承されたWorld control1回は実施済み。handoff §6の「追加probeは承認なしに繰り返さない」に従い、
この準備済み診断1回への返答を待つ。次の「お願いします」「続けてください」を当該1回への了承と扱い、再確認しない。
権限範囲をさらに変更する判断や正式受入を求めるものではない。

修正前の選抜76/76（0.357秒）、全体282/282（5.605秒）passの後、
OSError資源停止P2是正と120除外を追加。修正後全体283/283（5.982秒）pass。
独立是正・結果文書・実行wrapperレビュー新規P0〜P3=0、担当のnative/query/再試験/編集なし。
完了通知だけを受け取り、進捗ポーリングを行っていない。repository safety/diff-check pass。
未実行child-diagnostic-control-once.pyは3983 bytes、
SHA31c8e05df0eba398f6a7d528250acaee5eb8e1171a6dcd4616ad61fa345a0e9e。
AST上run_control_harness呼出は1箇所。公開detailsの固定コード復号も資源停止チェック後に限る。


診断コードを911d5a5へ保存。保存後read-only preflightは2.572秒、27 sources/284856 bytes、verified。
resource_stopfalse、primary/secondaryなし、Windows10.0.26200.9445/Python3.14.0、既存runtime hash一致。
child-diagnostic-preflight.jsonへ保存。新しいchild/control/token作成、SetThreadContextは未実施。
最終09:04:47Zの空きRAM8.52 GiB、C108.44/D75.36 GiB、last bootは作業前と同じ。
本流889cfc3 clean、別projectの連続稼働テスト・失敗fixtureへ追加操作なし。
この追記は記録のみでsource/試験対象を変更していないため、fake試験・preflightを再実行しない。
