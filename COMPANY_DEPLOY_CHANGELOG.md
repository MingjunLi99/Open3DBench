# 公司环境部署适配修改日志

本文件记录 `huawei-partition` 分支针对公司离线环境和公司 3D placer 的适配。后续提交按时间倒序追加，记录行为变化、兼容性影响、验证结果和遗留事项；不要在此写入公司 URL、账号、token、license server、内部 PDK 路径或专有 DEF 内容。

## 2026-08-13：为 backend-only release 增加离线 Git bundle

### 源码双载体

- `deploy/offline/make_backend_source_bundle.sh` 现在同时生成两个 backend-only 源码载体：
  - `.tar.gz` 供公司 CentOS WSL 直接解压部署；
  - `.bundle` 供公司 Win11 从本地克隆、验证后推送到 CodeHub。
- backend Git bundle 是由当前 upstream commit 导出的精简源码创建的 `huawei-partition` 单提交快照，不含 `Place-LoL`、`Place-MoL` 或原仓库完整历史。
- `BACKEND_SOURCE_MANIFEST.txt` 记录 upstream commit、bundle 分支和单提交快照属性；`BACKEND_SOURCE_SHA256SUMS` 同时校验 tar 与 bundle。
- bundle 在 Linux 制备机创建，保留 shell 脚本的 Git executable bit；项目 `.gitattributes` 继续保证 `.sh`、`.py`、`.tcl` 和 `Makefile` 使用 LF。

### Win11 与 CodeHub 文档

- 明确先解压外层 release ZIP，再从 `source/` 定位 backend-only bundle；无需解压 source tar 或访问 GitHub。
- 增加 `git bundle list-heads`、本地 clone、clone 后 `git bundle verify`、分支/commit/status 检查以及关键脚本 `100755` 模式检查。
- clone 时显式指定 `--branch huawei-partition`，避免 bundle 未记录默认 HEAD 时落入空的 `master` 分支。
- 说明 clone 后的 `origin` 指向本地 bundle，推送 CodeHub 前应将其替换为公司远程 URL。
- 区分 eval-only 单提交快照 bundle 和 placer-complete 完整历史 bundle。
- 将 Win11 解压 backend tar 后重建 repo 降为备用方案，并补充 LF、NTFS executable bit 风险和显式 `git update-index --chmod=+x` 恢复步骤。

### 验证

- `make_backend_source_bundle.sh` 和 `prepare_release.sh` 通过 shell 语法检查。
- backend bundle 通过 `git bundle verify`，可在无网络临时目录中 clone 为 `huawei-partition`。
- clone 后抽查公司评估入口和离线部署脚本的 Git 文件模式为 `100755`。
- 文档和脚本修改通过 `git diff --check`。

### Release 归档结构说明补充

- README 增加 eval-only backend tar/bundle 内部文件树，明确 `deploy/offline/` 位于源码归档内部，而不是 release 根目录。
- 增加 placer-complete 完整源码归档的顶层目录和 `Place-LoL`/`Place-MoL` 结构示意。
- 说明两种 release 都必须先解压源码 tar 或 clone bundle，之后才能执行 `deploy/offline/*.sh`；补充不解压查看 tar 内容的命令。

## 2026-08-13：简化 ExFAT 离线发布与公司目录约定

### 变更范围

- 基于上次提交 `b1246b74`（`support deploy to CentOS7.9 WSL, and conversion parser for OpenROAD-style 2 separate die DEFs to 1 Open3DBench-style double-metal stacking DEF`）。
- 本次提交只调整离线 release 制备、校验、传输文档和公司 DEF 示例路径；不改变双 DEF 转换算法、HBT 建模或 OpenROAD backend 主流程。

### Release 制备与大文件处理

