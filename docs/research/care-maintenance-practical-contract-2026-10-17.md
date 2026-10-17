# CARE-A-MAINT-PRACTICAL-20261017 — 保全の実用性評価と基盤モデル比較の契約

2026-10-17 JST。人が決めた方針（先行時間と誤警報は複数で報告し基準は後で決める、TimesFM 3・Chronos-2・Toto 2の3つを比べる、CARE testは開発材料として使う）に沿い、実行より前に固定する。機械可読版は[実用性評価契約](../../examples/configs/care-a-maintenance-practical-20261017.json)。

元の[CARE保全契約](care-a-maintenance-contract-2026-10-16.md)（CARE-A-MAINT-20261016-r1。機械設定のsha256 `f199f0f4…0cf1`、本文 `6aca0b81…743d`）の条件はすべてそのまま使う。変えないものは次のとおり。
- split・時点（利用可能時刻＝記録時刻＋600秒）
- 共通支持の定義（校正ではstatus0を含む）
- 校正の512件以上・70%/30%の区分
- score・閾値・警報の開閉
- 主hit・誤警報の数え方
- native支持のbaseline

この契約は、先行時間別の集計、誤警報の換算、基盤モデルの追加だけを定める。

## データの位置づけ

CARE testは既に読まれている。自作モデルのevent別の検知・先行時間も[保存済み](../results/care-macos-learning-evaluation-2026-10-16.md)である。したがってこの比較は**未知のholdoutではなく、開発材料での評価**として記録し、業務での合否や本番採用の根拠にしない。

基盤モデルの設定（context 128行、p50、99.5%の閾値、adapterの既定）は、元契約と既存adapterからそのまま取った。保存済みのevent別結果を見て選んだものではない。

既存の自作モデルとbaselineは、保存済みの予測・警報をそのまま使う。閾値・持続・checkpointは調整し直さない。

基盤モデルの推論と方法別の閾値の校正は、parameterを更新しないので学習ではない。R0.2の「正式R2以外の実データ学習は停止」はそのまま維持する。

## 比べるもの

| 方法 | 内容 |
| --- | --- |
| 自作モデル | 保存済みのSmallForecaster（5fold）の予測・閾値・警報。再学習・再推論しない |
| baseline | 保存済みの負荷bin別温度中央値（共通支持とnative支持） |
| TimesFM 3 | google/timesfm-3.0-pytorch（固定revision）。非商用の研究用途 |
| Chronos-2 | amazon/chronos-2（固定revision）、Apache-2.0 |
| Toto 2.0 4M | Datadog/Toto-2.0-4m（固定revision）、Apache-2.0 |

TimesFM 3の重みのライセンスは商用の意思決定を除外する。そのため、TimesFMの結果は研究上の参考に留め、人が後で決める基準や採用の判断には使わない。

## 基盤モデルの手順

学習・fine-tuningはしない（zero-shot）。既存adapter（`src/banto_ai/adapters/`）と固定package version・checkpoint revisionを使う。

- **入力**：
  - CARE側は`care_input.Consumer`を通す（過去だけのcontext、正解を見ない検査つき）。元契約の真値の分離をそのまま引き継ぐ。
  - 各origin nの過去128row `[n−128,n)` の3信号を元単位で渡す。
  - adapterが求める時刻は、固定の基準時刻（2000-01-01T00:00:00Z）にfile内の秒offsetを足して作る。間隔は600秒。3モデルともcalendar特徴を使わないので、この写像は結果に影響しない。
- **信号の役割**：
  - TimesFM・Chronosは、2温度を予測対象、powerを過去だけの共変量とする（未来の共変量なし）。
  - Totoは3信号すべてを変量とする。powerも予測されるが、使うのは2温度だけ。
  - いずれもadapterの既定どおり。主な既定は次のとおり。
    - TimesFM：`use_znorm=False`、`padding_mode="none"`、`univariate=False`
    - Chronos：`cross_learning=False`
    - Toto：128行はちょうど4 patchなので、paddingや欠測maskは入らない
- **要求**：horizon 1、分位点はp50だけ。警報に使うのはlead1のp50で、元契約と同じ。
- **支持**：自作モデルと同じ共通支持の行だけを予測する。
- **score**：元契約と同じ`max(abs(y−p50)/R)`（2温度）。Rは各foldの学習だけから求めたMAD×1.4826で、閉じたfold rootの`input.json`の`profile.alarm_scales[v].R64`を読む。計算し直さず、全方法で同じ値を使う。
- **校正**：foldごとに元契約と同じ校正区間（validation anchorのprefix後半30%）でscoreを計算する。閾値は方法別に99.5%点、警報の開閉も元契約と同じ。校正scoreが512件未満になったら閾値を作らずに止める（元契約と同じ下限）。

