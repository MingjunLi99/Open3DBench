# 公司环境部署适配修改日志

本文件记录 `huawei-partition` 分支针对公司离线环境和公司 3D placer 的适配。后续提交按时间倒序追加，记录行为变化、兼容性影响、验证结果和遗留事项；不要在此写入公司 URL、账号、token、license server、内部 PDK 路径或专有 DEF 内容。

## 2026-08-24：修复 company flow 的 STA 报告兼容性

- 修复 eval image 中 OpenSTA 2.6.0 不支持 `report_wns/report_tns -max/-min` 而导致 `global_route.tcl` 报 `STA-0562` 的问题；setup/hold WNS、TNS 现分别通过 OpenSTA min/max API 生成。
- setup/hold 路径报告改用该版本明确支持的 field 名称，继续默认各输出 100 条路径。
- ideal-clock reset false path 只施加到当前设计实际存在的 port，并补充 Swerv 的 `rst_l` 和 TinyRocket 的 `reset`，不再因其他 case 的 reset 名称不存在而产生 `STA-0101/STA-0472`。
- 新增脚本兼容性和 Tcl mock 回归测试，覆盖 Ariane、BP、Swerv、TinyRocket 使用的 reset 名称，以及 setup/hold summary/path 报告生成。

## 2026-08-24：三种 company 实验模式和阶段化 timing 报告

### Route mode

- 新增共享配置 `flow/designs/nangate45_3D/config_company_route_modes.mk`，四个 company case 共同引用。
- `run_company_3d.sh` 新增 `--route-mode postplace|quick|quality`：postplace 只运行 GR 并停止；quick 使用 GR/DR 各 5 轮；quality 使用 GR 50 轮、DR 默认停止条件。
- 默认模式由 quality 改为 quick；不写参数等价于 `--route-mode quick`。
- 新增 `do-company-postplace`/`do-company-flow`，postplace 不进入 Detailed Routing 和 Finish，也不支持 `--hotspot`。
- 三种模式分别使用 `company_postplace`、`company_quick`、`company_quality` 作为 `FLOW_VARIANT`，隔离 results、logs 和 reports。

### Reports

- Global Routing 报告从 `congestion.rpt` 改名为 `postplace_global_congestion.rpt`，并新增 `postplace_congestion.webp`（部分构建可能为 `.webp.png`）。
- Finish 将 `5_route_drc.rpt` 复制为 `final_detailed_route_drc.rpt`；继续生成 final congestion 图片。
- 新增 `postplace_timing.rpt`：GR 后 `estimate_parasitics -global_routing` 的 setup/hold 报告。
- 新增 `final_timing.rpt`：Finish 中 OpenRCX extraction、SPEF 回读后的 setup/hold 报告。
- Timing 报告默认各输出 100 条路径，可用 `TIMING_REPORT_PATH_COUNT` 调整；company config 仍使用 `IDEAL_CLOCK=1`，不等同 signoff OCV/MMMC STA。
- congestion `.rpt` 是 overflow marker 报告；无 overflow 时部分 OpenROAD 版本不会创建空文件，需结合 `5_1_grt.log` 判断 GR 是否完成。

### 文档和验证

- 重写 `DEPLOY_README.zh-CN.md`，主线改为 CodeHub clone → CentOS 首次安装 Docker/加载镜像 → 启动容器 → 选择 route mode 运行 company 实验，并区分首次部署、WSL 重启和日常运行步骤。
- 文档补充可选参数、输出目录、reports/results/logs 内容和 timing/congestion/DRC 解释。
- 部署指南中的 company 命令改为使用容器内 `/workspace/company-input/<design>_{top,bot}.def` 完整路径，并补充 DEF 转换、legalization、routing、finish 的流程图及 results/reports 目录树。
- Bash 语法、Make mode 选择、`git diff --check` 和现有 9 个 Python 单元测试通过；尚未在缺少 OpenROAD/Tcl 的当前 WSL 做端到端报告生成验证。

## 2026-08-17：忽略 backend evaluation 运行产物

