# MetroPT複数日比較 — 固定詳細仕様 MPT-MAC-20261016-r2

2026-10-16 JST。[上位計画](timesfm-inspired-practical-evaluation-plan-2026-10-16.md)に従うM0/M1の詳細。人の「計画に沿って行うことを明記し、計画の詳細を詰める」に対応する。[設定JSON](../../examples/configs/metropt-macos-multiday-20261016.json)と本書を一組の契約とし、不一致があれば実行を止めて実行前に訂正する。計画の存在は停止中の学習・推論・採点を再開する許可ではない。

## M1の完了状態（固定条件は不変）

人の明示再開指示により[3seed実学習・評価](../results/metropt-macos-m1-2026-10-16.md)を完了した。全6構成各4096更新・4選択時点、全test予測freeze後採点、3親unit上限を遵守。事前仮説・新しいphase許可は[実行前記録](../../artifacts/metropt-m1-20261016-authorization/prescore-contract.json)に保存した。固定config/manifest/model sourceを変更していない。全文書中のM0/再開待ち/未実施は各時点の経過で、現状は結果報告と本節を優先する。学習の中断再開・Rust実装やCAREイベント検知の成功まで確認したものではない。

## M0の現在状態（実行条件の変更なし）

人の「計画に沿って進める」により、[M0実装・数量品質・最小接続を完了](../results/metropt-macos-m0-2026-10-16.md)。固定13日/3信号を厳格変換し全8,967/123/123窓を維持。Macの未学習forwardはfull/self各1回、境界10項目と新guard6件・独立読戻しがpass。科学的な比較条件と固定JSON/manifestは不変。JSONのstatus/authorizationは凍結時の記録で、今回の許可は別のM0 phase記録に限定する。実学習とvalidation/testのモデル予測・性能採点・2015再評価は未開始。本文中の「未実施」は仕様凍結時の履歴で、現在状態は本節と結果報告を優先する。

paired trainer/分離scorer/seed-slotを実装したが、実データの勾配/optimizer/保存再開の成功はまだ確認していない。M1再開時は既存の親監視下で1seedずつ、第3slotの一括採点も同じ870秒枠内に含め、3親unit上限を守る。人の用途回答は保全・点検支援（異常の予兆）であり、次の用途契約はCAREを優先する。

## 上位目的へのRust追加（比較契約は不変）

