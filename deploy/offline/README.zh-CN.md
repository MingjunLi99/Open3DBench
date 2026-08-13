# Open3DBench 公司环境离线部署与 CodeHub 同步

本文档面向以下固定环境：

- 制备机：当前可联网的 Ubuntu WSL，源码分支为 `huawei-partition`；
- 目标机：公司 Windows 11 内的 CentOS 7.9 WSL2，不能访问公网；
- 公司 WSL：`x86_64`、cgroup v2、PID 1 不是 systemd；
- 公司 yum 源只提供 Docker 1.13.1；
- 公司 placer 输出 Nangate45 top/bottom DEF，HBT 是名为 `HBT[n]` 的 DEF PIN；
- 公司 CodeHub 支持 Git LFS。

文档分为三部分：

1. 在 Ubuntu WSL 制备离线部署包；
2. 在公司 CentOS WSL 部署并运行 backend evaluation；
3. 在公司 Win11 将源码和离线制品同步到 CodeHub。

## 0. 方案选择和安全边界

### Eval-only，推荐用于公司日常评估

只部署：

- `OpenROAD-3D` 和 `deploy/offline`；
- `shiyunqi/open3dbench:eval` 镜像；
- Docker 26.1.4 静态包；
- 公司 placer 产生的 top/bottom DEF。

不包含 `Place-LoL`、`Place-MoL`、公开 LoL placer、LoL benchmark 和 place 镜像。该方案体积更小，也符合当前“公司 placer + OpenROAD-3D 评估”的需求。

### Placer-complete，用于保留公开 LoL 复现能力

在 eval-only 基础上额外包含：

- 完整 Open3DBench 源码和 Git bundle；
- `shiyunqi/open3dbench:place` 镜像；
- `benchmarks_lol.tar.gz`；
- `binaries.tar.gz`。

本文件只说明如何制备和部署这些文件；暂不说明如何运行公开 Place-LoL placer。

### 安全边界

不要安装公司 yum 源中的 Docker 1.13.1。它早于 cgroup v2 支持，不能可靠运行本工程容器。本文使用 Docker 26.1.4 静态发行包，并以无 bridge、无 iptables 的方式手动启动 daemon。

Open3DBench 容器默认使用 `--network none`。Docker daemon 是高权限软件，安装前仍应完成公司的软件、开源和信息安全审批。

不得提交或打包到源码仓库：

- 公司 placer 源码、二进制、许可证和内部路径；
- 公司 top/bottom DEF；
- 运行日志、ODB、route 结果和评估报告；
- CodeHub token、账号、license server 或其他凭据。

## 第一部分：在 Ubuntu WSL 制备部署文件

### 1.1 前置检查

在 Open3DBench 根目录执行：

```bash
git switch huawei-partition
git status --short
git rev-parse HEAD
```

制备脚本从当前 `HEAD` 导出源码，因此应先提交本次适配修改，并保持 working tree clean。将 commit ID 记录在发布说明中。

确认本机存在 Docker 静态包：

```text
/path/to/docker-26.1.4.tgz
```

确认 eval 镜像已经拉取并导出：

```bash
docker pull shiyunqi/open3dbench:eval
docker image inspect shiyunqi/open3dbench:eval \
  --format '{{.Id}} {{.Architecture}} {{.Os}}'
docker save -o /path/to/open3dbench-eval.docker.tar \
  shiyunqi/open3dbench:eval
```

如果镜像已经存在，只需执行 `inspect` 和 `save`。离线包必须是 `linux/amd64`。

### 1.2 制备 eval-only 包

推荐命令：

```bash
bash deploy/offline/prepare_release.sh \
  --mode eval \
  --output offline-dist/Open3DBench-eval-only \
  --docker /path/to/docker-26.1.4.tgz \
  --eval-image /path/to/open3dbench-eval.docker.tar \
  --split-size 3800M
```

输出目录必须尚不存在，避免旧 release 文件混入新的 `SHA256SUMS`。

`3800M` 分卷可兼容 FAT32 U 盘的 4 GiB 单文件限制。若介质支持大文件并希望保留完整文件，可省略 `--split-size`。

输出示意：

