# Open3DBench 公司环境部署与使用指南

本指南面向公司同事：从 CodeHub 获取工程，部署到离线 CentOS WSL，并运行公司 3D placer 的 top/bottom DEF backend evaluation。支持 `ariane`、`bp`、`swerv_wrapper`、`tinyRocket`，不运行 Place-LoL/Place-MoL。

## 1. CodeHub 到 CentOS（首次部署）

Win11 用于 CodeHub，CentOS WSL 用于 Docker/OpenROAD。工程应放在 WSL ext4（如 `/root/Workspace/Open3DBench`），不要直接在 `/mnt/c`、`/mnt/d` 运行。

首次在 Win11 clone：`git lfs install`（当前用户只需一次），然后 `git clone <CODEHUB_REPO_URL> Open3DBench`、进入目录并执行 `git lfs pull`。确认 `docker/docker-26.1.4.tgz` 和 `docker/open3dbench-eval.docker.tar` 是实际大文件而不是 LFS pointer。

在 CentOS WSL 复制（不会产生第二层 `Open3DBench/Open3DBench`）：

```bash
mkdir -p /root/Workspace
tar -C /mnt/d/Workspace -cf - Open3DBench | tar -C /root/Workspace -xf -
cd /root/Workspace/Open3DBench
```

首次安装 Docker 26（root；不要使用 yum 的 Docker 1.13.1）：

```bash
bash script/install_docker_static.sh docker/docker-26.1.4.tgz
```

首次部署、或每次 WSL 完全退出后启动 daemon：`bash script/start_docker_wsl.sh`。首次部署或镜像更新后加载 eval image：`bash script/load_images.sh docker/open3dbench-eval.docker.tar`。

## 2. 启动容器和运行实验

将公司 DEF 放在仓库外，例如 `/root/Workspace/freePartitioner/output_openroad/`，在 host 执行：

```bash
cd /root/Workspace/Open3DBench/OpenROAD-3D
COMPANY_PLACER_OUTPUTS=/root/Workspace/freePartitioner/output_openroad ./start_docker_eval.sh
```

容器内工程为 `/workspace/OpenROAD-3D`，输入为只读的 `/workspace/company-input`，默认进入 `/workspace/OpenROAD-3D/flow`，网络为 `none`。

```bash
# 默认 quick：global routing (GR) 5 轮、detail routing (DR) 5 轮、Finish
./run_company_3d.sh swerv_wrapper \
  /workspace/company-input/swerv_wrapper_top.def \
  /workspace/company-input/swerv_wrapper_bot.def

# postplace：GR 5 轮后输出报告并停止，不运行 DR/Finish
./run_company_3d.sh swerv_wrapper \
  /workspace/company-input/swerv_wrapper_top.def \
  /workspace/company-input/swerv_wrapper_bot.def \
  --route-mode postplace

# quality：GR 50 轮、DR 默认停止条件、Finish
./run_company_3d.sh swerv_wrapper \
  /workspace/company-input/swerv_wrapper_top.def \
  /workspace/company-input/swerv_wrapper_bot.def \
  --route-mode quality
```

这里必须使用容器内的完整 DEF 路径。`start_docker_eval.sh` 把 host 的 placer 输出目录只读挂载为 `/workspace/company-input`，而脚本当前工作目录是 `/workspace/OpenROAD-3D/flow`；因此 `top.def bot.def` 只有在这两个文件确实位于当前 flow 目录时才成立。

完整语法：`run_company_3d.sh <ariane|bp|swerv_wrapper|tinyRocket> <top.def> <bot.def> [--route-mode postplace|quick|quality] [--output DIR] [--hotspot]`。`--hotspot` 只能用于 quick/quality。

三种模式共用 `flow/designs/nangate45_3D/config_company_route_modes.mk`；timing 路径默认各 100 条，可用 `TIMING_REPORT_PATH_COUNT=300` 临时调整。

### 2.1 当前整体 flow

company 入口先把两个 die DEF 合并并转换，再完成上下 die 的独立 legalization 和坐标重组，生成可供 OpenROAD-3D routing 使用的 `4_cts.odb`。之后的标准 routing/finish 链如下：

