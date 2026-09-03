# banto-ai アーキテクチャと Banto Hub との境界

## 目的

`banto-ai` は、研究コード、評価、モデル成果物、提案段階の連携契約を担当します。`banto-industrial` と Banto Hub は、運用データへのアクセス、権限、デバイス ID、制御連携、本番監視を担当します。

初期アーキテクチャは、意図的に一方向でレビュー可能な構成にします。

```text
Banto Hub / historian
        |
        | 承認済み export または read-only adapter
        v
banto-ai dataset adapter
        |
        +--> benchmark / training / evaluation
        |          |
        |          +--> model artifact
        |          +--> evaluation report
        |          +--> commissioning profile candidate
        v
shadow inference またはレビュー済み handoff
        |
        v
Banto Hub の運用コンシューマー
        |
        v
PLC / 制御システム（安全の権威はここに残す）
```

## 責務分担

| 関心事 | banto-ai | Banto Hub / 制御システム |
| --- | --- | --- |
| 予測・異常検知の研究 | 担当 | 承認済み出力を利用 |
| モデル学習・評価 | 担当 | 本番環境で暗黙に学習しない |
| データ export とアクセス方針 | 契約を要求 | ID、権限、保持期間を管理 |
| 設備モードとレシピ実行 | 提案されたメタデータを観測 | コマンド実行とインターロックを管理 |
| 警告候補 | 提案 | レビュー、適用、または却下 |
| 非常停止とハード上限 | 担当しない | 常に担当 |
| 本番昇格 | 根拠を提供 | 承認と rollout を管理 |

## 連携段階

### Stage 1: offline export

オペレーターまたはスケジュール処理が、データセット manifest とともに期間を限定したデータを export します。研究コードは live 接続なしでこの export を読み取ります。

最低限必要なメタデータ:

- `dataset_id` とデータの出所
- tag 名と工学単位
- サンプリング間隔とタイムゾーン
- 必要に応じて匿名化した設備・ライン ID
- 取得できる場合は運転モードとレシピ ID
- quality flag、欠損値方針、保全期間
- train／validation／test の分割定義

### Stage 2: read-only または shadow adapter

adapter は直近の観測値を要求し、予測、残差、異常スコア、信頼区間を返せます。ただし PLC 値、閾値、レシピ、インターロック設定を書き込んではいけません。

すべての応答に、明示的な model version と profile version を含めます。モデルが利用不能、古い、out of distribution、または必要な tag が不足している場合は、暗黙の fallback ではなく明確な degraded state を返します。

### Stage 3: reviewed handoff

レビュー済みの model artifact または commissioning profile は、Banto Hub の既存の承認・デプロイ手順を通して昇格できます。昇格時には次を含めます。

- 評価レポートとベースライン比較
- 学習データの出所
- model と設定の hash
- 根拠がある運転モード
- 既知の失敗モードと rollback 先
- レビュー担当者と承認日時

## 提案する論理契約

以下は研究用の契約であり、確定した公開 API ではありません。

### Forecast request

```json
{
  "model_id": "timesfm3-baseline",
  "model_version": "<immutable-version>",
  "equipment_id": "<pseudonymous-id>",
  "as_of": "2026-01-01T00:00:00Z",
  "horizon": 60,
  "frequency": "1s",
  "signals": {
    "motor_current": ["..."],
    "motor_temperature": ["..."]
  },
  "mode": "shadow"
}
```

### Forecast response

```json
{
  "model_id": "timesfm3-baseline",
  "model_version": "<immutable-version>",
  "profile_version": "<optional-profile-version>",
  "status": "ok",
  "forecast": {"motor_current": ["..."]},
  "intervals": {"motor_current": {"p10": ["..."], "p50": ["..."], "p90": ["..."]}},
  "anomaly_score": 0.0,
  "quality": {"missing_ratio": 0.0, "out_of_distribution": false}
}
```

### Commissioning profile candidate

candidate profile には、学習した正常エンベロープ、校正係数、カバーしたレシピ step、データ品質の根拠、有効期間を含めます。助言値と自動昇格から保護する値を明確に区別します。この profile は制御レシピではなく、PLC に直接書き込んではいけません。

## データと成果物のルール

- 顧客の raw data は、顧客が承認した storage boundary 内に留めます。
- リポジトリ内のデータは合成または公開データとし、license と出所を記録します。
- export データは experiment run 内で不変とし、変換処理を manifest に記録します。
- 成果物は content-addressed、または昇格後に不変となる方式にします。
- 学習に使ったデータだけでモデルを評価してはいけません。

## 今後決めること

1. 最初の adapter に適した安定形式は何か: CSV bundle、Parquet、または versioned API。
2. shadow adapter が使う ID と認可方式は何か。
3. 承認済み artifact と commissioning profile をどこに保存・署名するか。
4. ユースケースごとに必要な latency、保持期間、backfill 保証は何か。