```text
Open3DBench-eval-only/
├── RELEASE_MANIFEST.txt
├── SHA256SUMS
├── docker/
│   └── docker-26.1.4.tgz[.part-000...]
├── images/
│   └── open3dbench-eval.docker.tar[.part-000...]
└── source/
    ├── Open3DBench-backend-<commit>.tar.gz[.part-000...]
    ├── BACKEND_SOURCE_MANIFEST.txt
    └── BACKEND_SOURCE_SHA256SUMS
```

backend source tar 只含 `OpenROAD-3D`、离线部署脚本和文档，不含 `Place-LoL`/`Place-MoL`。

### 1.3 制备 placer-complete 包

先准备完整源码所需的 LoL 数据和 place 镜像 archive，然后执行：

```bash
docker pull shiyunqi/open3dbench:place
docker save -o /path/to/open3dbench-place.docker.tar \
  shiyunqi/open3dbench:place

bash deploy/offline/prepare_release.sh \
  --mode placer \
  --output offline-dist/Open3DBench-placer-complete \
  --docker /path/to/docker-26.1.4.tgz \
  --eval-image /path/to/open3dbench-eval.docker.tar \
  --place-image /path/to/open3dbench-place.docker.tar \
  --benchmarks /path/to/benchmarks_lol.tar.gz \
  --binaries /path/to/binaries.tar.gz \
  --split-size 3800M
```

该包的 `source/` 同时包含完整源码 tar 和 Git bundle；`data/` 包含 LoL benchmark/binary archive；`images/` 包含 eval/place 两个镜像。

### 1.4 在制备机验证并转移

```bash
bash deploy/offline/verify_bundle.sh \
  offline-dist/Open3DBench-eval-only
```

检查 manifest：

```bash
cat offline-dist/Open3DBench-eval-only/RELEASE_MANIFEST.txt
```

整个 release 目录原样复制到 Mac/U 盘/公司 Win11。不要单独重命名分卷；`.part-000`、`.part-001` 必须放在同一目录。

## 第二部分：在公司 CentOS WSL 部署并评估

以下以 release 位于 `/mnt/c/Open3DBench-offline/Open3DBench-eval-only` 为例。最终源码和运行目录应位于 WSL ext4，例如 `/root/work`，不要直接在 `/mnt/c` 上运行 OpenROAD。

### 2.1 验证 release

```bash
RELEASE=/mnt/c/Open3DBench-offline/Open3DBench-eval-only
cd "$RELEASE"
sha256sum --check --strict SHA256SUMS
cat RELEASE_MANIFEST.txt
```

SHA256 必须先验证，验证失败时不要安装或加载任何内容。

### 2.2 解压源码

如果源码没有分卷：

```bash
mkdir -p /root/work/Open3DBench
tar -xzf "$RELEASE"/source/Open3DBench-backend-*.tar.gz \
  -C /root/work/Open3DBench
```

如果源码有分卷，先重组：

```bash
mkdir -p /root/work/staging /root/work/Open3DBench
cat "$RELEASE"/source/Open3DBench-backend-*.tar.gz.part-* \
  > /root/work/staging/Open3DBench-backend.tar.gz
tar -xzf /root/work/staging/Open3DBench-backend.tar.gz \
  -C /root/work/Open3DBench
```

确认：

```bash
test -f /root/work/Open3DBench/OpenROAD-3D/flow/Makefile
test -f /root/work/Open3DBench/deploy/offline/verify_host.sh
```

placer-complete 包中的完整源码 tar 自带顶层目录，可这样解压：

```bash
mkdir -p /root/work
tar -xzf "$RELEASE"/source/Open3DBench-<commit>.tar.gz \
  -C /root/work
mv /root/work/Open3DBench-<commit> /root/work/Open3DBench
```

如果希望在公司 WSL 保留完整 Git 历史，可以改用 bundle：

```bash
git clone "$RELEASE"/source/Open3DBench-<commit>.bundle \
  /root/work/Open3DBench
cd /root/work/Open3DBench
git switch huawei-partition
```

若 tar 或 bundle 被分卷，先用对应的 `.part-*` 重组成原文件，再执行上述命令。

