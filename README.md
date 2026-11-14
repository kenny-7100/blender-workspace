# Blender + Python 移动硬盘工作区

建立日期：2026-11-14。适用机器：Apple Silicon Mac。

所有路径 `~/kenny/blender-workspace` 与 `/Volumes/kenny/blender-workspace` 指向同一工作区。先连接移动硬盘再启动。

## 长期 Agent 协作

协作规则见 [AGENTS.md](AGENTS.md)，按任务查阅 [文档导航](docs/README.md)。文档会随实际任务主动沉淀可复用结论，保持轻量，不要求每次扫描全库或生成会话日志。

Git 保留代码、文档和经过选择的工作模型与预览；应用、安装包、个人配置、缓存、日志、自动备份及 `projects/**/outputs/` 等批量产物被忽略。忽略不等于备份，大型或外部资源的保存规则见 [建模工作流](docs/modeling-workflow.md)。

## 启动与运行

双击 `Open-Robot-Demo.command` 打开机器人示例，或双击 `Launch-Blender.command` 启动 Blender；建议始终使用它，以便配置、用户脚本、扩展、缓存和临时文件指向移动硬盘。macOS 自身仍可能在系统目录保存少量日志或缓存。

在终端运行示例（首次 Cycles 渲染需要等待）：

```sh
~/kenny/blender-workspace/bin/blender --background --python ~/kenny/blender-workspace/projects/robot-demo/model.py
```

打开已生成的可编辑模型：

```sh
~/kenny/blender-workspace/bin/blender ~/kenny/blender-workspace/projects/robot-demo/robot.blend
```

`model.py` 使用 Blender 内置的 `bpy`，必须通过 Blender 执行，不要用系统 `python3 model.py`。无需另外安装 Python、pip 或 bpy 包。

## 文件布局

- `apps/Blender.app`：官方 Blender 4.5.9 LTS，macOS arm64 应用，自带 Python。
- `downloads/`：官方原始 DMG 和 SHA-256 清单。
- `bin/blender`：配置环境变量的命令行入口，无需修改全局 PATH。
- `Launch-Blender.command`：图形界面启动入口。
- `config/`、`scripts/`、`datafiles/`、`extensions/`：用户资源。
- `cache/`、`tmp/`：缓存和临时目录。
- `projects/robot-demo/model.py`：生成静态卡通机器人、材质、灯光和相机。
- `projects/robot-demo/robot.blend`：可编辑模型与完整场景。
- `projects/robot-demo/robot.png`：800 × 800 Cycles CPU 渲染。
- `projects/robot-demo/verification.json`：运行版本、对象数和输出记录。
- `projects/robot-demo/build.log`：建模与渲染日志。

此示例是静态基础建模，未做骨骼绑定或动画。脚本会替换当前场景，建议在独立后台进程运行；重复执行会覆盖同名输出，Blender 可能保存 `.blend1` 备份。

## 安装来源

- https://download.blender.org/release/Blender4.5/blender-4.5.9-macos-arm64.dmg
- https://download.blender.org/release/Blender4.5/blender-4.5.9.sha256
- DMG SHA-256：`e3a3d7aac381fb4e4d05197f99cd8899484d7e8bc4497c134066e6733f372238`

macOS 的 `hdiutil attach` 拒绝挂载后，使用已有 `7zz` 直接提取 DMG 中的 `Blender/Blender.app`，应用放在移动硬盘，不安装到系统 `/Applications`。

## 实际验证结果

Blender 4.5.9 LTS / 内置 Python 3.11.11；官方 DMG 摘要与应用代码签名校验通过。后台建模与 Cycles CPU 渲染完成，39 个场景对象（35 个网格），输出 800 × 800 PNG。独立进程重新载入 `.blend` 并检查对象和相机通过（`reopen.log`）。图形界面已成功打开 `robot.blend`，完成默认初始设置。配置路径与运行时临时目录均核实位于移动硬盘。GPU 渲染与人物绑定未验证。
