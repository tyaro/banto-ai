# 共有学習用の店舗選定と数量支持診断（2026-10-14）

[入力契約](../research/store-sales-shared-series-input-contract-2026-10-14.md)を数量読取り前に保存。metadata選定→新train側snapshot→支持診断だけを実施。新fit/モデル/2016label読取りは行っていない。次は[共有残差一候補の未実行設計](../research/store-sales-shared-residual-design-2026-10-14.md)。

## 数量を使わない選定

stores.csv54店舗の保存pinを照合。既使用1/2/3/5/11/12を除外し、残りID昇順で4の倍数の先頭6を検証、それ以外の先頭18を学習、残り24を予約した。familyはBREAD/BAKERY。数量/残差/販促による選別0。共有都市Guayaquil/Quito/Santo Domingoあり、新都市の検証とはしない。便宜標本。

学習18：6,7,9,10,13,14,15,17,18,19,21,22,23,25,26,27,29,30。
fit未使用の検証6：4,8,16,20,24,28。予約31〜54は数量未読。

## 新snapshotと支持

元ZIP/memberのSHA/bytes/3000888行をstream照合し、対象24store/family/2013–15だけsalesを数値化。26280暦行、観測26208、欠落72（各store/年Dec25）、同じ欠測・実ゼロを区別した。onpromotion/2016/17/予約群/旧6storeの数量は数値解析しない。原archive・既存snapshot変更0。検証6のprefixは履歴/尺度の可用性確認にのみ使い、モデルfitには使っていない。

各storeの71適格窓を保存。context56日49以上/label14全観測/28日各曜日3以上で判定、値の大小や残差では選別しない。最低10適格窓・10正値日の支持は学習18全部でpass。ただし最低支持は精度や営業状態の合格を意味しない。

|店舗|群|正値日|記録ゼロ日|適格窓|14日label全ゼロ窓|
|---|---|---:|---:|---:|---:|
|10|train|1089|3|71|0|
|13|train|1089|3|71|0|
|14|train|1051|41|71|2|
|15|train|1089|3|71|0|
|16|validation_prefix_only|1089|3|71|0|
|17|train|1089|3|71|0|
|18|train|1089|3|71|0|
|19|train|1089|3|71|0|
|20|validation_prefix_only|321|771|71|49|
|21|train|160|932|71|60|
|22|train|83|1009|71|66|
|23|train|1089|3|71|0|
|24|validation_prefix_only|988|104|71|6|
|25|train|1092|0|71|0|
|26|train|1089|3|71|0|
|27|train|1089|3|71|0|
|28|validation_prefix_only|1089|3|71|0|
|29|train|286|806|71|51|
|30|train|1066|26|71|1|
|4|validation_prefix_only|1089|3|71|0|
|6|train|1089|3|71|0|
|7|train|1089|3|71|0|
|8|validation_prefix_only|1089|3|71|0|
|9|train|1089|3|71|0|

学習21/22/29と検証20には長いゼロ履歴がある。記録の原因は未開店/休業/欠品等と同定しない。全ゼロlabelを除去せず保存した。次の共有fitは店舗等重みとし、検証はorigin前の正値支持あり/なしも分けて記述する設計。検証店舗の過去統計を使うため「情報を全く見ていない店舗」とはしない。

14日以上のゼロ連続区間の原保存記述：

- 店14: 2014-08-04〜2014-09-10（38日）
- 店20: 2013-01-01〜2013-12-24（358日）; 2013-12-26〜2014-12-24（364日）; 2014-12-26〜2015-02-12（49日）
- 店21: 2013-01-01〜2013-12-24（358日）; 2013-12-26〜2014-12-24（364日）; 2014-12-26〜2015-07-23（210日）
- 店22: 2013-01-01〜2013-12-24（358日）; 2013-12-26〜2014-12-24（364日）; 2014-12-26〜2015-10-08（287日）
- 店24: 2014-04-14〜2014-07-23（101日）
- 店29: 2013-01-01〜2013-12-24（358日）; 2013-12-26〜2014-12-24（364日）; 2014-12-26〜2015-03-19（84日）
- 店30: 2013-07-08〜2013-07-30（23日）

snapshot 776915B/SHAb7805b258cb6e7a268b3b3289ac1b9688bd54cf03e1f06b01f8e74172fdeddc4。診断5.055342秒/OSpeak22024192B、CPython3.14.0/Windows、Torch/weights未使用。

## 保存と次の未完成unit

metadata/shared-prefixと各prep/launch全閉鎖、script/入力契約/source全文/metadata/原ID付きsnapshot/観測mask/支持ledger/summary/原stdout-stderr/exit0を保存した。新数量支持の検査をコード全体の回帰試験成功にしない。旧zero_runsの不変関数を新storeの新数量へ使い、旧評価/確認/CIは反復していない。literal globのforeground読取り失敗はselected tool excerptとして保存し、helper/model/nativeの失敗へしない。

次は共有残差の固定設計に対応する純粋入力・店舗等重みfit・検証分離の新少数確認。新fitと2016数量読取りはその後、共有係数の保存後だけ固定25起点×6storeを一回検証する。2017、係数grid、別seed、未来販促は使わない。独自NNの新共有namespaceはまだ未実装。

direct ACTIVE/automation PAUSED、CARE手動報告待ち/自動確認0、追加agent0、旧closedroot不変。Gitは独自codeと集約文書だけ、原数量/ledger/尺度値/fitを送信しない。実行900秒2GiB/output1GiB/single32MiB/files32、記録16MiB512files/256KiBparts/reserve2MiB16files、prep128KiB16files維持。formal_permission=false/credit0/登録holdout未読/native reader禁止/正式受入未完了。本文shared-series-doc-records、Git後shared-series-git-records post-save優先。