### 2.3 检查公司 WSL

```bash
cd /root/work/Open3DBench
bash deploy/offline/verify_host.sh
```

预期为 CentOS 7.9、WSL2、`x86_64`、cgroup v2，且 rootfs 至少有 100 GiB 可用空间。

### 2.4 安装 Docker 26 静态包

若 Docker 包被分卷，先重组：

```bash
cat "$RELEASE"/docker/docker-26.1.4.tgz.part-* \
  > /root/work/staging/docker-26.1.4.tgz
```

未分卷时直接使用 release 内文件。以分卷情形为例：

```bash
bash deploy/offline/install_docker_static.sh \
  /root/work/staging/docker-26.1.4.tgz
bash deploy/offline/start_docker_wsl.sh
docker version
docker info
```

WSL 完全退出后 dockerd 会停止。以后每次重新进入公司 WSL，执行：

```bash
cd /root/work/Open3DBench
bash deploy/offline/start_docker_wsl.sh
```

若 overlay2 启动失败，先查看：

```bash
tail -100 /var/log/docker/dockerd-open3dbench.log
```

仅为定位问题时可测试 `vfs`：

```bash
DOCKERD_EXTRA_ARGS='--storage-driver=vfs' \
  bash deploy/offline/start_docker_wsl.sh
```

### 2.5 加载 eval 镜像

未分卷：

```bash
bash deploy/offline/load_images.sh \
  "$RELEASE"/images/open3dbench-eval.docker.tar
```

已分卷时把 `.part-000` 作为参数；脚本会流式读取后续分卷，无需先生成大 tar：

```bash
bash deploy/offline/load_images.sh \
  "$RELEASE"/images/open3dbench-eval.docker.tar.part-000
```

验证无网络容器：

```bash
docker run --rm --network none \
  shiyunqi/open3dbench:eval \
  bash -lc 'uname -m; python3 --version; openroad -version'
```

placer-complete 包如需同时导入 place 镜像，可将 place archive 或其 `.part-000` 作为 `load_images.sh` 的第二个参数。本文件暂不展开 Place-LoL 的运行方法。

### 2.6 准备公司 placer 输出

公司 DEF 放在源码仓库外，例如：

```text
/root/open3dbench-inputs/
├── ariane/top.def
├── ariane/bottom.def
├── bp/top.def
├── bp/bottom.def
├── swerv_wrapper/top.def
├── swerv_wrapper/bottom.def
├── tinyRocket/top.def
└── tinyRocket/bottom.def
```

转换契约：

- top/bottom instance 分别加 `_top`、`_bot`，确保合并后唯一；
- cell/fakeram master 分别加 `_upper`、`_bottom`，匹配 `nangate45_3D` LEF/Lib；
- 每对 `HBT[n]` DEF PIN 变成一个 `HBT_n` pseudo-cell；
- top/bottom local net 分别加 `_TOP`、`_BOT`，连接 HBT 的 `TOP`/`BOT` pin；
- HBT 必须成对、坐标一致、方向互补并指向存在的 net；
- 普通外部 PIN 默认不得在两侧重名。

### 2.7 先转换并检查一对 DEF

启动 eval 容器，并将输入只读挂载：

```bash
cd /root/work/Open3DBench/OpenROAD-3D
COMPANY_PLACER_OUTPUTS=/root/open3dbench-inputs \
  ./start_docker_eval.sh
```

容器中执行：

```bash
cd /workspace/OpenROAD-3D/flow
python3 util/convert_company_3d_def.py \
  --top /workspace/company-input/ariane/top.def \
  --bottom /workspace/company-input/ariane/bottom.def \
  --output /tmp/ariane.merged.def
```

检查 `COMPONENTS`、`PINS`、`NETS` 数量和若干 HBT 连接。若公司 DEF 与上述契约不一致，不要通过关闭校验绕过，应先更新转换规则和测试 fixture。

### 2.8 运行 backend evaluation

仍在 eval 容器中：

```bash
./run_company_3d.sh ariane \
  /workspace/company-input/ariane/top.def \
  /workspace/company-input/ariane/bottom.def
```

支持：

