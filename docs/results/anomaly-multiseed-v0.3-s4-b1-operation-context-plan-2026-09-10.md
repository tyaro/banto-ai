# S4-B1 子の作業場所と操作結果診断の修正

状態: **選抜87件・全pure/fake293件・独立レビュー完了。修正後のchildは未実行**。
直前のcontrolは子側の実操作へ進み、旧exit37で停止した。
実API errorと操作名が失われているため、今回の停止原因をCWDやWinError32と断定しない。

## 修正内容

_startのlpCurrentDirectoryだけをfixture.root/controlから同じ専用fixture.rootへ変更する。
親プロセスのCWDは変えない。Windowsは実行中のprocessのcurrent directoryをロックして削除・移動・renameを防ぐ。
操作対象control自体をCWDにする設計は、controlのDELETE権限open検証に干渉し得る。
[Microsoft SetCurrentDirectory](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-setcurrentdirectory)。
CreateFileの既存共有条件も、DELETE accessを含む後続openに影響する。
[Microsoft CreateFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew)。
これは保存コードと仕様から選んだ修正であり、旧37の実原因を実測したという意味ではない。

fixture.rootはcontrol/frozen両操作matrixの対象外で、成功cleanupはchild終了後に行う。
rootは既存のprotected DACLとguardで維持し、token/ACL/環境変数/親CWDは変更しない。
固定childとfixtureの引数は引き続き絶対pathで渡す。操作対象、期待値、share/アクセスmask、必須操作数は変更しない。

operation_unexpectedに限り、実WinErrorと固定48操作ケースのIDを保持する。
コードは0x20000000 | (ケースID << 16) | WinError。既存206理由IDと旧37を変更せず、別のappend-only領域を使う。
復号は保存sourceにある固定ラベルだけで、任意case値・例外文・パス・token/SDを公開しない。
資源WinErrorは操作詳細より先に80へ分類し、右open失敗の資源番号が失われる問題も修正する。
資源停止時はケース文字列生成や親側の追加hash/save/scanを行わない。
positive mutation自体が例外を送出した場合などは既存理由で停止し、操作IDが付かない場合がある。
全種類の失敗を必ず詳細識別できるという保証ではない。

## 検証と次の1回

選抜87/87（0.557秒）pass。実_startへのCWD引数、実_operationsで11種類のpositive right-open失敗時の
操作名・WinError32保持と直後停止、資源番号7種の80優先、全48期待値、frozenでの予期しない成功の拒否、
旧コード・未知case非公開・数値境界を検証する。テスト中のnative API・child起動はない。
独立差分レビュー新規P0〜P3=0、担当のnative/query/試験/編集なし、進捗ポーリングなし。
repository safety/diff-check pass。

全pure/fakeと保存後read-only preflightを完了した候補で、operation-context-control-once.pyを新規fixture1個で1回実行する。
成功には子の全必須操作、report照合、cleanup/teardownまで必要。失敗時は固定診断を保存し、自動再試行しない。
同じRC＋Everyone、flags9、非昇格・同一user/session/integrity、privilege削減、source/runtime pin、protected DACLを維持。
30秒/親＋子512 MiB未満/temp空き1 GiB以上、資源停止後の追加hash/save/scan禁止を維持する。
既存fixture再open/清掃/ACL修復/再利用、別projectへの操作、追加権限は含まない。
成功時もnative_accepted/s4_accepted/formal_permission/execution_authenticatedはfalse。

今回了承されたruntime-machine control1回は実施済み。handoff §6の「追加probeは承認なしに繰り返さない」に従い、
この次の1回への返答を待つ。「お願いします」「続けてください」は当該1回への了承として扱い、再確認しない。

全pure/fake293/293（10.843秒）pass。全Windows nativeテストをまとめて起動していない。
未実行operation-context-control-once.pyは4047 bytes、SHA8dc7b3940930212f477c95b195a2960a0eac0c7bffadcea27784f77a113b0658。
新規summary出力先と保存source上のCWDラベルを変更。AST上harness呼出1箇所、詳細復号は資源停止判定後のみ。
