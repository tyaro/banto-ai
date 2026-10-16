# Rust R1の停止済み調査資料

2026-10-17に通常の実行対象から退避した。不採用の拡張、単発の診断・報告生成、ポインタ/SGEMM調査を含む。全source bytesは保存時のまま、拡張子に`.txt`を付けてimport・compile・実行対象から外した。

原版commit: `50d69b684acd8af6db6c045e372ce9d564d855f4`。保存tag: `archive/preformal-research-20261017`。[catalog](catalog.json)は元パス・保存先・サイズ・SHA256を列挙する。各ファイルを検証して退避し、失敗や不採用の履歴を変更していない。閉鎖済みartifactは元の場所に残す。

ここにあるコードは現checkoutのAPIではない。元の相対パス・ROOT計算・依存・Cargo featureを前提とするため、名前を戻したり直接実行したりしない。歴史的な構成の確認には原版commitと当時の証跡を使う。ポインタ追跡は人の指示で停止しており、通常の「進めて」で再開しない。

現行の比較器・参照producer・metadata・閉鎖検証helperは、共通利用があるため`tools/public-data/`に残した。旧R1 JSONと報告は固定パスを保持し、実行許可や次工程の指示とは扱わない。[現在の引継ぎ](../../../docs/current-handoff.md)を優先する。
