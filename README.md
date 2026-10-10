# MS Paint 口播视频制作 Skill

把已确认的中文口播制作成 MS Paint 粗绘风格的逐句分镜，再结合用户原配音对齐并导出视频。

适合知识讲解、观点表达和故事类口播，也支持只制作图片、断点续作，以及仅修正指定分镜。

![粗绘画风参考](assets/approved-style-reference.png)

## 安装

使用支持 Agent Skills 的工具，通过 Skills CLI 安装：

```bash
npx skills add usercccw/ms-paint-narrated-video --skill ms-paint-narrated-video
```

安装到 Codex 的个人技能目录：

```bash
npx skills add usercccw/ms-paint-narrated-video --skill ms-paint-narrated-video -g -a codex -y
```

也可以下载本仓库，把整个目录命名为 `ms-paint-narrated-video`，放入使用环境的技能目录；Codex 可使用 `~/.codex/skills/`。

## 怎么使用

向支持该 skill 的助手提供文稿，并说明当前制作阶段。例如：

> 使用 $ms-paint-narrated-video，按这份已确认口播先做前五张粗绘分镜，每张底部放对应原文字幕。

> 样图已经认可，继续做剩下的独立分镜，保留已经通过的图片。

> 图片和配音都已准备好，把它们逐句对齐并导出完整 MP4，保留原配音。

> 只修改第 12 张的多余手臂，保留其他元素和字幕。

## 工作流程

1. 锁定已确认文稿，建立逐句分镜与素材清单。
2. 先制作用户指定的样图，确定画风后完成其余分镜。
3. 检查原文字幕覆盖、图像完整性和已认可素材哈希。
4. 根据用户配音的逐词时间生成初步分镜时间表，核对不确定切换。
5. 按时间表合成视频，检查实际输出的画面、声音与结尾停留。

默认画面为横向粗绘、白色画区、上下黑带及底部白色原文字幕。视频默认 1920×1080、30 fps、静态停留与直接切换，末尾约 2 秒留图。用户提供的样图和新要求优先。

## 运行环境

这个仓库提供技能指令、参考资料、画风样图和两个 Python 工具，不包含图像模型、转写模型或视频渲染器。

- 助手需要具有文件操作和图像生成能力；Codex 中可使用内置 imagegen。缺少图像工具时，可先产出分镜与提示词。
- 合成阶段需要 ffmpeg / ffprobe，以及 HyperFrames 或用户认可的其他视频合成工具。使用 HyperFrames 时，需另行安装其 CLI 和对应技能。
- 配音对齐需要外部工具输出的逐词时间，例如 Vosk 或其他识别引擎；本仓库不自行转写音频。
- 两个脚本需要 Python 3.9 或更新版本。素材核对脚本还需要 Pillow：

```bash
python -m pip install -r requirements.txt
```

## Python 工具

以下命令在本仓库根目录运行；`EPISODE`、`WORK`、`DELIVERY` 和 `ACTUAL_SECONDS` 需替换为本期实际路径或配音时长。

核对分镜编号、图片解码、原文覆盖和已认可素材哈希：

```bash
python scripts/audit_storyboards.py --manifest EPISODE/manifest.json --root EPISODE --script EPISODE/approved-script.txt --report WORK/audit.json --require-reviewed
```

核对通过后打包选中素材：

```bash
python scripts/audit_storyboards.py --manifest EPISODE/manifest.json --root EPISODE --script EPISODE/approved-script.txt --require-reviewed --zip DELIVERY/storyboards.zip
```

将逐词时间与原文分镜对齐，生成时间表和 SRT：

```bash
python scripts/align_narration.py --manifest EPISODE/manifest.json --words WORK/words.json --audio-duration ACTUAL_SECONDS --output WORK/timeline.json --srt DELIVERY/captions.srt
```

输入字段和更多用法见 [素材清单说明](references/assets-and-resume.md) 与 [音画对齐说明](references/audio-and-video.md)。时间表中的 `needs_review_ids` 需要实际核对；脚本结果不能代替人工查看图片和试听声音。

## 仓库结构

```text
ms-paint-narrated-video/
├── SKILL.md                      技能入口与工作流程
├── agents/openai.yaml            Codex 展示信息
├── assets/approved-style-reference.png
├── references/
│   ├── storyboards.md            画面规范与生图提示词
│   ├── assets-and-resume.md      素材清单、修正与续作
│   └── audio-and-video.md        配音对齐与成片核对
├── scripts/
│   ├── audit_storyboards.py      素材核对及 ZIP 打包
│   └── align_narration.py        逐词时间对齐及 SRT 输出
├── requirements.txt
└── LICENSE
```

## 开源许可证

本仓库的技能指令、脚本、说明和附带的画风参考图以 [MIT License](LICENSE) 发布，允许使用、修改、分发和商业使用，需保留许可证与版权声明。

本仓库不捆绑生成模型、转写模型、字体或用户的配音与人物照片；使用者自行准备的素材和工具遵循各自许可。
