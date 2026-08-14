# Open3DBench 公司环境简化部署

本文只支持一种流程：公司 placer 生成 top/bottom DEF，OpenROAD-3D 负责转换和 backend evaluation。不包含或运行 Place-LoL、Place-MoL。

代码和离线大文件最终保存在同一个 CodeHub repo：

```text
Open3DBench/
├── OpenROAD-3D/
├── script/
│   ├── install_docker_static.sh
│   ├── start_docker_wsl.sh
│   └── load_images.sh
├── doc/
│   ├── README.zh-CN.md
│   ├── COMPANY_DEF_AGENT_PROMPT.zh-CN.md
│   └── COMPANY_DEPLOY_CHANGELOG.md
├── docker/
│   ├── docker-26.1.4.tgz
│   └── open3dbench-eval.docker.tar
├── .gitattributes
└── .gitignore
```

`docker/` 中两个大文件在当前 GitHub fork 中由 `.gitignore` 排除，但仍会进入 Ubuntu 制作的离线传输压缩包；测试通过后，在公司 Win11 初始化 CodeHub repo 时再通过 Git LFS 强制加入。公司 DEF、运行日志、ODB、route 结果和报告不得提交。

## 第一部分：Ubuntu 制备并传入公司 CentOS

### 1.1 确认文件

在 Open3DBench 根目录执行：

```bash
test -s docker/docker-26.1.4.tgz
test -s docker/open3dbench-eval.docker.tar
test -f OpenROAD-3D/flow/util/convert_company_3d_def.py
```

当前 Ubuntu 不需要安装 Docker；两个 Docker 文件已经准备好。

### 1.2 打包工作树

在 Open3DBench 的上一级目录执行。压缩包不包含当前 Git 历史、旧 `offline-dist`、临时文件和 OpenROAD 运行结果：

```bash
cd /home/mjli/Workspace/3DIC/flow

tar -czf Open3DBench-company.tar.gz \
  --exclude='Open3DBench/.git' \
  --exclude='Open3DBench/.agents' \
  --exclude='Open3DBench/.codex' \
  --exclude='Open3DBench/.vscode' \
  --exclude='Open3DBench/offline-dist' \
  --exclude='Open3DBench/tmp' \
  --exclude='Open3DBench/OpenROAD-3D/flow/logs' \
  --exclude='Open3DBench/OpenROAD-3D/flow/reports' \
  --exclude='Open3DBench/OpenROAD-3D/flow/results' \
  Open3DBench
```

将 `Open3DBench-company.tar.gz` 通过 scp 或 U 盘复制到公司电脑，再放到公司 WSL 可访问的位置，例如：

```text
/mnt/d/Workspace/Open3DBench-company.tar.gz
```

## 第二部分：公司 CentOS WSL 部署和测试

### 2.1 解压

```bash
mkdir -p /root/Workspace
tar -xzf /mnt/d/Workspace/Open3DBench-company.tar.gz \
  -C /root/Workspace
cd /root/Workspace/Open3DBench
```

源码和运行目录位于 WSL ext4；不要直接在 `/mnt/d` 上运行 OpenROAD。

### 2.2 安装并启动 Docker

不要使用公司 yum 源中的 Docker 1.13.1。安装随仓库提供的 Docker 26：

```bash
bash script/install_docker_static.sh \
  docker/docker-26.1.4.tgz
bash script/start_docker_wsl.sh
docker version
```

WSL 完全退出后 dockerd 会停止。重新进入 WSL 后执行：

```bash
cd /root/Workspace/Open3DBench
bash script/start_docker_wsl.sh
```

### 2.3 加载 eval 镜像

```bash
bash script/load_images.sh \
  docker/open3dbench-eval.docker.tar
```

运行容器：

```bash
cd /root/Workspace/Open3DBench/OpenROAD-3D
COMPANY_PLACER_OUTPUTS=/root/Workspace/freePartitioner/output_openroad \
  ./start_docker_eval.sh
```

### 2.4 公司 DEF 目录

```text
/root/Workspace/freePartitioner/output_openroad/
├── swerv_wrapper_top.def
└── swerv_wrapper_bot.def
```

其他设计使用相同命名方式：

```text
ariane_top.def / ariane_bot.def
bp_top.def / bp_bot.def
tinyRocket_top.def / tinyRocket_bot.def
```

转换约定：

- top/bottom instance 分别增加 `_top`、`_bot`；
- cell/fakeram master 分别增加 `_upper`、`_bottom`；
- 成对的 `HBT[n]` DEF PIN 转换为 `HBT_n` pseudo-cell；
- top/bottom local net 分别增加 `_TOP`、`_BOT`；
- HBT 的两侧坐标、方向、net 引用必须符合实际 DEF 和 OpenROAD-3D 输入要求。

### 2.5 转换和评估

在 eval 容器中先单独运行转换：

```bash
cd /workspace/OpenROAD-3D/flow
python3 util/convert_company_3d_def.py \
  --top /workspace/company-input/swerv_wrapper_top.def \
  --bottom /workspace/company-input/swerv_wrapper_bot.def \
  --output /tmp/swerv_wrapper.merged.def
```

完整 backend evaluation：

```bash
./run_company_3d.sh swerv_wrapper \
  /workspace/company-input/swerv_wrapper_top.def \
  /workspace/company-input/swerv_wrapper_bot.def
```

支持：

```text
ariane  bp  swerv_wrapper  tinyRocket
```

添加 HotSpot：

```bash
./run_company_3d.sh swerv_wrapper \
  /workspace/company-input/swerv_wrapper_top.def \
  /workspace/company-input/swerv_wrapper_bot.def \
  --hotspot
```

主要结果位于：

```text
OpenROAD-3D/flow/results/nangate45_3D/<design>/company/
OpenROAD-3D/flow/logs/nangate45_3D/<design>/company/
OpenROAD-3D/flow/reports/nangate45_3D/<design>/company/
```

公司 Windows agent 修改转换器时，使用 `doc/COMPANY_DEF_AGENT_PROMPT.zh-CN.md`。修改后的文件必须回到 CentOS WSL 完成实际 DEF 和 backend 测试。

## 第三部分：Win11 创建单一 CodeHub repo

测试通过后，将 `/root/Workspace/Open3DBench` 复制到 Win11，例如：

```text
D:\Workspace\Open3DBench
```

在 PowerShell 中执行：

```powershell
Set-Location D:\Workspace\Open3DBench

git init
git checkout -b huawei-partition
git lfs install
git lfs track "docker/docker-26.1.4.tgz"
git lfs track "docker/open3dbench-eval.docker.tar"

git add .
git add -f `
  docker/docker-26.1.4.tgz `
  docker/open3dbench-eval.docker.tar
git commit -m "Initial Open3DBench company backend"
git remote add origin <CODEHUB_REPO_URL>
git push -u origin huawei-partition
```

提交前确认大文件由 LFS 管理：

```powershell
git lfs ls-files
git status
```

这里必须使用 `git add -f`，因为这两个本地离线文件在从 GitHub 传来的 `.gitignore` 中被精确排除；`.gitattributes` 已保证强制加入时写入 Git 索引的是 LFS pointer，而不是原始大文件。

后续同事只使用这一个 repo：

```powershell
git lfs install
git clone <CODEHUB_REPO_URL>
git checkout huawei-partition
git lfs pull
```

CodeHub 中不需要第二个 artifacts repo，也不需要 release bundle、checksum、source tar 或单独的 Docker 制品仓库。
