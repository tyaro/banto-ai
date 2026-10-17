# MetroPT Mac M0 — 複数日入力・最小接続の実装結果

2026-10-16 JST。人の「計画に沿って進める」を受け、[固定仕様MPT-MAC-20261016-r2](../research/metropt-macos-multiday-protocol-2026-10-16.md)のM0を実施した。途中で回答された産業用途の第一優先は**保全・点検支援（異常の予兆）**として上位計画へ反映する。今回の予測接続を、異常予兆の有効性へ読み替えない。

## 結果と範囲

| 項目 | 結果 |
| --- | --- |
| 固定対象 | 既定13日、TP3/Oil_temperature/Motor_current。日付・信号・窓数・recipe・評価条件の変更なし |
| 原本変換 | 1,516,948 timestamp行を確認し、指定日の113,311行×3信号＝339,933数量をdecode。各信号18,720個の1分値をfloat32で保存 |
| 品質 | raw欠測/nonfinite0、empty bin0、補間0、日付差替え0。選定日内最大raw gap11秒。正常運転や無故障の認定ではない |
| 共通支持 | train8,967、validation123、test123。全候補を保持。日を跨がず、既定分母/90%条件を維持 |
| train尺度 | 各信号7日×1,440＝10,080 binを一度ずつ集計。float64計算→有限正のT/floor float32をpin。独立population計算と整合 |
| 最小接続 | 最初のtrain origin 2020-02-03 02:08だけ。C128入力[1,3,128]、label形[1,3,32]、予測[1,3,32,3]。full/self-only各1回の未学習forwardで有限値・分位点順序pass |
| モデル/乱数 | 各109,024 parameters、共有初期state。3固定samplerseedごとの4096×8 scheduleを保存。学習更新は0 |
| 新しい検証 | 接続時10項目、別のguard/集計試験6件がpass。異なる日の支持数でも日等重み、interval端点、未完campaign拒否、明示再開なしの起動拒否を含む |
| 独立読戻し | データと実行の6closed rootsのhash/サイズを検査。原本の最初・context境界・日末の12 bin-target平均は保存float32と厳密一致 |

学習、loss/backward/optimizer更新、validation/testのモデル予測、実データ性能採点、2015参照再評価は0。6試験内の集計値は人工値だけであり、研究の成績ではない。数量準備ではtest日も品質確認・変換したが、学習口には渡さず、test labelの性能利用は行っていない。

## 実装と保存物

- [厳格converter](../../tools/public-data/prepare_metropt_multiday.py) → [入力root](../../artifacts/public-datasets/metropt3-multiday-macos-20261016/summary.json)。train/validation/testのlittle-endian float32を別ファイルにし、配置は[day,target,minute]。旧単日14信号のcanonical importer/adapterを変更しない。
- [複数日adapter/数値契約](../../models/mini-transformer/metropt_multiday.py) → 固定config/calendar/model pin、日内窓、共通支持、train-only尺度、sampler、baseline、日等重みpinball。test readerはcontextのみを公開し、通常のtargets呼出しを拒否する。
- [M0接続](../../models/mini-transformer/metropt_multiday_connect.py) → [接続結果](../../artifacts/metropt-m0-connect-20261016/summary.json)、[境界確認](../../artifacts/metropt-m0-connect-20261016/checks.json)、[初期state配置](../../artifacts/metropt-m0-connect-20261016/initial-layout.json)、[neutral初期state](../../artifacts/metropt-m0-connect-20261016/initial-portable.bin)、[forward参照](../../artifacts/metropt-m0-connect-20261016/forward-reference.json)。
- [paired trainer](../../models/mini-transformer/metropt_multiday_run.py)、[分離scorer](../../models/mini-transformer/metropt_multiday_score.py)、[seed-slot入口](../../models/mini-transformer/metropt_multiday_slot.py)を実装。import/設定読取りだけではTorch読込や学習を始めない。実行には当該phaseの明示再開記録を要求する。これは研究scopeの誤起動防止で、OS認証境界ではない。
- [新guard試験](../../models/mini-transformer/test_metropt_multiday_contract.py) → [6件の結果](../../artifacts/metropt-m0-guards-20261016/checks.json)。[独立読戻し](../../tools/public-data/check_metropt_multiday_m0.py) → [読戻し結果](../../artifacts/metropt-m0-readback-20261016/summary.json)。