- `OpenROAD-3D/.gitignore` 新增 `flow/logs/`、`flow/reports/` 和 `flow/results/`，并将已有 `flow/objects` 规范为目录规则。
- 因此 OpenROAD backend flow 生成的日志、JSON metrics、ODB、DEF、SPEF、DRC 报告、布局图片和 HotSpot 输出不会进入 CodeHub 提交；源码、设计配置、脚本和文档仍正常跟踪。
- 部署指南的 CodeHub 初始化段明确：不得用 `git add -f` 加入这些运行产物或公司输入 DEF，评估归档须在仓库外按公司规定保存。
- 公司 CodeHub 首次初始化和后续默认开发分支改为 `main`；制备机上的 GitHub 适配分支仍可保留原名 `huawei-partition`，两者不要求同名或共享历史。

## 2026-08-14：收敛为单仓库 OpenROAD-3D eval 流程

### 目录规范化

- 新建根目录 `script/`，集中存放 Docker 静态安装、WSL daemon 启动和 eval image 加载脚本。
- 新建根目录 `doc/`，集中存放中文部署指南和本修改日志；仓库根目录只保留 `README.md`。
- 删除原 `deploy/offline/` 空目录，并同步更新 README、脚本提示和部署命令中的有效路径。
- 中文部署指南进一步重命名为 `doc/DEPLOY_README.zh-CN.md`，并同步修正根 README 和 OpenROAD-3D README 的导航链接。
- 公司 DEF debug prompt 移至本地 `tmp/`，不再通过 Git 或离线工程压缩包同步；需要时由使用者单独手工复制。

### 仓库范围

- 从 `huawei-partition` 工作树删除 `Place-LoL` 和 `Place-MoL`；本分支不再支持公开 placer 或 placer-complete 复现。
- 根目录和 `OpenROAD-3D` README 改为只介绍公司 placer top/bottom DEF 转换及 OpenROAD-3D backend evaluation。
- `OpenROAD-3D/start_docker_eval.sh` 删除 Place-LoL 自动探测、挂载和 `PLACE_LOL_ROOT` 环境变量。

### 单仓库与 Git LFS

- 根目录新增 `docker/`，包含 `docker-26.1.4.tgz` 和 `open3dbench-eval.docker.tar`。
- `.gitattributes` 为这两个固定路径配置 Git LFS；删除 `.gitignore` 对 `*.docker.tar` 的全局排除。
- CodeHub 只使用一个 repo；不再拆分源码 repo 和 offline-artifacts repo。
- GitHub public fork 不再提交这两个新 LFS 对象：`.gitignore` 精确排除本地 Docker 文件，但 Ubuntu 离线工作树归档仍包含它们。
- 公司 Win11 初始化 CodeHub repo 时执行 `git lfs track`，再用 `git add -f` 将两个被忽略的文件作为 LFS 对象加入同一个公司仓库。

### 部署简化

- 删除 placer、release、source bundle 和 checksum 专用脚本，只保留 Docker 静态安装、WSL daemon 启动和 eval image 加载脚本。
- 重写 `deploy/offline/README.zh-CN.md`：Ubuntu 直接打包不含 `.git` 的工作树，CentOS WSL 解压并测试，Win11 对测试通过的目录执行 `git init`、Git LFS track、首次 commit 和 push。
- 不再生成或校验 release bundle、源码 bundle、SHA256SUMS，也不在 Win11 建立第二个 artifacts repo。

### 验证

- 保留的 shell 脚本通过语法检查；文档和属性修改通过 `git diff --check`。
- 两个 Docker 大文件已移动到根目录 `docker/`，总大小约 560 MiB。
- 当前 Ubuntu 尚未安装 Git LFS；在公司 Win11 首次 `git add` 前必须先执行 `git lfs install` 和两个精确路径的 `git lfs track`。

## 2026-08-13：为 backend-only release 增加离线 Git bundle

### 源码 bundle 与 release 传输