```text
ariane  bp  swerv_wrapper  tinyRocket
```

当前 `ariane` 映射到仓库的 `ariane133` backend config，`bp` 映射到 `black_parrot`。公司综合网表版本、top module、SDC 或 fakeram 类型不同，必须相应调整 `config_company.mk`。

添加 HotSpot：

```bash
./run_company_3d.sh ariane top.def bottom.def --hotspot
```

主要结果位于：

```text
OpenROAD-3D/flow/results/nangate45_3D/<design>/company/
OpenROAD-3D/flow/logs/nangate45_3D/<design>/company/
OpenROAD-3D/flow/reports/nangate45_3D/<design>/company/
```

后端复用现有 `do-lolflow` 的读 DEF、ODB、CTS、上下 die legalization、route 和 finish 阶段，但不运行 Place-LoL placer。

## 第三部分：在公司 Win11 同步到 CodeHub

### 3.1 推荐仓库划分

推荐建立两个 CodeHub repo：

- `Open3DBench-company`：源码和文档，普通 Git；
- `Open3DBench-offline-artifacts`：Docker 静态包、镜像和可再分发的离线制品，Git LFS。

这样修改脚本或文档时无需下载数 GB 镜像。公司 placer 输出和运行结果不应上传到这两个 repo；如确需团队共享，应使用单独受控仓库并确认数据分级和权限。

以下命令在 Windows PowerShell 中运行，要求公司已安装 Git for Windows 和 Git LFS。

### 3.2 上传源码 repo

如果 Win11 收到的是完整 Git bundle：

```powershell
git clone .\Open3DBench-<commit>.bundle Open3DBench-company
Set-Location .\Open3DBench-company
git remote remove origin
git remote add origin <CODEHUB_SOURCE_REPO_URL>
git push -u origin huawei-partition
```

如果使用 backend-only tar，希望建立精简源码 repo：

```powershell
New-Item -ItemType Directory Open3DBench-company
tar -xzf .\Open3DBench-backend-<commit>.tar.gz -C .\Open3DBench-company
Set-Location .\Open3DBench-company
git init -b huawei-partition
git add .
git commit -m "Adapt Open3DBench backend for company offline deployment"
git remote add origin <CODEHUB_SOURCE_REPO_URL>
git push -u origin huawei-partition
```

若公司 Git 版本不支持 `git init -b`，使用：

```powershell
git init
git switch -c huawei-partition
```

### 3.3 上传离线制品 repo（Git LFS）

复制整个 release 目录到 Win11 工作目录，然后执行：

```powershell
git lfs install
git clone <CODEHUB_ARTIFACT_REPO_URL> Open3DBench-offline-artifacts
Set-Location .\Open3DBench-offline-artifacts

Copy-Item -Recurse C:\Transfer\Open3DBench-eval-only .\releases\

git lfs track "*.tgz"
git lfs track "*.tar"
git lfs track "*.tar.gz"
git lfs track "*.bundle"
git lfs track "*.part-*"
git add .gitattributes releases
git commit -m "Add Open3DBench offline release <commit>"
git push origin main
```

在 `git add` 前执行 `git lfs track`，否则大文件可能进入普通 Git object。提交后确认：

```powershell
git lfs ls-files
git status
```

CodeHub 可能对单文件大小、LFS 总量、push 超时和代理有额外限制；以公司 CodeHub 管理策略为准。若 LFS 支持大文件，可省略制备阶段的 `--split-size`；已分卷文件也可直接由 LFS 管理。

### 3.4 同事同步和校验

源码：

```powershell
git clone <CODEHUB_SOURCE_REPO_URL>
git switch huawei-partition
```

离线制品：

```powershell
git lfs install
git clone <CODEHUB_ARTIFACT_REPO_URL>
git lfs pull
```

拉取后必须在公司 WSL 中重新执行：

```bash
sha256sum --check --strict SHA256SUMS
```

发布和协作时固定记录：源码 commit ID、release mode、Docker 静态包版本、eval/place image ID、`SHA256SUMS`，以及公司输入数据版本。适配代码的逐次变更记录见仓库根目录 `COMPANY_DEPLOY_CHANGELOG.md`。
