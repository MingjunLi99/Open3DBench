# 公司环境部署适配修改日志

本文件记录 `huawei-partition` 分支针对公司离线环境和公司 3D placer 的适配。后续提交按时间倒序追加，记录行为变化、兼容性影响、验证结果和遗留事项；不要在此写入公司 URL、账号、token、license server、内部 PDK 路径或专有 DEF 内容。

## 2026-08-13：首次离线 backend 适配

### 目标

- 在无公网的 CentOS 7.9 WSL2 上运行 OpenROAD-3D backend evaluation；
- 接收公司 placer 输出的 Nangate45 top/bottom DEF，而不运行 Open3DBench Place-LoL placer；
- 将 `HBT[n]` DEF PIN 转换为 Open3DBench 使用的 HBT pseudo-cell；
- 支持 eval-only 和保留公开 placer 的完整离线发布方式；
- 支持后续通过公司 CodeHub 和 Git LFS 协作。

### DEF 转换和公司评估入口

- 新增 `OpenROAD-3D/flow/util/convert_company_3d_def.py`：
  - 合并 top/bottom DEF；
  - instance 默认增加 `_top`/`_bot`，保证合并后唯一；
  - cell 和 fakeram master 增加 `_upper`/`_bottom`，匹配 `nangate45_3D` LEF/Lib；
  - 将成对的 `HBT[n]` PIN 转换为 `HBT_n` pseudo-cell；
  - 将两侧 local net 转换为 `_TOP`/`_BOT` 并连接 HBT 的 `TOP`/`BOT` pin；
  - 校验 DEF section 数量、DIEAREA、重复 instance/IO、HBT 配对、坐标、方向和 net 引用；
  - 提供 `--no-instance-suffix` 调试选项，但公司默认流程保留 `_top`/`_bot`。
- 新增 `OpenROAD-3D/flow/run_company_3d.sh`，完成双 DEF 转换并调用现有 backend flow；支持 `ariane`、`bp`、`swerv_wrapper`、`tinyRocket`。
- 新增 `config_company.mk`；`ariane` 暂映射 `ariane133`，`bp` 映射 `black_parrot`。
- 为仓库原本缺失的 Nangate45 3D `tinyRocket` 增加初始 company config 和 SDC；仍需用真实公司网表确认 top module、SDC 和 fakeram 类型。

### 后端 DEF 解析修复

- 重写 `split_cts_def_lol.py`，按完整 DEF entry 和 `_upper/_bottom`、`_TOP/_BOT` 归属拆分 legalization DEF，不再依赖固定行布局。
- 重写 `save_map_lol.py`，兼容标准多行 COMPONENT entry。
- 重写 `read_def_store_coord.py`，从 `PLACED/FIXED` 语句解析和回写坐标，不再依赖固定列号。
- 保留原 `do-lolflow` 的读 DEF、ODB、CTS、上下 die legalization、route 和 finish 主流程；公司入口不再依赖 `Place-LoL` 路径。

### 离线 Docker 和发布工具

- eval/place 容器默认使用 `--network none`。
- `OpenROAD-3D/start_docker_eval.sh` 支持只读挂载公司 placer 输出，且 eval-only 模式不要求存在 `Place-LoL`。
- 增加 Docker 26.1.4 静态安装和非 systemd WSL 启动脚本；拒绝将公司 yum 中的 Docker 1.13.1 作为运行时。
- 增加 host、SHA256、镜像导入和 LoL 数据部署检查脚本。
- 增加 backend-only source bundle 和完整 source/Git bundle 制备脚本。
- 增加 `prepare_release.sh`，统一制备 eval-only/placer-complete release，支持 FAT32 分卷并生成 `SHA256SUMS`。
- 增加 `assemble_parts.sh`，用于安全检查连续分卷并重组非镜像文件。
- Place-LoL benchmark、binary、Docker archive、公司 DEF 和运行结果保持在 Git 之外。

### 文档和协作

- 重写 `deploy/offline/README.zh-CN.md`，分别说明 Ubuntu WSL 制备、公司 CentOS WSL 部署评估、公司 Win11/CodeHub LFS 同步。
- 更新根目录和 OpenROAD-3D 文档，说明公司双 DEF 入口和 backend-only 部署边界。
- 增加 `.gitattributes`、`.gitignore` 和源码/制品发布约束，避免大文件及运行产物进入源码历史。

### 验证

- 双 DEF 转换器单元测试覆盖正常合并、cell/fakeram master 后缀、HBT 生成、HBT 缺失、坐标不一致和重复外部 IO。
- Python 脚本通过编译检查。
- Shell 脚本通过 `bash -n`。
- Makefile company config 通过 dry-run 接口检查。
- 修改通过 `git diff --check`。

### 尚待真实公司数据确认

- top/bottom DEF 中普通 IO、SPECIALNETS、ROWS 和 HBT 的实际生成约定；
- 四个 case 的 top module、综合网表版本、SDC、fakeram master 集合和 die area；
- `HBT[n]` 两侧坐标是否严格一致以及信号方向定义；
- eval Docker 内实际 OpenROAD 版本的完整 route/timing 回归；
- CodeHub 的 LFS 单文件、仓库容量和 push 超时策略。