- 简化 `deploy/offline/prepare_release.sh`：
  - eval-only 默认读取 `offline-dist/docker/docker-26.1.4.tgz` 和 `offline-dist/images/open3dbench-eval.docker.tar`；
  - placer-complete 额外默认读取完整的 `open3dbench-place.docker.tar`、`benchmarks_lol.tar.gz` 和 `binaries.tar.gz`；
  - 默认输出分别固定为 `offline-dist/releases/Open3DBench-eval-only` 和 `offline-dist/releases/Open3DBench-placer-complete`；
  - 移除 `--split-size` 和 release 自动分卷逻辑；输入必须是完整 archive；
  - 输出为可整体复制到 ExFAT U 盘的自包含 release 目录，而不是单个总压缩包；
  - 完成时打印输出目录、校验命令和 U 盘复制提示；
  - 保持发布保护：源码从当前 `HEAD` 导出，working tree 包含已修改或未跟踪文件时拒绝制备。
- 已将历史 place image 分卷重组为完整 `offline-dist/images/open3dbench-place.docker.tar`；该大文件继续由 `.gitignore` 排除，不进入源码提交。
- 删除仅用于历史分卷重组的 `deploy/offline/assemble_parts.sh`。
- 移除 `deploy/offline/load_images.sh` 对 `.part-000` 的流式加载支持，只接受完整 `.tar`、`.tar.gz` 或 `.tgz` image archive。
- `deploy/offline/verify_bundle.sh` 校验成功后明确提示不会生成或修改文件。

### 部署、传输和 CodeHub 文档

- 重写并细化 `deploy/offline/README.zh-CN.md` 的三部分操作：
  - Ubuntu WSL 制备 eval-only 或 placer-complete release；
  - 公司 CentOS 7.9 WSL2 安装 Docker、加载 eval image、转换公司 DEF并运行 backend evaluation；
  - 公司 Windows 11 使用普通 Git 和 Git LFS 同步源码与离线制品到 CodeHub。
- 明确当前 Ubuntu WSL 只打包现成 Docker image archive 时不需要安装 Docker；仅在重新 pull/save 镜像或本机运行容器测试时需要容器运行时。
- 修正 `offline-dist/SHA256SUMS` 的相对路径校验方式：从仓库根目录使用 `verify_bundle.sh offline-dist`，或进入 `offline-dist` 后执行 `sha256sum --check`。
- 公司 WSL release 示例位置改为 `/mnt/d/Wrokspace/Open3DBench-eval-only`，WSL ext4 工作区统一改为 `/root/Workspace`。
- 增加将完整 release 目录封装为不分卷 ZIP64 单文件的可选命令：使用 store 模式避免重复压缩，便于 SCP 和 ExFAT U 盘传输，并给出 CentOS WSL、Windows 11 和 7-Zip 解压说明。
- CodeHub LFS 示例不再跟踪 `*.part-*`，完整 `.tar`、`.tar.gz`、`.tgz` 和 `.bundle` 由 LFS 管理。

### 公司 placer 输出约定

- 公司 DEF 示例目录改为 `/root/Workspace/freePartitioner/output_openroad`。
- 采用扁平命名 `<design>_top.def` 和 `<design>_bot.def`，例如 `swerv_wrapper_top.def`、`swerv_wrapper_bot.def`。
- 更新 `OpenROAD-3D/README.md`、`run_company_3d.sh` usage、容器挂载、独立转换和 backend evaluation 示例。
- 转换器本身通过显式 `--top`/`--bottom` 参数接收任意路径，因此无需修改转换逻辑。

### 验证

- 完整 place Docker archive 可正常读取，SHA256 为 `10c21ac2eb138e3e152973150158f81b6527ffea2586b1bbc350a7496cb202e8`。
- `offline-dist` 中 Docker 静态包、eval/place image 和 LoL 数据通过统一 `SHA256SUMS` 校验；这些制品不进入 Git 提交。
- ZIP 命令使用当前 Ubuntu WSL 的 Info-ZIP 3.0 完成小型目录创建和 `unzip -t` 回归测试。
- 修改后的 shell 脚本通过 `bash -n`，文档和代码通过 `git diff --check`。

### 兼容性说明

- 新 release 不兼容 `.part-*` 输入；若其他环境仍保存旧分卷，需在升级前自行重组为完整 archive。
- Windows 自带文件管理器或 `Expand-Archive` 对超大 ZIP64 的支持可能受系统版本影响，失败时使用 7-Zip。
- CodeHub 的 LFS 单文件大小、仓库配额、push 超时和权限策略仍需在公司环境确认。

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
