# S4-B1 子の作業場所と操作結果診断の修正

状態: **最大3候補の了承を受領し、1回目がnative_control_pass。成功条件により試行枠を終了、追加実行なし**。
[実行結果](anomaly-multiseed-v0.3-s4-b1-operation-context-result-2026-09-10.md)とhandoff §76を参照。
以下の未実行・未承認・返答待ち表記は準備時点の履歴であり、再実行の指示ではない。
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

今回了承されたruntime-machine control1回は実施済み。handoff §6の追加probe条件について、
毎回の確認を減らすため、下記の限定した進行方針を今回の返答対象として提示する。

全pure/fake293/293（10.843秒）pass。全Windows nativeテストをまとめて起動していない。
未実行operation-context-control-once.pyは4047 bytes、SHA8dc7b3940930212f477c95b195a2960a0eac0c7bffadcea27784f77a113b0658。
新規summary出力先と保存source上のCWDラベルを変更。AST上harness呼出1箇所、詳細復号は資源停止判定後のみ。


修正コードを0b30e63へ保存。保存後preflight2.884秒、27 sources/288326 bytes、verified。
resource_stopfalse、primary/secondaryなし、Windows10.0.26200.9445/Python3.14.0、既存exe/DLL hash一致。
operation-context-preflight.jsonへ保存。修正後のrestricted child/controlは未実施。
最終09:40:09Zの空きRAM8.24 GiB、C108.16/D75.36 GiB、last bootは作業前と同じ。
本流889cfc3 clean、別project・失敗fixtureへの追加操作なし。点の資源量でリーク有無は断定しない。
この追記は文書のみでsourceを変えないため、fake試験・preflightを再実行しない。

## 今回提示する進行方針（未承認）

準備済み0b30e63候補を含む最大3候補について、各候補control harness1回、合計最大3回まで進める。
child作成前に失敗した呼出も1回と数える。同じcandidateの再実行はしない。
次の候補は観測結果に基づく修正・診断改善が必要な場合だけ準備し、各候補の適切なpure/fake検証、
独立差分レビュー、source保存、read-only preflightと空き資源確認を終えてから1回実行する。
権限/token/保護DACL/必須期待値/起動隔離条件/資源上限は変更しない。既存failure rootsや別projectを操作しない。
成功、資源停止、所有後処理の不確実性、許可条件外の変更が必要な場合、または3回消化で停止して記録する。
各結果・修正は保存する。正式受入/本流統合/formal/B2/publisherの許可を含まない。

この問いへの「お願いします」「続けてください」を上記最大3回への了承として扱い、受領後は§6の都度確認をこの範囲だけ緩和する。
現時点では未承認であり、今回実施済みのruntime-machine1回を再実行する意味ではない。
§75の先の「次の1回への返答待ち」は準備途中の記録で、今回最終提示する対象はこの限定した最大3回の方針とする。
