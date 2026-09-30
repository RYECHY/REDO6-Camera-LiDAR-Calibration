# 坐标、逆变换与 ROS 2 静态 TF

## 外参方向

本文固定使用：

\[
\mathbf p_C=\mathbf R_{CL}\mathbf p_L+\mathbf t_{CL}.
\]

它把 LiDAR 坐标中的点变成相机坐标中的点。字母 C/L 分别代表相机和 LiDAR，不能只通过某个文件名推断变换方向。

对应的齐次变换及逆变换为：

\[
T_{CL}=\begin{bmatrix}R_{CL}&t_{CL}\\0&1\end{bmatrix},
\qquad
T_{LC}=\begin{bmatrix}R_{CL}^{T}&-R_{CL}^{T}t_{CL}\\0&1\end{bmatrix}.
\]

逆平移不是简单的 `-t_CL`。若旋转不是单位阵，两者一般不同。

## 光学坐标与帧名

相机光学坐标常用 x 向右、y 向下、z 向前。设备提供的 `camera_link`、光学帧和图像消息帧可能不是同一个坐标约定。

不能通过把消息帧名强制改成某个字符串来修复坐标轴错误。还应核对点云是否已经由 LiDAR 帧变换到了 body 或 map 帧；已经变换的点不能直接再次使用原始 LiDAR→Camera 外参。

## TF 父子关系

若以 LiDAR 为父帧、相机光学帧为子帧，静态 TF 的数值表示相机光学帧在 LiDAR 帧下的位姿，应使用 `T_LC`。查询相反方向时 TF2 返回相应逆变换。

四元数按 `(x,y,z,w)` 记录。`q` 与 `-q` 表示同一个旋转，不能只根据符号比较结果。

## 本地生成参考命令

先准备自己拥有的真实参数，并确认父帧与光学子帧。命令中的帧名是示意名称，需替换为真实已确认的帧名：

```bash
python3 scripts/check_calibration.py private/local_calibration.yaml \
  --print-tf --parent lidar_frame --child camera_optical_frame
```

检查工具只打印 `static_transform_publisher` 命令，不会运行它，也不会连接设备。本项目参数原文件把相机帧记录为 `camera_frame`；实际使用前须确认它是否对应光学坐标，不能只凭名称判断。

生成四元数时，对已经通过数值检查的 R 做一次 SVD 正交化，只用于消除有限小数带来的数值偏差。源 YAML 不会被修改。严重不合法的旋转会直接被拒绝，而不是自动修复。

## 发布前与发布后的核对

在正确 ROS 环境中，检查图像与点云真实消息头、已有 TF 链和静态变换发布者。若已有权威的同一子帧关系，应核对其数值，避免另开一个冲突发布者。

例如在运行期间分别执行：

```bash
ros2 topic info /tf_static --verbose
ros2 run tf2_ros tf2_echo lidar_frame camera_optical_frame
```

保存第一方向的输出后停止该命令，再查询相反方向：

```bash
ros2 run tf2_ros tf2_echo camera_optical_frame lidar_frame
```

父 LiDAR、子相机的第一方向应对应 `T_LC`，反向应对应 `T_CL`。有中间帧时比较的是组合变换。

同时验证图像 K/D、时间戳与投影图。TF 连通不等于标定准确。本文不包含任何具体机器人当前的 TF 部署状态。

参考：[ROS 2 Humble 官方静态广播器教程](https://docs.ros.org/en/humble/Tutorials/Intermediate/Tf2/Writing-A-Tf2-Static-Broadcaster-Py.html)。