## 失敗の扱い

**行の非支持**：adapterが行単位の`ValueError`（出力の非有限値など）を出した行は、その方法の非支持として記録し、別の値で埋めない。
- 非支持の行は、警報では元契約の欠測と同じに扱う。開いている警報を閉じ、連続数を数え直す。誤警報の分母（eligibleな時間）からも外れる。これは元契約のgapと同じ扱いで、意図したものである。
- 方法別・fold別の非支持数を報告する。
- ある方法のあるfoldで非支持が1%を超えたら、採否の前に止めて原因を調べる。

**実行の停止**：それ以外の失敗（モデルの読み込み失敗、process異常終了、メモリ・時間の超過）は停止として扱う。
- 実行ツールだけを直して、その単位を実行し直せる。
- 結果を見た後に、入力・context長・閾値・支持条件を変えない。

## 指標と集計

元契約の主指標と、実数・pooled・event別・asset別・支持をすべて報告する。主指標は次の4つ。
- asset macroの検知率
- 正常1000 record-hour当たりの誤警報
- 正常の警報時間割合
- miss込みearliness

加えて次を報告する。

- **先行時間別の検知**：W＝0・24・72・168時間（file内の利用可能時刻でW×3600秒）。
  - 主hit（推定異常期間内で最初に新しく開いた警報）が「期間の終わりの利用可能時刻−W」以前に開いたeventだけを、Wでの検知と数える。
  - W＝0は元契約の主hitと同じ。
  - 期間開始前から続いている警報は、どのWでも検知に数えない（元契約どおり別表）。期間内の2番目以降の警報も数えない。
  - 期間の長さがWより短いeventは、Wでは検知できない。event表に「Wで検知可能か」を付け、その未検知を検知の失敗と読まないようにする。
  - 期間の終わりは実際の故障時刻と保証されないので、先行時間は代理値である。
- **誤警報の換算**：正常1000 record-hour当たりの率に加え、asset・30日（720 record-hour）当たりの件数を示す。この件数は率からの換算値で、asset別とpooledの両方を出す。正常の時間が720時間に満たないassetもある。
- **event別の対比**：方法ごとに、検知の有無・OPEN時刻・先行時間・Wで検知可能かをevent単位で並べる。anomalyは12件しかないため、差の有意性は主張しない。

必要な先行時間と許容する誤警報の基準は、この比較の結果を見てから人が決める。今回は合否を出さない。

## 実行の単位と資源

- **環境**：基盤モデル用の別Python環境を作り、package versionと、downloadしたcheckpointのrevision・hashを記録する。
- **単位**：fold・区間（校正・test）・方法ごとに、originを固定した大きさ（1,000行）の塊に分けて推論する。1単位は子870秒・親900秒以内。各塊の出力は閉じて保存し、途中から再開できる。adapterは1行ずつ推論するので、batch推論はしない。
- **並列**：互いに独立な単位を、同時に最大3 processまで並べてよい（4コア）。
- **メモリ**：1 processあたり、TimesFMは4GiB、他は2GiB（人が承認）。
- **全体の上限**：経過時間で24時間。1行あたりの実測は、Totoが約0.02秒、Chronosが約0.12秒、TimesFMが約0.37秒。合計約11.9万行で、TimesFMは逐次なら約12時間かかる。
- **固定と採点**：全方法・全foldの予測・score・閾値・警報を保存し、hashを付けて固定する。その後に、評価者だけがlabelを読んで全方法を採点する（元契約と同じ順序）。採点では、まず保存済みの自作モデルとbaselineの指標が保存値と一致することを確かめる。
- **保存物**：CARE由来の入力・予測・labelは公開リポジトリに入れない（gitignoreの`artifacts/`）。リポジトリにはhashと集計だけを残す。
- **範囲外**：より長いcontext、共変量の別の扱い、fine-tuning、公式CARE score。

## 受け取った保存物

Macから受け取ったfold0〜4の学習結果の閉包hashは、保存済みの固定記録（`care-learning-scores-20261016/freeze-before-truth.json`）と5件とも一致した。このほか、評価者のlabel、採点結果、split manifest、学習の実行許可も受け取った。いずれもgitignoreの`artifacts/`にあり、閉包記録と全件一致する。hashは機械可読版に記録した。
