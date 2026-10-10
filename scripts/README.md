# Python 工具

- `audit_storyboards.py`：检查连续编号、图像解码、原文覆盖及素材哈希；通过核对后可打包选中素材。
- `align_narration.py`：将外部识别工具提供的逐词时间匹配到原文分镜，输出时间表和 SRT；不确定的匹配仍需核对。

运行需要 Python 3.9 或更新版本，素材核对还需要 Pillow。请在仓库根目录运行 `python -m pip install -r requirements.txt`。

用 `python scripts/audit_storyboards.py --help` 或 `python scripts/align_narration.py --help` 查看参数。完整命令见 [仓库说明](../README.md)。
