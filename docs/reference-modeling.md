# 参考建模通用工具

2026-11-14 建立的轻量本地工具。只有通用代码进入 Git；所有个人输入、项目脚本、模型、贴图、预览和项目记录都放在忽略的 `projects/`。默认只提供静态图片，不自动打开 GUI、网页或常驻服务。

## 视频与图像处理

`uv run` 按 `pyproject.toml`、`uv.lock` 在忽略的 `.venv/` 中准备 NumPy 和 Pillow。Blender 仍使用自身 Python；FFmpeg/ffprobe 使用本机现有程序。

```sh
uv run python tools/prepare_video.py INPUT_VIDEO --output projects/PROJECT/references/frames --times 0.5,1.5,3.5 --height 1440
```

原件不变，输出时间命名 PNG、联系图和不含定位的清单。FFmpeg 应用显示旋转后缩放；采样时间对应邻近视频帧，不是精确姿态记录。拉普拉斯方差只是整幅图的清晰度辅助指标，不代表主体局部质量。

HLG 使用近似反变换、BT.2020 到 BT.709 矩阵与固定 filmic 映射；不应用 Dolby Vision 动态元数据，不是颜色标定或去光照。其他 HDR 格式未配置专门变换。已用真实 HLG 竖屏素材验证解码与旋转抽帧，具体证据留在私有项目。

## 后台渲染与检查

```sh
./bin/blender --background FILE.blend --python-exit-code 1 --python tools/render_views.py -- --output OUTPUT_DIR --views Hero,Front,Back --samples 24 --width 600 --height 800 --device METAL
./bin/blender --background FILE.blend --python-exit-code 1 --python tools/inspect_scene.py -- --output REPORT.json
```

渲染使用已有 `Camera.<名称>`，不保存场景改动，可选 `--device CPU`。Metal 在本机已实际完成渲染；无对应设备时明确失败，不静默切换。默认先小图低采样、串行处理，必要时提高质量，完成后退出进程。

检查读取 `role=asset` 网格，记录原网格和修改器求值后的非流形边、体积、尺寸以及缺失图片，不保存模型。实体项目可加 `--require-closed` 要求求值后封闭且正体积；有意开口的曲面不机械使用。不验证自相交、真实尺寸、照片相似度或材质准确性。

## 静态参考对照

```sh
uv run python tools/compare_reference.py --reference REFERENCE.png --render RENDER.png --reference-crop LEFT,TOP,RIGHT,BOTTOM --render-crop LEFT,TOP,RIGHT,BOTTOM --output COMPARISON.jpg
```

裁剪坐标按输入图片像素，输出并排比较图。工具不恢复相机、不校正透视，也不报告虚假的像素误差。结合近似参考相机判断轮廓与比例，不能把不同灯光的亮度差异全部归因于几何或材质。

项目特定的投射标注脚本留在私有项目。摄影测量、精确相机求解、自动分割、去光照与自动纹理拼接尚未实现，按真实需求选型。
