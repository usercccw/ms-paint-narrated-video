# 记录、修正与图片交付

用于分镜清单、断点续作、图片数量核对及 ZIP 打包。

## 一个权威清单

建议每期保存 `approved-script.txt` 和 `manifest.json`。完整口播文件只放实际要读的内容，不混入文件名、Markdown 标题或说明。不要把口播标题又在正文中重复计算。

`manifest.json` 可以直接使用以下结构；如接手旧项目，保留旧记录并转换字段或让工具适配，不要再造相互冲突的多份清单。

```json
{
  "title": "本期标题",
  "timing_status": "pending_audio",
  "frames": [
    {
      "id": 1,
      "file": "001.png",
      "caption": "本句完整原文。",
      "mode": "imagegen",
      "scene": "对应场景",
      "prompt": "实际使用的提示词",
      "references": [],
      "source": "工具返回的本地图片或用户原图来源",
      "sha256": "选中图片的实际 SHA-256",
      "status": "selected",
      "visual_review": "passed",
      "corrections": []
    }
  ],
  "approved_hashes": {
    "001.png": "已认可样图的实际 SHA-256"
  }
}
```

- `id` 从 1 连续编号，文件名至少三位补零，如 `001.png`。不要把上期的 77 当成固定数量。
- `caption` 是原文，包括标点；图片中的换行可与记录中的自然句格式不同。
- 照片页使用 `mode: original_photo_layout`，并保存原照片文件、原照片哈希和生成版面的路径。
- 修正记录包含原因、旧版本、选中版本和检查结果。显式修改原已认可图片时，同步更新认可记录，并保留修改依据；没有修改指令不能把旧哈希静默更新掉。
- `visual_review: passed` 只在实际查看图片后填写，不能由文件存在或 OCR 成功自动设置。

## 续作规则

先清点已存在、解码有效且选中版本明确的图片；再与原文单元清单比较。复用已正确的部分，定位未生成、出错或因新稿变化而失效的编号。

文稿改动后，比较原句与新句，重新编号映射和受影响的后续切换时间；不要因为编号整体移动就重新画没有变化的画面。记录旧编号对应新编号以免丢图。

服务异常时保存已完成结果及错误类型。连接错误或 403 访问失败按工具访问问题处理；真正内容拒绝才按其理由处理。对失败请求作有限重试，例如两次合理重试后暂停该编号并报告。不要无限循环，也不要未经用户要求切换到需要额外凭据或费用的服务。

异步任务尚未完成时，不假定内存状态已跨执行单元提交；保存每个完成结果到磁盘，再以磁盘清点续作。

## 核对与打包工具

`scripts/audit_storyboards.py` 需要 Pillow；脚本不修改图片，默认只核对。它检查：

- 连续编号与正确文件名，每个图片实际解码。
- 拼接字幕与完整口播一致，仅忽略空白；不能把同义改写当成一致。
- 选中图片和已认可图片的哈希，没有缺失或重复编号。
- 清单中的人工查看状态；`--require-reviewed` 可将尚未通过的图片视为未完成。

命令中的 `python` 应替换为当前可用运行时，路径带空格时使用所属 shell 的正确引号：

```text
python scripts/audit_storyboards.py --manifest EPISODE/manifest.json --root EPISODE --script EPISODE/approved-script.txt --report EPISODE/audit.json --require-reviewed
```

全部通过后再打包，可附带已经存在的总览、浏览页、字幕文件与原照片目录：

```text
python scripts/audit_storyboards.py --manifest EPISODE/manifest.json --root EPISODE --script EPISODE/approved-script.txt --require-reviewed --zip DELIVERY/分镜.zip --include captions.txt --include contact.jpg --include gallery.html --include references
```

脚本默认拒绝覆盖报告或 ZIP；需要更新已有输出时显式加 `--overwrite`。仅被选中的图片、清单、原文和明确附带的文件进入 ZIP；`attempts/`、中间图和制作程序不作为默认交付内容。脚本核对 ZIP 文件完整性，但无法证明画面中实际文字或构图正确，仍需人工看图。

## 推荐图片交付

- 编号独立 PNG。
- 完整口播、按编号的字幕清单和选中素材记录。
- 总览 JPG 与可顺序翻看的本地 HTML 浏览页。
- 有原照片页时附原照片来源记录。
- ZIP 成品包；在回复中提供实际可点击路径，并展示少量预览或总览。

配音尚未收到时，说明图片已完成、时间待音频对齐。用户只要图片时在这里结束本次制作。