trainerは同一初期stateとbatch列でfull/self-onlyを4096回更新し、4val時点から選ぶ実装。scorerは3seed全てのcomplete closure、同source/input、選択state、全test予測、同一baselineを検査し、freeze記録を保存してからtest targetを読む。best seed選択はない。**今回この学習から採点までの経路自体を実行して成功確認したわけではない。** 新コードの構文・import・拒否条件・人工集計を確認した段階であり、実学習時の勾配/optimizer/checkpoint再開・所要時間は未確認。

## 次に起動する際の手順と上限

1. M1実学習・評価の再開が明示された場合に限り、その指示・phase・固定config hashを実行記録に保存する。古い設定JSONのfalseをtrueへ書き換えて許可の代用にはしない。
2. `macos_industrial_run_v2.py`を親にして`metropt_multiday_slot.py`を1seedずつ起動し、順番は20261016→17→18。fresh campaign/seed rootを使い、直前のexit/complete closureが不成立なら残りを起動しない。
3. 第3slotは全seed予測のfreeze後の一括採点までを**同じ子870秒枠内**で行う。採点用の第4親unitを追加しない。内部helperの時計が別でも、外側の監視でslot全体を制限する。
4. 各親900秒/子870秒、Mac physical footprintとpeak RSS各2GiB、最大3親unit/計2700秒。slotは親の終了通知を例外として受け、可能な共通prefix/partial stateと元エラーを保存して閉じる。上限・nonfinite・未完はcampaign incompleteで、追加seed/延長/差替えによる救済なし。

全stdio/exitと親側資源記録は、[変換記録](../../artifacts/metropt-multiday-prepare-20261016-records/exit.json)、[接続記録](../../artifacts/metropt-m0-connect-20261016-records/exit.json)、[guard記録](../../artifacts/metropt-m0-guards-20261016-records/exit.json)、[読戻し記録](../../artifacts/metropt-m0-readback-20261016-records/exit.json)。全てexit0。最長親観測5.709秒、最大親観測child footprint248,677,192B、最大child peak RSS305,741,824Bで上限内。checkpoint観測とOS hard capは同一視しない。

各artifactはnormal24file/768MiB・single32MiB以内。全体32file/1GiBと失敗reserve8file/256MiB、Evidence16MiB/512file・part256KiB・失敗reserve2MiB/16file、stdout1MiB/stderr128KiBを維持する。新source・実行時source snapshot・失敗保存口・closureを用意し、旧root/原本/失敗/既存変更を上書き・削除していない。

## Rust・保全用途・次工程

Rust比較用の初期stateはdtype/shape/byte offset/parameter-or-buffer/各tensor hash付きで、独立unpackにより全値の厳密一致を確認した。共通contextからのfull/self-only未学習出力も保存。最終のRust学習実装、backend選定、optimizer/再開形式、banto接続受入は未実施。今回の`.pt`はPython参照の保存形式であり、Rust学習への移植完了を意味しない。

M0は完了し、次の有限学習工程M1は再開待ち。保全・点検支援が第一優先になったため、M1の勝敗だけで異常予兆を判断せず、次の用途契約はCAREを優先する。版/利用条件・sensor/asset・時点とlabel・運転状態別baselineを先に決め、event単位の検知率・誤警報・先行時間を評価する。油圧/XJTUの全実験終了をCARE契約の前提にしない。

需要は別の本線として、調整2014以前・同休業mean28・四季の過小量/過大量非増加と既存MSE条件・観測のみ/休業相当欠測だけ0仮定の分離を維持。実学習と2015再評価停止、heartbeat PAUSED、正式holdout等の境界を保持。Mac共通経路の今回結果と、Windows native/OS依存suite未実行を分けて報告する。新依存/Rust実装/新取得/外部送信/commit-push/本番採用/追加agentなし。
