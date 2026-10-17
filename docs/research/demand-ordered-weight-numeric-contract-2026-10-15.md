# D1重み：固定数値契約と人工検証の範囲

2026-10-15 JST。実装・人工実行前の固定契約。Astra（gpt-6-astra）の数式レビューを反映。旧[第一設計](demand-ordered-persistence-design-2026-10-15.md)と[説明限定](demand-ordered-persistence-amendment-2026-10-15.md)を保持し、本契約で未決だった定数とraw encoderだけ具体化する。実データのr/fit/予測/2014評価/2015参照・再評価は起動しない。

## 定数と唯一の仕様

τ=Fraction(1,20)、τ²=1/400を全店・全季節共通に固定する。past56営業相当観測平均μを単位とした変化尺度0.05という工学的規約であり、前block比5%成長、通過閾値、最適値、信頼確率ではない。同方向・V0・支持s1・a=b=τならr=2/3。実データ分布/店13/特定日/既読Q1へ合わせた選択やτ探索はしない。

raw APIはschema/origin/recordsだけ、各recordはdate/available_at/valueだけ。originは2013–2014、56日窓の初日も2013-01-01以降。origin前56暦日を昇順・重複なしで厳密に要求する。available_atはdate+1暦日という既存仮定に一致しorigin以下。未来・未可用・余計なlabel字段・不正gridはエラーで、r0へ救済しない。営業予定unknownはunknownのまま、祝日全般を休業にしない。

valueは有限非負の厳密なint/float（bool不可）またはNone。binary64はexact Fractionへ変換し-0を0へ正規化。01-01/12-25だけを既存の休業相当日として扱う。実測0・None・休業相当の各数を保存し、営業相当0を平均とJに含める。欠測を特徴用0で補完しない。休業日のraw正値/0/Noneは保ちつつ特徴から外す。

全営業相当観測のμと曜日平均μ_wをexact Fractionで求める。観測なし/μ0/J空は理由付きr0。真0を小さい正数に置換しない。4×14blockの全4日が営業相当観測である共通位置J、s=|J|/14。z=(y−μ_w)/μ。各zだけをq=2^-32の**絶対格子**に最近接偶数丸めしzqとする（相対32bitではない）。以後L_b=mean_J(zq)、d1..3、a=d3、b=(d1+d2)/2、V=mean_(4×J)((zq−L_b)²)をexact Fractionで順に計算。

```text
r_raw = s * 2*max(a*b,0) / (a²+b²+V+1/400)
r_stored = nearest_even_grid(r_raw, 2^-32)
new_x = exact_fraction(old_x) * r_stored  # 切片を含む3特徴
```

nearest-evenは整数divmodで実装し、負のtieも同じ規則を使う。各z誤差≤q/2、そこからa/b誤差≤q。保存するr誤差≤q/2は量子化済みzからのr_rawとの比較であり、生rawの丸めなしD1との差ではない。ほかの中間量/特徴積は丸めない。

N≤56と非負入力よりexact |z|≤56、丸め後|zq|≤56+q/2、|a|,|b|≤M=112+q。非空J、V≥0から s−r_raw≥(1/14)(1/400)/(2M²+1/400)>61(q/2)。最終丸め後も0≤r_stored≤s≤1を保証し、保存前にも検査する。clampで救済しない。無制限scalarのa/bにはこの証明を適用しない。

既存tools/demand_bounded_metrics.pyのArithmetic（8192bit、交差約分、積の事前bit検査、和/約分前積/約分後分子分母検査）をそのまま再利用する。最大bit数を保存。超過はBoundFailureで停止し、r0へ置換しない。値妥当性と算術受入可能性は別。モデル/solverをimportしない。入力pinは妥当性・算術検査後のcanonical packetに対し作る。失敗入力を巨大文字列へ変換して救済しない。

project_pastはoriginを先に検査し、wide recordsのdate metadataで窓を選んだ後に必要3字段だけをコピーする。窓外のvalue、選択行の余計なlabelを参照/数値変換/deepcopyしない。strict raw入口の未来拒否とadapterの未来非選択は別canaryで確認する。これは関数境界でありOS sandbox/本物prefix統合の証明ではない。

旧特徴NoneはNoneのまま。旧適格行のr0は[0,0,0]で元E/nE・complete I/nIから落とさない。raw時点検査は旧特徴Noneでも省略しない。old_xは先頭1の有限3数値に限定し、負の他2特徴は許す。B/日別mask/labelをencoderへ渡さず、同休業mean28と採点母数を変えない。r0と旧不支持、算術failureを区別する。

## 人工検証・有限終了

横ばい/持続/最新反転/単発/曜日だけ/実測0/全0/全欠測/J空/weekday平均0、元日・12/25・それ以外の祝日、positive/subnormal/maxfinite/-0、正負tie、非有限/負/bool/bit超過、未来可用性/重複/順序/余計字段/2015拒否、future/label canary、旧E/I分母保存、観測のみと欠測0仮定の分離を人工fixtureだけで試験。独立readerは新encoder/solverをimportせずFractionと独自丸めで全保存中間量を再計算する。入力改変なしも確認する。

各単位親900秒/子870秒、sampled Mac footprint/peak RSS各2GiB。既存artifact normal24files768MiB/total32files1GiB/single32MiB/failure8files256MiB、EvidenceStore16MiB512files/part256KiB/failure2MiB16filesを維持。今回は人工結果もEvidenceStoreのみで、モデルartifactを生成しない。stdio/exit/source/input/state/result/resource/closureと失敗を保持。閉鎖済みroot/sourceを書換えない。失敗時はそのrootを閉鎖して次版を別名で保存する。

人工終了後もfit_ready=false。次工程は別のprefix統合/構造支持・energy集中/rank監査契約であり、実データrやfitへ自動接続しない。調整2014以前、四季平均under/over非増加とMSE条件、同休業mean28、観測/欠測0仮定の分離を維持する。2015停止・heartbeat PAUSED、固定分類/店番号/特定日の特例/採用なし。Windows native・OS依存包括suiteは別で今回未実行。
