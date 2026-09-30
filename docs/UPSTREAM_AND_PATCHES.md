# 上游版本、公开补丁与复现范围

## 1. 来源与核对

| 项目 | 公开上游 | 收集时的本地 HEAD | 已核对的修改文件 |
|---|---|---|---|
| FAST-Calib ROS2 | [ichangjian/FAST-Calib-ROS2](https://github.com/ichangjian/FAST-Calib-ROS2) | `707df94bf7a4acdcb806affed7a9e41ee179518c` | `include/common_lib.h`、`src/qr_detect.hpp`、`src/lidar_detect.hpp` |
| FAST-LIVO2 | [hku-mars/FAST-LIVO2](https://github.com/hku-mars/FAST-LIVO2) | `837b7bbc1431cb04cf936528e52c83c835efba8e` | `include/LIVMapper.h`、`src/LIVMapper.cpp`、`src/vio.cpp` |

2026-09-30 补充审核包的八项文件摘要全部匹配。上述六个算法文件及两份 LICENSE 均从公开上游的确切 commit 获取并比对；收集到的 diff 应用后，六个文件都与上传文件逐字节相同。公开包只分发修改补丁与许可，没有复制整个算法工程。

这证明本次收集到的改动相对公开基线成立；不能自动证明 HEAD 和这些选定文件就是历史成功运行当天的全部环境。所有摘要和公开修改后的文件摘要见 [UPSTREAM_VERSIONS.json](UPSTREAM_VERSIONS.json)。

## 2. FAST-Calib：两个补丁

| 补丁 | 内容 |
|---|---|
| [0001-redo6-circle-fit.patch](../patches/fast_calib/0001-redo6-circle-fit.patch) | 增加圆拟合诊断日志；圆候选接受门限从 `0.02` 改成 `0.03` |
| [0002-redo6-k3-distortion.patch](../patches/fast_calib/0002-redo6-k3-distortion.patch) | 参数结构、声明和读取补上 `k3`；相机检测端把第五项畸变从固定 0 改为 `params.k3` |

圆日志包含簇编号、内点数、拟合半径、配置半径和平均半径偏差。接受门限针对代码中按**配置半径**计算的平均绝对半径偏差，单位为米；它不是最终外参 RMSE，也不是像素误差。放宽门限不意味着精度必然提高，换用其他板或距离时仍需验证。

`k3` 默认是 0。本项目模板给出了用户最终标定的第五项系数，应用两个补丁后检测端才会实际使用它。这个修改与历史 FAST-LIVO2 四项畸变配置不同，不能写成两种模型完全相同。

## 3. FAST-LIVO2：一个补丁

[0001-pixel-correspondence-and-image-ownership.patch](../patches/fast_livo2/0001-pixel-correspondence-and-image-ownership.patch) 包含三项改动：

1. 新增 `/pixel_point_correspondence` 发布者，重用已有的世界点到当前图像投影，输出六项 FLOAT32。
2. `getImageFromMsg()` 对 `toCvShare()` 的结果调用 `.clone()`，让队列持有独立图像数据。
3. 在视觉稀疏地图点投影处理中增加红点显示，实际条件为 `i % 2 == 0`。

原上传的第三项注释写了“1/5”，与条件不符；公开版只把该注释改成“1/2”，没有改变抽样条件。两项目的补丁另添加了 2026-09-30 的修改说明，原作者和许可说明保留，早期本地修改日期未独立确定。除这些公开说明与注释修正外，公开补丁没有改动用户提供的算法行为。

对应消息的具体坐标、时间戳和边界见 [FAST_LIVO2_CORRESPONDENCE.md](FAST_LIVO2_CORRESPONDENCE.md)。这不是新的定位算法或已经验收的语义建图实现。

## 4. 在干净副本中应用

以下命令从本资料仓库根目录执行。`upstream_sources` 是使用者新建的独立副本，已加入 `.gitignore`。不要在已经修改过的原工作空间强行应用补丁。

```bash
mkdir -p upstream_sources
git clone https://github.com/ichangjian/FAST-Calib-ROS2.git upstream_sources/fast_calib
git -C upstream_sources/fast_calib checkout --detach 707df94bf7a4acdcb806affed7a9e41ee179518c

git -C upstream_sources/fast_calib apply --check \
  "$PWD/patches/fast_calib/0001-redo6-circle-fit.patch" \
  "$PWD/patches/fast_calib/0002-redo6-k3-distortion.patch"
git -C upstream_sources/fast_calib apply \
  "$PWD/patches/fast_calib/0001-redo6-circle-fit.patch" \
  "$PWD/patches/fast_calib/0002-redo6-k3-distortion.patch"
```

```bash
git clone https://github.com/hku-mars/FAST-LIVO2.git upstream_sources/fast_livo2
git -C upstream_sources/fast_livo2 checkout --detach 837b7bbc1431cb04cf936528e52c83c835efba8e

git -C upstream_sources/fast_livo2 apply --check \
  "$PWD/patches/fast_livo2/0001-pixel-correspondence-and-image-ownership.patch"
git -C upstream_sources/fast_livo2 apply \
  "$PWD/patches/fast_livo2/0001-pixel-correspondence-and-image-ownership.patch"
```

检查差异：

```bash
git -C upstream_sources/fast_calib diff --check
git -C upstream_sources/fast_livo2 diff --check
git -C upstream_sources/fast_calib diff --stat
git -C upstream_sources/fast_livo2 diff --stat
```

依赖安装、ROS 工作空间放置和编译按各上游此版本的说明实施。本资料仓库自身不是可直接 `colcon build` 的完整 ROS 包。原始录包、完整配置、标定输入和必要依赖需由使用者提供。

**本次两个项目的三个补丁均通过 `git apply --check` 与实际应用验证，应用后文件等于公开版本的预期字节。本次没有在 ROS/PCL 环境编译、重新求解外参或回放录包。**

## 5. 已补齐与仍需提供的材料

此前缺少的 FAST-Calib 两个文件、FAST-LIVO2 三个文件已取得并整理为上述补丁，无需再次收集这五个文件。

仍未公开的输入包括原始标定图像、原始录包、完整设备配置、LiDAR→IMU 安装参数，以及历史求解日志和残差定义。这些缺口意味着仓库支持获取确切公开基线、还原选定源码修改和检查最终参数，但不能直接重跑所有历史结果，也不能保证另一台设备复用同一外参。

[collect_repro_sources.py](../scripts/collect_repro_sources.py) 保留作后续审查工具。其输出审核包没有纳入公开包，不能把它直接提交 GitHub。

## 6. 许可

两个项目的补丁均是 GPL-2.0 上游文件的修改，继续按 GPL-2.0 提供。许可全文分别见 [FAST-Calib LICENSE](../third_party/fast_calib/LICENSE) 与 [FAST-LIVO2 LICENSE](../third_party/fast_livo2/LICENSE)。根目录 MIT 不覆盖这些补丁。

FAST-LIVO2 的 `package.xml` 有 BSD 标签，但本次提供文件的原始头部指向仓库 LICENSE，该 LICENSE 是 GPL-2.0；不依据单行元数据把这些修改重新标成 BSD 或 MIT。原作者公开版权联系信息保留，不是用户的内部登录账号。独立辅助脚本与新说明的许可范围见 [ASSET_NOTICE.md](../ASSET_NOTICE.md)。
