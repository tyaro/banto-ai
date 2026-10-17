# Astra 入力境界・時点契約の結果確認

2026-10-15 JST。方法担当 /root/astra_method_review と評価監査担当 /root/astra_process_audit（gpt-6-astra）が実装・fixture・保存canaryをread-onlyで確認。両者は新計算/テスト再実行/編集/2015参照をしていない。原snapshot照合の実行とpass確認は親agentの別readerで行った。

方法担当は主要な境界設計を確認し、v1 loaderのpin読出しとparse読出しが別であることを指摘。旧complete v1を保存したまま、[v2修正](demand-input-boundary-loader-review-2026-10-15.md)を追加。上限付き一回readの同じbytesをhash照合後parseするため、この問題は解消したとコードで確認。追加3fixtureも適切との回答。これは認証/アクセス隔離や実着荷時刻の証明ではない。

評価監査担当は今回を契約チェック完了とする判断を支持し、以下の限定を求めた。

- load_inputsは全470行をdecodeする。早いcutoffから見て後のcontextもプロセスには存在し、fit_prefixはそれらをfit対象に通さない契約。将来の学習consumerはaccepted keysだけを使う。cutoff後の数量が物理的に不可視とは主張しない。
- LabelReaderの初期化は全payloadをhash用bytesとして読む。正確には『prefixで未到来labelをdecode/数量利用しない』。trusted bindingからのindex/pinsが前提で、任意Pythonを隔離するsandboxではない。
- canaryは、既存contextを固定してtarget欄を変えた非干渉の検証。原context/尺度/休業根拠の正しさは別のraw照合が必要。
- readinessはschema上の可用性だけで、feature_support_for_new_model_verified=Falseを維持。新モデル特徴支持/実arrival/timezone/独立性能/逐次モデル挙動は未検証。

双方の最終回答時点でv2独立readbackは実行中だったため、passを先取りしないと指摘。回答後、親agentがreadback-records completeとchecks passedを確認し、[結果報告](../results/demand-input-boundary-2026-10-15.md)へ反映した。新fit/候補予測/score/2015再評価へ接続せず、今回の境界契約と独立原データ照合までで閉じる。
