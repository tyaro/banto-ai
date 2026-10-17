# 検証記録の保存と失敗時の保全

[文書の入口](../../README.md) · [実行・保存の目次](README.md) · [最新の引継ぎ](../../current-handoff.md)

2026-10-12の人の承認により、今後のengineering検証記録に共通の保存処理を使います。
実装は [verification_records.py](../../../tools/verification_records.py)、読取りCLIは [check_verification_record.py](../../../tools/check_verification_record.py) です。
評価計算の出力、固定archive/transport形式、正式受入の容量契約は別の制限を維持します。

## 保存上限

| 対象 | 上限 |
| --- | --- |
| 新規の検証記録root全体 | 16MiB・512ファイル |
| 通常の記録 | 14MiB・496ファイル |
| raw/JSONの分割part | 256KiB |
| 失敗記録・終了manifestの予備枠 | 総量内の2MiB・16ファイル |
| 上の予備枠から終了manifest用に残す枠 | 512KiB・4ファイル |

元の実行時間900秒、private memory2GiB、評価出力1GiB、評価単一file32MiB/files32を変更しません。
Gitの累積30秒・batch16entry/512KiB、stdout1MiB/stderr128KiBも変更しません。
これらは従来のcheckpoint/呼出し制限で、blocking IOや計算の中断、全runtime/native/global容量を証明するものではありません。

新しい保存上限は、新しく作る検証記録rootだけに適用します。閉鎖済み・外部固定済みrootの再利用、追記、整理、移動、削除は行いません。
既存artifact内のhelper scriptや旧制限は当時の原証拠として保持します。固定schema、frame、formal gateへ今回の保存値を流用しません。

## 自動分割と状態

- raw bytesを改変せず分割し、順序・各partのbytes/SHA256・保存stream全体のpinを記録します。
- 大きなJSONもUTF-8のbyte streamとして分割します。読む時に連結するため、part途中の文字境界には依存しません。
- 途中で止まったstreamはpartial、終了コードが未観測ならnullのままです。元のraw prefixや部分fileは削除しません。
- 例外の最小記録を先に予備枠へ保存し、その後にraw streamとtracebackを保存します。長い例外messageの省略も明記します。
- 戻ってきたCompletedProcessは、終了コードとstdout/stderrを保存した後に判定します。記録保存の例外で元の失敗終了コードを置き換えません。
- TimeoutExpiredのstdout/stderrは観測済みprefixとして保存し、完全なprocess logとは扱いません。
- finallyの終了記録にはwrite_terminalを使います。元例外を隠さず、終了記録だけが失敗した正常処理も保存成功にはしません。
- rootの終了状態はcomplete/failed/incompleteです。closeは記録を閉鎖する操作で、未終了operationを成功にしません。

## helperでの使い方

既存の実行・監視・stop/owner保持処理を使い、戻った結果だけを共通保存処理へ渡します。
この部品自身はsubprocessやモデルを起動しません。

~~~python
from verification_records import EvidenceStore

status = "failed"
with EvidenceStore(new_record_root) as evidence:
    evidence.write_json("helper-live", original_creation_metadata)
    try:
        with evidence.operation("command", metadata=original_inputs) as operation:
            result = existing_bounded_execution()
            operation.capture_process(result, stdout_limit=1024**2, stderr_limit=131072)
            validate_original_result(result)
        status = "passed"
    finally:
        evidence.write_terminal("helper-execution", {
            "creation_identity": original_creation_identity, "status": status
        })
~~~

capture_processの上限引数には、その呼出しが従来使っていた値をそのまま渡します。
例外・未着手・判定不能・保存失敗を、性能合格や集計対象successへ補いません。
既存の原PID/creation/start_tokenの照合とunknown owner/handle保持は別に継続します。

## 読取り検査

~~~text
python -B tools/check_verification_record.py artifacts/<new-record-root>
~~~

CLIは閉鎖manifest・全file・順序付きpart・SHA256と状態を読み取り照合します。計算や元のhelperを再実行しません。
record_integrity=passedは保存内容の整合性です。recorded_status=failed/incompleteはそのまま保持されます。
これはcallerの記録の整合性検査で、外部からの実行者認証やnative owner認証ではありません。

## 保存できない場合

通常枠の到達時にも予備枠へ元例外・終了コード・可能なrawを保存し、終了manifest用の枠を残します。
予備枠でも全量を収容できないstreamはpartialとし、既知prefixと保存失敗を記録します。上限を自動で拡大したり、別rootへ原receiptを移したりしません。
実ディスク満杯・権限障害では保存自体を保証できません。元例外を維持し、stderrへ保存失敗を通知します。閉鎖失敗の同一rootを自動再試行しません。
単一writerのlocal検証記録用であり、OS排他、全writer atomic予約、物理disk容量の予約、全process memoryの保証は含みません。

実装・確認結果は [2026-10-12の保存改善報告](../../results/verification-recording-policy-2026-10-12.md) を参照してください。
