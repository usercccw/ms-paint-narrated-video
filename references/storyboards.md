# 画面规范与生图方法

用于样图、全量分镜、单图修正以及原照片观点页。先读取本期确认文本和认可样图，不要从旧一期复制主题或角色。

没有用户提供的画风样图时，可查看附带的 [粗绘画风参考](../assets/approved-style-reference.png)，仅用于观察色彩、头发和衣物处理、黑白区域布局及字幕大小。新分镜按新稿重新设计，不复制这张图的场景和字幕。

## 场景规划

每个编号先确定以下信息：原文字幕、叙事作用、画面主体、动作或图形关系、少量颜色、普通粗绘还是原照片观点页。抽象句可以用可理解的物件、两个小人、天平、标签、绳索等表达；保持画面简单，避免每张图都是一个人物做同一手势。

独立短句也有自己的画面。例如“代表自由。”“代表反抗。”可以各用一个鲜明符号，不因为字少就漏掉。长句仍完整保留字幕，通过两行和合理字号解决。

## 普通粗绘图片

采用当前环境可用的图像生成工具生成新位图；在 Codex 中优先使用内置 imagegen，具体调用遵循当前技能和工具说明。每个编号是独立图片，不能拿一张包含多个小格的总览冒充所有分镜。没有图像生成能力时说明缺失，先完成分镜清单与提示词。

参考图有两个不同用途，提示词要说清楚：

- 样图仅提供线条、平涂色、布局及字幕形式，不能无意继承其人物、道具或文字。
- 修改图提供目标画面本身，要明确哪些元素保留，哪些改变。

对于有本地路径的图片，先查看实际图像，再将路径作为编辑参考。不要把生成结果的完整 base64 放入文本输出。

### 通用提示词骨架

按每个编号改写场景和原文字幕，不要机械照抄整段：

```text
Create ONE standalone landscape storyboard image, about 16:9.
Style: an extremely simple beginner MS Paint drawing made quickly by hand.
Thick uneven black outlines, wobbly lines, flat bucket-fill colors,
round heads, dot eyes, basic expressions and simple limbs.
Characters have simple visible hairstyles and plain clothing details.
No gradients, realistic shading, 3D, textures or cinematic lighting.

Layout: a black top band about 12% of the height, a plain white central
drawing field about 73%, and a black bottom subtitle band about 15%.
Scene: [本句对应的单一清楚场景，以及人物动作和道具关系].
Keep all hair, faces, hands and props inside the white field with margin.
The reference image is for style and layout only; do not copy its scene.

Bottom subtitle, in readable white plain Chinese system-style type:
[逐字填写本句原文].
Use [明确的一行或两行断句], preserve every character and punctuation.
No unrelated caption, watermark or invented text.
```

黑带比例允许微调；所有帧看起来属于同一套模板更重要。实际输出尺寸由工具能力决定，后续整张等比放入 1080p 画布，不为追求整齐裁掉字幕。

## 原照片观点页

直接把用户照片放进版面。只等比缩放及摆放，不通过 imagegen 编辑人物。需要气泡、图标、背景和字幕时可用确定性 HTML/CSS/SVG 排版并截成 PNG。

- `<img>` 可用 `object-fit: contain`，确保脸、手、照片边缘没有意外裁切。
- 图片长宽比和原图内容保持一致；保留原照片文件及其哈希作为来源证明。
- 气泡配合对应句的观点，不把全文全部挤进气泡。
- 观点是稿件概括时加小标题“观点概述”。真正逐字引用才用引文形式，并确认来源；没有证据时不要编造名言。
- 气泡可随照片放左侧或右侧；字数多时手动安排合理行宽，避免最后一行只剩一个字。
- 图像底部字幕仍来自完整原稿，不能用气泡文字替代字幕。

真实人物照片页需由用户明确选择；没有提供或要求照片时，不应自行下载或换用照片素材。

## 批量生成与修正

先完成用户要求的样图数量并展示。认可后，以编号清单继续生成，保留已认可样图的文件与哈希。

可以批量安排已经确定的独立请求，但保持小批次；每批保存结果并检查再继续。失败的编号单独重试，不因一个失败而重做整个批次。磁盘上选中版本的实际文件才是可靠的完成状态。

每张检查：

- 字幕与原文逐字对应，包含引号、否定词、姓名、数字和标点。
- 人物肢体数正确，头发和道具完整，不碰到黑带。
- 构图确实表达该句，人物及服装有适度变化。
- 符合粗绘、平涂、白背景和统一版式。
- 原照片页保留照片内容、气泡易读且没有虚构逐字引文。

按约六张一组查看总览有助于发现重复布局；出现疑点时打开原尺寸图片。OCR 仅用于寻找疑点，不能代替看图，也不能因 OCR 把正确汉字误认而重新生成正确图片。

### 常见问题与修正方法

| 问题 | 修正方法 |
| --- | --- |
| 中文大字“羞”写错 | 对目标图片局部编辑，明确替换为“羞耻”，保留其他元素和底部原文 |
| 头发或头像撞上顶部黑带 | 缩小或下移主体，在白色画区上沿留下明显间距 |
| 同一人物出现三只手 | 明确保留两只手的动作，删除多余手臂及相关线条 |
| 道具超出白色画区 | 缩放整个道具而非裁掉外缘，保持字幕带完整 |
| 长字幕拥挤 | 在自然语义处拆成两行，全部字和标点保持原样 |
| OCR 把“观点”读成“观占”等 | 查看原图确认文字，不按识别误差盲目改图 |

这些是检查重点，不是要求每期都做相同修正。修正后的版本重新查看，旧版本放在 `attempts/`；更新选中版本及修正记录，再继续。
