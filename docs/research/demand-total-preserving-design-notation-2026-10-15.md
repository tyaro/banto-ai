# 総量保存契約の数式表記について

2026-10-15 JST。[実行前契約](demand-total-preserving-design-2026-10-15.md)にある係数のclip表記は次の演算を意味する。

```python
alpha = max(0.0, min(1.0, covariance / energy))
# energy <= 1e-24 の場合は alpha = 0.0
```

元の角括弧と丸括弧を続けた数式表記がMarkdownリンクとして解釈され、文書リンク監査が停止した。研究条件・演算の変更ではない。元の契約/source pin・完了したmodel/execution/readback・failed doc-recordsを保持し、修復や模型再実行をせずこの補記を追加した。後続doc-records-v2で、元契約の当該一箇所を数式の表記誤りとして明示し、その他のリンクと結果数値を検査する。