- `deploy/offline/make_backend_source_bundle.sh` 现在只生成 backend-only `.bundle`，供公司 CentOS WSL 初始 clone；不再生成重复的源码 `.tar.gz`。
- `deploy/offline/make_source_bundle.sh` 现在只生成完整源码 `.bundle`，placer-complete 同样由 CentOS 初始 clone。
- `prepare_release.sh` 使用 `bash` 调用两个源码 bundle builder，避免历史文件模式为 `100644` 时 placer-complete 制备失败。
- backend Git bundle 是由当前 upstream commit 导出的精简源码创建的 `huawei-partition` 单提交快照，不含 `Place-LoL`、`Place-MoL` 或原仓库完整历史。
- `BACKEND_SOURCE_MANIFEST.txt` 记录 upstream commit、bundle 分支和单提交快照属性；`BACKEND_SOURCE_SHA256SUMS` 校验 bundle。
- bundle 在 Linux 制备机创建，保留 shell 脚本的 Git executable bit；项目 `.gitattributes` 继续保证 `.sh`、`.py`、`.tcl` 和 `Makefile` 使用 LF。
- eval-only 和 placer-complete 的 source/ 现在只保留对应 Git bundle，不再生成重复的源码 `.tar.gz`。

### Win11 与 CodeHub 文档

- 明确在 CentOS WSL 中从 `source/` 定位并 clone backend-only bundle；无需解压源码归档或访问 GitHub。
- 增加 `git bundle list-heads`、本地 clone、clone 后 `git bundle verify`、分支/commit/status 检查以及关键脚本 `100755` 模式检查。
- clone 时显式指定 `--branch huawei-partition`，避免 bundle 未记录默认 HEAD 时落入空的 `master` 分支。
- 说明 clone 后的 `origin` 指向本地 bundle，推送 CodeHub 前应将其替换为公司远程 URL。
- 区分 eval-only 单提交快照 bundle 和 placer-complete 完整历史 bundle。
- 删除 Win11 解压源码 tar、重建 repo 和恢复 executable bit 的旧备用流程。

### 验证

- `make_backend_source_bundle.sh` 和 `prepare_release.sh` 通过 shell 语法检查。
- backend bundle 通过 `git bundle verify`，可在无网络临时目录中 clone 为 `huawei-partition`。
- clone 后抽查公司评估入口和离线部署脚本的 Git 文件模式为 `100755`。
- 文档和脚本修改通过 `git diff --check`。

### Release 归档结构说明补充

- README 增加 eval-only backend bundle clone 后的文件树，明确 `deploy/offline/` 位于源码工作树内部，而不是 release 根目录。
- 增加 placer-complete 完整源码归档的顶层目录和 `Place-LoL`/`Place-MoL` 结构示意。
- 说明两种 release 都必须先 clone 对应 bundle，之后才能执行 `deploy/offline/*.sh`。

### 公司本地修改与 CodeHub 推送流程

- 第三部分调整为直接在 `huawei-partition` 上进行公司本地修改、测试和提交，不再要求额外创建 feature branch 或进行 review。
- 明确禁止将公司 DEF、ODB、日志、license 和运行结果加入源码仓库。
- 测试通过后在 Win11 创建新的 CodeHub 仓库，并直接 push `huawei-partition`；若修改发生在 CentOS WSL，则通过 `git bundle create` 将该分支带到 Win11。
- 新增 `deploy/offline/COMPANY_DEF_AGENT_PROMPT.zh-CN.md`，提供给公司电脑 agent 的只读调查、最小修改和验证提示词模板。
- 源码传输流程进一步收敛为 Ubuntu 制备初始 release、CentOS WSL 修改/测试/提交、Win11 接收 CentOS 导出的已测试 bundle 并推送 CodeHub；删除 Ubuntu 直接向 Win11 导入源码 repo 的开发路径。
- 新增 `deploy/offline/export_tested_source_bundle.sh`，在 CentOS WSL 中检查 clean working tree 后导出当前 `huawei-partition`，并生成 SHA256 文件。
- README 的 backend-only 文件树加入该导出脚本；placer-complete 的完整 bundle 同样只作为 CentOS 初始 clone 输入，不再作为 Win11 直接导入源码 repo 的路径。
- `1.4` 的整体 release 传输方式改为 Ubuntu 生成单个不分卷 `.tar.gz`，仅保留 CentOS WSL 解压说明，移除 Win11 解压 ZIP 说明。

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
