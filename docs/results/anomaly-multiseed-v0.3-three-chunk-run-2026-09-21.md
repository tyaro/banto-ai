# v0.3 準備済みrunの3区間連続運転

2026-09-21 JST。対象はclean `C:/Users/TKent/.codex/worktrees/v03p/banto-ai`、実装 **c01d1c978f78bab51391392d56cdcb7aab5afaab**、出力`artifacts/v03-runs/r1`。

## 実行中の保存点

ユーザーの「お願いします」に基づき、準備済みの初期closed記録から`continue --max-chunks 3`を開始した。登録dev seed2486912926863618161のlayout0〜2、各core/quality-stress×3候補＝最大18評価。同じrunの完了済み区間はまだなく、旧trialを転用しない。

外部prepared hashは`be582d48faf61a764cd0341d742af2112fd9cd0e7e9d16e979aff8770d2538c7`、開始closedは`run/control/000000/closed.json` / hash`85a6163034c5392ce1ef78f4cbaa6da0faf9c06a66faae03c8c0f8df0c8ebf39`。全体48時間/32GiBの候補上限と区間ごとの所有process監視を維持する。

実行wrapperは候補worktreeの`artifacts/three-chunk-run-2026-09-21/run.py`、同folderの`request.json`に実argv/開始runtime/資源を保存した。CLIのstdout/stderrは外部ファイルへ保持し、診断は60秒間隔でcontroller private、空きRAM/disk、確定済みjournalの最新状態を記録する。診断表示だけを成功判定にせず、終了後のclosed pinと成果物を照合する。未終了processや未閉鎖呼出しの自動再起動は行わない。

開始時Windows26200.9457/CPython3.14.0/exe・DLL hashは前回と同じ。事前空きRAM13133750272/C174109761536/D119512887296 bytes。実行中のsourceは編集しない。保護root/principal、UAC/ACL/service/task、本流や過去trialに変更なし。

この保存点では実行中で、3区間完了や全120区間、Phase 2/3、S6の完了を追加しない。終了結果は同文書に追記する。
