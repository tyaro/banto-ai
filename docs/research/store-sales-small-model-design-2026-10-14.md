# 独自小型モデルの需要用途設計（2026-10-14）

## 問いと今回の範囲

過去数量と起点で計算できる暦から、同曜日平均28日を上回る14日予測を作れるか。独立初期化の小型モデルを一設定だけ学習する。TimesFM3の重み・教師出力・公式学習は使わず、同等再現や一般性能を主張しない。完成MetroPT学習は反復しない。

Store Salesの保存済み別都市snapshot、店舗5/11/12・BREAD/BAKERYを使う。実績salesを対象にし、潜在需要・菓子メーカーの箱数・販促因果効果・PSI採択は今回の結論にしない。2017は既に基準研究で読んだ期間なので、回顧探索であり未見確認ではない。

## 入力と分割

- context56日、patch7日、未来14日。3店舗を同一日付で束ね、CPU float32/batch最大8。
- 過去数量と観測mask。欠測を観測ゼロと区別し、欠測セルの数量tensorは0でもmask=falseとする。正規化統計はcontextの観測セルのみ。実ゼロと店舗12の60日連続ゼロは保持する。
- 暦5要素：曜日sin/cos、年内位相sin/cos（閏年の日数を使用）、過去2013–15資料で確認済みの名目8記念日の月日flag。過去と未来で同じ計算を使う。Transfer/Event、営業予定、将来販促実績・oil・transactionsは入力にしない。
- train labelは2013–15内、日次origin（最初2013-02-26、最後2015-12-18）。validationは2016-01-01+14*k、k=0..25。testは固定2017-01-01+14*k、k=0..15。各label期間がsplit境界を跨がない。contextは過去splitを跨いでよい。
- 14日labelに欠測があるoriginは3店舗共通で除外。context欠測はmask付きで許可。過去28日に同曜日観測が一つもない場合は予測不能として共通除外し、理由を保存する。2017基準が存在する16originは全て利用できることを入力準備で確認する。
- 店舗別固定尺度はtrain観測の平均数量、最低1。context標準偏差のfloorはその1%。validation/testで尺度をfitしない。origin後の実績は特徴へ渡さず、test label採点はcheckpoint選択後のみ。

## 構造と出力

既存独自モデルのBlock（D64/4heads/L2/FFN128、因果時間attention→系列attention→FFN）を再利用し、旧固定C128/H32モデルを変更しない。今回系列attentionはfull一構成だけ。系列ID embeddingは追加しない。

過去patchは数量7+mask7+暦35の49要素を64へ線形写像。8patchの後に未来14日暦70要素の投影＋learned horizon queryを加える。過去tokenは未来queryを見ず、queryは全過去を見る。固定sin/cos位置符号を使う。

過去28日同曜日平均を14日へ並べた数量bを参照する。T0=sum(b)、s=max(T0,0.01*14*train平均)。horizon stateの3出力から、総量Q10=s*softplus(a)、Q50=Q10+s*softplus(b)、Q90=Q50+s*softplus(c)とする。非負・順序を構造で保つ。head初期weight=0、biasは倍率0.8/0.2/0.2のinverse-softplus。T0=0時も小さな正の尺度から回復できるが、ゼロが休業か欠品かは判定しない。

日次配分はhorizon state＋各未来日の暦＋相対leadを共有70→32→1 headへ渡し、2*tanhの補正をlog(b_day+0.01*train平均)へ加えてsoftmax。最後の線形weight/biasは0初期化。日次point=総量Q50*配分。配分和1、日次point和は総量中央値に一致（float32丸め許容）。平滑化を含むため初期日次は既存基準の完全一致ではない。

総量分位点を直接学習し、日次分位点を足さない。日次point和の総量中央値整合性を保持するが、日次各値がそれぞれの周辺中央値とは主張しない。日次区間は出さない。総量名目80%は未校正の学習区間であり保証ではない。

## 学習・選択・評価

独立init seed20261014、batch sampler別seed20261015。256step/batch8、replacement、AdamW lr3e-4/betas(.9,.999)/eps1e-8/weight_decay.01/foreach=false/fused=false、grad norm1、dropout0、CPU2threads/interop1/deterministic。grid、別seed、延長、自動再試行なし。

loss=0.5*総量pinball（14*固定train平均で除算）+0.5*日次point MAE（固定train平均で除算）。全店舗・lead/quantile平均。validationも同式。step64/128/192/256でcheckpoint保存、validation最小を選択、同値は早いstep。testを見て選択・幅調整しない。

選択後16originを一回forward、日次MAE/WAPE/Bias、14日総量MAE/WAPE/Bias、総量pinball/coverage/幅/外れ方向を保存。店舗別も示す。既存mean28/暦配分の2017予測・実績を保存rootから再利用し、新モデルlabelと対応照合する。既存総量区間の48窓も再利用し、直接学習区間との幅・coverage比較は記述に留める。統計CI/勝者/実務採択/正式creditは出さない。

## 新しい機構確認と保存

今回に必要な少数確認：missingとzero/過去境界、label split、非負順序と総量整合、未来暦経路、総量loss、有限gradient。完成旧確認は再実行しない。

実行900秒/OS private2GiB/output1GiB/single32MiB/files32を維持。通常24file/768MiB、失敗8file/256MiBを予約。source/input/schedule/initial/4checkpoint/4prefix/test/journal/summary/closureを新rootへ保存。全stdout/stderr/exitは別EvidenceStore（16MiB512files/256KiBparts/失敗reserve2MiB16files）に保存。prepは128KiB16file。例外時に元例外・完成prefix・選択状態を保存して閉鎖し、同rootへ再試行しない。checkpoint上限はblocking中断/native全経路証明ではない。

公開原本・CSV・予測・fit・重みはlocalのみ。Gitは独自codeと集約文書だけ。formal_permission=false/credit0/登録holdout未読/native reader禁止。automation PAUSED、直接研究ACTIVE、追加agent0、CARE手動完了待ちを維持する。