人の追加指示により、最終的に学習・推論をRustへ移植し、bantoから使いやすいlibrary API/CLIとモデル管理へ接続することも目的とする。[上位計画のR0〜R4](timesfm-inspired-practical-evaluation-plan-2026-10-16.md#7-最終実装--学習も含めたrust移植とbanto統合)を参照。Python参照の構造/recipe/state/sampling/前処理を明示して移植に活かす。本MPT-MAC-20261016-r2の対象・日付・学習条件・集計・設定JSON・manifest・停止状態は変更しない。Rust実装や実データ学習を今回開始したという意味ではなく、先のAstraレビューをRust追補への確認済みとはしない。

## 1. 遵守する目的と今回の範囲

**今後は上位計画と本詳細仕様に沿って進める。目的・対象・期間・指標を、実装や結果に合わせて黙って変更しない。** 主問は、TimesFM3の公開構造を参考に独立学習する自作モデルが、産業と需要予測・PSIにどの追加価値を持つか。mean28やQPの改善、人工境界試験の完了へ主目的を置き換えない。

各作業の開始記録へPlan ID/revision、工程、問い、固定入力、成果物、中止点を記載する。変更は理由・影響・既読情報・旧新差分を実行前に保存し、旧source・失敗・closed rootsを保持する。testを見た後の修正は同じ評価の救済ではなく、既読評価に基づく新候補として扱う。人の最新指示が優先する。固定契約内の通常実装は反復確認を要しないが、停止中の実学習・2015再評価や未許可領域へ自動拡張しない。

今回は文書・設定の固定と、その前提に必要なtimestamp-only監査2件まで。センサー数量decode、モデルforward、学習、solver、性能採点、2015参照再評価は0。heartbeat PAUSEDを維持する。M0の実行sourceはまだ未実装であり、`can_launch_learning=false`。

## 2. 期間改訂の理由と証拠

元案はtrain [2020-02-01,03-01)、validation [03-01,03-08)、test [03-08,03-15)だった。[初回日時監査](../../artifacts/metropt-multiday-timestamp-20261016/summary.json)では空の1分binが9,275、60秒超gapの影響binが9,401、最大gap100,981秒。候補に対する日時適格窓はtrain31,629/41,601、validation212/315、test233/315で、日ごとの90%条件は不成立。監査自体は正常終了したが、この連続期間案は採用しない。既存rootを閉鎖状態のまま残す。

数量・誤差を見ず、取得済み全原本のtimestampだけで「各日1,440個の1分binがすべて非空、同一日内の連続raw timestamp差が60秒以下」を満たす日を一度列挙した。global重複・逆行は0を要求。既読2020-02-21を除き、時系列順で最初の13日を7/3/3へ割り当てる規則を走査前に保存した。日を跨ぐgapを架空の連続時系列へ接続しない。

[第二監査](../../artifacts/metropt-complete-days-timestamp-20261016/summary.json)は1,516,948行のtimestampを走査し、適格30日から次を確定した。sourceは2020-02-01 00:00:00〜09-01 03:59:50。センサー文字列は数量へ変換していない。原本SHAは設定JSONにpin済み。

| split | 固定日（すべて2020年、時系列順） | 候補窓 | 日ごとの90%下限 |
| --- | --- | ---: | ---: |
| train | 02-03、02-04、02-15、02-16、02-18、02-22、02-25 | 7×1,281 = 8,967 | 1,153/1,281 |
| validation | 03-08、03-18、03-22 | 3×41 = 123 | 37/41 |
| test | 03-23、03-25、03-26 | 3×41 = 123 | 37/41 |

13日確定後に数量不良が分かっても別日と差し替えない。変換失敗として閉じる。初めから13日に足りない場合も停止する規則だった。成績で対象を圧力だけへ絞らない。

「完全日」は**timestamp上の適格性**だけを意味する。数量の完全性・正常運転・無故障を意味しない。評価日を含む全期間の取得可用性で選んだ回顧的標本であり、欠測を含む連続運用や一般的な故障期間の性能は主張しない。日付の過去利用履歴を全面認証したわけでもなく、未知holdoutと呼ばない。

## 3. 時点・数量変換・共通支持

source-naiveを研究上UTC解釈し、実設備のtimezoneを確認したとはしない。各日を独立segmentとし、raw時刻`[日開始+i分, 日開始+(i+1)分)`をbin iとする。平均をbin終了時に利用できる仮定で、実際の転送・確定遅延は未検証。

日内origin nではcontext `[n−128,n)`、label `[n,n+32)`。発行時刻は日開始+n分で、bin-endならcontext `(o−128分,o]`、未来 `(o,o+32分]`。n=128〜1,408 inclusive。train stride1、validation/test stride32、後者n=128+32k（k=0〜40）。評価日の先頭128分はcontext専用。labelは重ならず、contextは重なる。context/labelとも日を跨がず、split間も繋がない。後のtest発行時に既に観測されたtest内の過去をcontextへ使ってよいが、学習・選択へ戻さない。

[候補窓manifest](../../artifacts/metropt-complete-days-timestamp-20261016/calendar-windows.jsonl)の全行とhashを固定する。90%の分母を除外後の窓数へ縮めない。1店/1信号だけ残すのではなく3target・両構成・baselineの共通支持を使う。

新adapterは原本の選定日とTP3、Oil_temperature、Motor_currentの3列だけを数量変換する。旧14信号・単日canonical importer/sourceは変更しない。各raw値をfloat64へparseし、有限性を確認、全観測値を`math.fsum/count`で平均しfloat32へ丸めて保存する。float32 overflowも失敗。raw欠測/nonfinite、empty bin、同日60秒超gap、重複/逆行、集約nonfiniteは**変換全体を失敗**させる。finite値だけの平均、補間、欠測の0補完、数量不良後の日付変更は禁止。

変換済みqualityが不正な窓を共通除外するadapter guardと、raw変換失敗は別。日ごとの90%は前者の最低運用条件であって、raw失敗の救済許可や統計的十分性ではない。今回timestamp支持は100%だが、数量品質は未確認。元の14信号importとの数値再現も認定しない。

## 4. 数値・学習・選択条件

| 項目 | 固定値 |
| --- | --- |
| 対象順 | tp3/bar、oil_temperature/℃、motor_current/A |
| 構造 | 既存SmallForecaster、各109,024 parameters。V3/C128/H32/P32、D64、2blocks、4heads、FF128、LayerNorm eps1e−5、dropout0、q=.1/.5/.9 |
| 対照 | full / self-only。系列maskだけ変更。同じ登録parameter数を同じ実効容量と解釈しない。self-onlyのQ/K退化も開示 |
| 初期seed | 20261016、20261017、20261018 |
| sampler seed | 対応して20262016、20262017、20262018。初期化乱数と独立 |
| 実行 | Python3.14.8、既存Torch、CPU float32、threads2/interop1、deterministic algorithms有効 |
| sampling | local `random.Random(seed)`でdayを`randrange(7)`、そのday内の昇順共通originを`randrange(len(origins))`。各sampleでこの2回、置換抽出。batch8×4096=32,768個のscheduleを先保存し両構成で共有 |
| optimizer | AdamW lr3e−4、betas(.9,.999)、eps1e−8、weight_decay .01、foreach=false、fused=false。各構成は独立の空optimizer state |
| 更新 | 両構成共通4096回。global grad norm clip1、nonfinite時はstep前停止。scheduler/early stop/gridなし |
| 学習loss | 既存`training_loss`を維持。context-only平均/scaleで正規化したlabelと予測の平均pinball、float32。選択指標とは区別 |
| val選択 | 512/1024/2048/4096の4時点だけ。日・target等重みの固定train尺度pinball最小。厳密同値は早い時点、epsilonで同値範囲を広げない |

各targetのtrain尺度は7日×1440=10,080 binを一度ずつ数える。重複学習窓やsampler回数で重み付けしない。保存float32値をfloat64へ戻し、日付/分の昇順に`mean=fsum(x)/N`、`var=fsum((x−mean)^2)/N`、sigma=sqrt(var)。T=max(sigma,1e−5 native)、context floor=max(.01sigma,1e−5 native)。平均・分散・sigmaは有限、T/floorはfloat64計算時とfloat32化後の両方で有限・正を必須とする。全scalarのfloat64値、Tensorへ渡すfloat32丸め値をpinし、選択/報告は後者をfloat64へ戻して使う。

この集約精度と順序は旧float32標準偏差からの明示的変更。旧報告の数値再現と呼ばない。forward内のcontext平均・population std（correction=0）は既存Torch float32のまま。未来labelはforwardへ渡さずloss側だけで処理する。`Forecast.mean`はcontext正規化平均であり、将来期待値ではない。

各seedでfullを一度初期化しstateを保存、self-onlyへ同stateをloadする。非persistent系列maskはそれぞれの指定を維持。schedule、初期state、optimizer初期条件が共通であることをpinする。検証/評価はeval/no_grad、訓練以外の統計を尺度へ使わない。

## 5. baseline、集計、判定

last-value（最後のcontext値を32leadへ反復）とMA15（最後15binの平均を反復）を両方保存する。MA15はfloat32保存値からfloat64 `fsum/15`、予測保存はfloat32へ一度丸める。target別にvalidationの日等重みMAEで主baselineを一度選択し、厳密同値はlast-value。testで選び直さず、両baselineを併記する。baselineを3seedの独立標本として水増ししない。

qτを予測、e=(y−qτ)/Tとしてρτ(e)=max(τe,(τ−1)e)。各seedの主scoreは日等重み、その中でtarget等重み、各日のorigin・32lead・3quantile等重みのpinball。演算はfloat64で、quantile→lead→origin→target→日を`math.fsum`で順に平均する。seed平均は最後に等重み。validationの選択とtest報告で同じ日重みを使う。

WISはこの3分位点の等重み定義で`2×平均pinball`。target別原単位のpinball/WIS、p50 MAE、coverage80、区間幅、下側/上側miss率、lead別/日別、支持と全除外、遅延・メモリを残す。coverageは端点を含み、missは厳密不等号。異単位のMAEをそのまま平均しない。ratioの分母0はnullと絶対差を示し、epsilonで補わない。

1. 機構：seed平均のfull scoreがself-onlyより低く、3seed中2つ以上でも改善なら「この条件で系列間経路の探索的利点」。効果量、各seedとtargetの悪化も表示。
2. 予測価値：targetごとのfull p50 MAEが、validation固定baselineよりseed平均で低く、2seed以上改善ならそのtargetの探索的利点。事前の3target全表を維持。一部の改善を全体優位へ広げない。
3. 用途適合：必要な先読み、最小実用差、業務損失、遅延上限は未確定。研究上の微差・coverage・2/3seedを業務合格や統計的有意性にしない。自己相関した大量の点を独立標本数として扱わない。

baseline MAEとモデルWISの大小比較は禁止。公式TimesFMの旧C120/H15/11過去共変量・約2.77GiBの結果は別条件の参考だけ。この計画で公式同等性・汎用性・PSI採用を認定しない。

## 6. test隔離、成果物、終了点

数量準備とtrain/validation/testの読取口を分け、trainerはtest未来値へアクセスしない。全3seedの両構成のcheckpoint選択とbaseline選択を確定し、全test予測を先にfreeze/pinした後にだけ評価labelを開いて一括採点する。前のseedのtest成績を後続へ返さず、best seedを選ばない。test context内の既観測値は許す。

M0実装の成果物は、(a)新Mac用3target複数日converter/adapter、(b)paired trainer/launcherと分離したscorer、(c)本書/JSON/manifestを照合するdry-run・source/runtime pin、(d)必要なMac固有接続だけの最小forward記録。Windows helperをimportする旧trainer/check_modelをそのまま実行しない。構造を変えず、旧source・単日入力・closed rootsを保持。汎用可変長化や完成済み全人工試験の反復をM0へ足さない。

**次に未完了なのはM0の実装と数量品質・接続確認。今回は実施していない。** 実装/数量読取り/小規模forwardの工程が指示されれば固定契約内で具体化し、準備済み成果を再度の計画作成だけへ戻さない。M1実学習はその再開が明示されてから。原本/日付/数量/shape/有限性/時点境界/source/runtimeのいずれか不成立ならM0未完で停止する。

M1はseedごとにfresh root、各unit内で両構成を4096更新まで行う。最大3unit、各親900秒/子870秒、Mac physical footprintとpeak RSS各2GiB。計最大親2700秒で、追加候補・seed・延長なし。時間/メモリは観測checkpointと監視で管理し、OS hard capと称さない。

通常24file/768MiB、全体32file/1GiB、単file32MiB、失敗reserve8file/256MiB。各seedの正常23file以下の案：input/config/initial/schedule(4)、両構成×4checkpoint(8)、selection/test予測2/journal/source bundle/resources/summary(7)、stdout/stderr/exit/closure(4)。実行前にbyte見積りも確認。Evidence16MiB/512file・part256KiB・失敗reserve2MiB/16file、stdout1MiB/stderr128KiBを維持する。大きなsource snapshotは分割し、raw cacheと実験outputは区別する。

未完・nonfinite・境界違反・支持不足・上限到達ならstdio/exit/source/state/共通prefix/元エラー/closureを保存し、campaign incompleteで残りを止める。良いseedだけの採点、日付入替え、失敗rootの追記、予算延長による救済はしない。完走して悪化なら「この条件で追加価値未確認」で一巡を終える。新仮説なしの再監査・再評価を自動追加しない。

## 7. 他領域とAstra確認

油圧・XJTU・CAREの役割は上位計画に従う。M0から各領域の学習へ自動接続しない。需要は既存10店、調整2014以前、同休業mean28、四季平均の過小量・過大量非増加と既存MSE条件、観測のみ/休業相当欠測だけ0仮定の分離を維持。営業日の欠測を0へ変換せず、2015再評価停止を解除しない。

既存Astra agent `astra_weight_support_audit` がread-onlyで契約を確認。raw変換失敗と窓除外の分離、除外前の支持分母、train尺度の母集団/演算、選択と報告の日重み、bin-endの可用性仮定を採用した。日時監査後の13日案にも新しいblockingなしと回答し、数量不良後の差替え禁止、完全日の意味/回顧的選定限界、尺度生成後のfinite/正検査、旧float32計算との差分明示を反映した。設計レビューはここで閉じる。Astraは観測数量・labelを読まず、実行許可や性能を認定していない。追加agentなし。

Mac共通経路の日時/文書準備のみ完了。Windows native・OS依存suiteは未実行。今回Git statusはXcode利用規約未同意でexit69だったため状態一覧は未確認、規約同意や設定変更はしていない。旧文書は[改訂前snapshot index](../../artifacts/metropt-plan-detail-20261016-records/before-index.json)へ全文byte保存してから更新した。
