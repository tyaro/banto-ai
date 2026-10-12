# S4-B2 公開状態と完了印のpureモデル

日付: 2026-09-11。基準f9f3ea5。状態: 実機接続前の設計prototype。

本体の保存・権限固定・名前確定・最終再検査・完了印のcommitを別の境界として扱う。
既存B1の限定control成功とLinux/Windows選抜fixture一致を、この公開工程の実機受入に読み替えない。
今回の成果物は`tests/fixtures/anomaly_v03_publication_model.py`とpure/fault試験であり、
filesystem/Win32/token/ACL/正式rootへの接続を持たない。production publisherの実装ではない。
src、D2 current-only集合、科学schema/config/registry、正式OS pinは変更しない。

## 単一attemptの状態

| 順番 | 操作 | 成功応答が得られない場合 |
| --- | --- | --- |
| 1 | prepare: 新規専用rootにpayloadとpending markerを排他的作成・write/flush | 一部が作られた可能性があるためunknown |
| 2 | verify_prepared: 全bytes/identity/境界と独立した意味検査 | failed |
| 3 | seal_payload: payloadのprotected DACLを設定・読戻し | 一部だけ固定された可能性があるためunknown |
| 4 | rename_payload: 保持した同一物をno-replaceで名前確定 | 移動後の応答喪失を含むためunknown |
| 5 | verify_final: fresh bytes/identity、独立reader tokenのAccessCheckとsource/runtime再検査 | failed |
| 6 | commit_marker: pending markerからatomic no-replaceで完了印を確定 | 作成済みの可能性があるためcommit unknown |

`begin`が正常に返ってからadapterが操作する。`succeed`はadapterが成功を確認した場合だけ記録する。
例外の前後どちらで実mutationが発生したかモデルだけで証明できないため、mutation失敗は保守的にunknown。
途中失敗後の後続操作・同じattemptの再試行・cleanupは認めない。未着手slotをそのまま残す。
順序違反・二重開始・未開始の成功通知等のprotocol違反もstopをラッチし、例外を握り潰してcompleteへ戻せない。
最初の原因を保持し、後からresource stopがあれば別flagを昇格する。resource stop後の追加IOはadapter側で禁止する。

commit成功後のteardown失敗は「commit confirmed / model stopped」と記録する。
成功したcommitを未公開へ巻き戻さず、全体成功や再実行可能とも扱わない。
commit応答不明を後から通常の成功通知で確定することはできない。調査は別のread-only工程の責務。
全操作成功でもhandle/process teardownが成功するまではawaiting_teardownとし、completeを返さない。
teardownの実行・所有権管理をこのモデル自体が保証することはない。

状態slotは固定6個で、snapshotは毎回独立したdict/listを返す。生のpath/handle/SID/例外本文を保持しない。
trusted callerがprivate stateを書き換えることへの耐性や、OOM下でsnapshotを作れる保証はない。

## toy完了印

caller-ownedの小さなbytes集合から、source revision・path・byte count・raw hashのinventoryとそのhashを作る。
external marker digest、同じsource revision、fresh payload bytesから完了印全体を再構成し、raw bytesで照合する。
marker自己hashをinventoryへ含めず、field追加・重複JSON・再整形・自己申告の受入pass等をexact再構成で拒否する。
pathは既存のlexical validatorを使い、case aliasとfile/ancestor衝突を追加拒否する。
payloadは最大8 files、各64KiB/合計256KiB、path128文字、marker16KiB。bytes長を先に検査する。
上限はこのモデルへの入力範囲であり、全processや実campaignのメモリ上限ではない。

このmarkerは`s4-b2-model.1`のtoy形式で、既存S3 markerや科学schemaを置換しない。
hashの一致は意味検査・実行者認証ではない。内容とexternal pinを一緒に交換できるcallerの改竄を防ぐとは称しない。
journalのcallerによる成功通知もnative動作の証拠にはならない。
出力は常にnot_completed/formal_permission=false/execution_authenticated=false
（marker検証はsemantic_verification=not_performed）を明記する。

## native接続前に必要な残件

- B1/Windowsの残りの必須受入、正式OS条件との整合、runtime/source/tokenの固定。
- 新規fixtureだけを所有するadapter、実handleと名前の同一性、no-replace、DACLの順序・権限、全ordinary rightsの実確認。
- marker自体と親directoryの保護、markerの同一性と非上書き、競合・flush/close失敗・resource stopの実証跡。
- independently reconstructed semantics、consumerのfresh再読込、全inventoryと不明状態の検査。
- native試行の具体的な対象・停止条件・資源上限の確定。終了済みB1の試行枠は流用しない。

今回のモデルをproductionへ接続したり、mainへ統合したり、formal入口を開く段階ではない。
