# Synthetic industrial data 実験

seed 再現可能な motor、conveyor、process-like signal の生成を扱います。generator には、regime、相関した signal、drift、欠損、label 付き fault-like event を持たせ、物理的な仮定を明示します。

生成した dataset 本体は、原則として Git の外に置きます。commit するのは generator parameter と manifest です。