```text
company top.def + bottom.def
          │
          ▼
merged double-metal-stacking DEF
          │  read_def / split upper-bottom / legalization / reintegration
          ▼
4_cts.odb                 CTS/placement 后的 3D 数据库
          │
          │ do-route
          ▼
5_1_grt.odb               Global Routing（生成 route.guide）
          │
          ▼
5_2_route.odb             Detailed Routing
          │
          ▼
5_route.odb               routing 阶段标准输出
          │
          │ do-finish
          ▼
6_1_fill.odb               可选 density fill；当前通常是复制 5_route.odb
          │
          ▼
6_final.odb
6_final.def
6_final.v
6_final.sdc
6_final.spef                 OpenRCX 提取后的寄生参数
          │
          ▼
final metrics / timing / DRC / congestion reports
```

`postplace` 模式执行到 `5_1_grt.odb` 后停止，不执行后续的 Detailed Routing 和 Finish；因此它只产生 postplace 报告，不会产生 `5_route_drc.rpt`、`final_timing.rpt` 或 `6_final.*`。

## 3. 输出目录和报告

```text
flow/reports/nangate45_3D/<内部设计名>/company_<mode>/
flow/results/nangate45_3D/<内部设计名>/company_<mode>/
flow/logs/nangate45_3D/<内部设计名>/company_<mode>/
```

所有模式：`postplace_global_congestion.rpt`、`postplace_congestion.webp`（部分构建为 `.webp.png`）、`postplace_timing.rpt`。无 Global Routing overflow 时，部分 OpenROAD 版本不会创建空 congestion `.rpt`，应结合 `5_1_grt.log` 判断。

quick/quality 另有：`5_route_drc.rpt`、`final_detailed_route_drc.rpt`、`final_timing.rpt`、`final_congestion.webp` 及 final routing/placement/clocks/resizer 图片。Timing report 包含 setup/max、hold/min 的 WNS、TNS 和最差路径；`IDEAL_CLOCK=1`，不等同 signoff OCV/MMMC STA。

postplace results 主要为 `4_cts.odb`、`4_cts.sdc`、`5_1_grt.odb`、`route.guide`；完整模式还生成 `5_2_route.odb`、`5_route.odb`、`6_final.odb/def/v/sdc/spef`。看到 DRT `running iteration N` 表示 GR 已结束、正在 DR。

### 3.1 results 目录示例

以 `swerv_wrapper` 的 `quick` 完整实验为例：

```text
flow/results/nangate45_3D/swerv_wrapper/company_quick/
├── 1_synth.sdc
├── 4_cts.odb
├── 4_cts.sdc
├── 5_1_grt.odb
├── route.guide
├── 5_2_route.odb
├── 5_route.odb
├── 5_route.sdc
├── 6_1_fill.odb
├── 6_1_fill.sdc
├── 6_final.odb
├── 6_final.def
├── 6_final.v
├── 6_final.sdc
└── 6_final.spef
```

`postplace` 目录通常在 `5_1_grt.odb` 和 `route.guide` 后结束；`quality` 的文件名相同，只是目录名为 `company_quality`。合并输入 DEF 另存于 `flow/results/company/<design>/<design>.merged.def`。

### 3.2 reports 目录示例

```text
flow/reports/nangate45_3D/swerv_wrapper/company_quick/
├── postplace_global_congestion.rpt
├── postplace_congestion.webp       # 有的构建为 .webp.png
├── postplace_timing.rpt
├── 5_route_drc.rpt
├── final_detailed_route_drc.rpt
├── final_timing.rpt
├── final_congestion.webp
├── final_routing.webp
├── final_placement.webp
├── final_clocks.webp
└── final_resizer.webp
```

postplace 实验只应查看前三项；DRC/final 项不存在是因为流程有意提前停止，而不是运行失败。

## 4. 更新与数据管理

CentOS 无网时先在 Win11 执行 `git pull --ff-only`、`git lfs pull`，再复制到 WSL；不要在 OpenROAD 运行期间覆盖脚本。普通使用者只需 `git lfs install`/`git lfs pull`；维护者首次建立 CodeHub 或更新 Docker 制品时才需 `git lfs track`。禁止提交公司 DEF、运行目录、ODB、SPEF、报告和图片，实验归档放在仓库外。
