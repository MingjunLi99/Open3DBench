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

先在 Open3DBench 根目录建立固定的制品目录：

```bash
mkdir -p offline-dist/docker offline-dist/images offline-dist/data offline-dist/releases
```

Docker 静态包固定放在：

```text
offline-dist/docker/docker-26.1.4.tgz
```

当前工程已经准备好 eval image archive：

```bash
test -s offline-dist/images/open3dbench-eval.docker.tar
tar -tf offline-dist/images/open3dbench-eval.docker.tar | head
bash deploy/offline/verify_bundle.sh offline-dist
```

`SHA256SUMS` 中记录的是相对于 `offline-dist/` 的路径；不要在仓库根目录直接执行 `sha256sum --check offline-dist/SHA256SUMS`。`verify_bundle.sh` 会先进入正确目录再检查全部文件。等价的手工命令是：

```bash
(cd offline-dist && sha256sum --check --strict SHA256SUMS)
```

因此，当前 Ubuntu WSL 仅执行 release 打包时不需要安装 Docker；`prepare_release.sh` 只复制、重组和校验 archive，不启动容器。

只有以下情况才需要在制备机安装 Docker 或其他兼容的镜像工具：

- `offline-dist/images/open3dbench-eval.docker.tar` 不存在；
- 需要更新镜像版本；
- 希望在送往公司前在当前 Ubuntu WSL 实际启动容器做 smoke test。

如果以后选择在制备机安装 Docker 并重新生成 archive，再执行：

```bash
docker pull shiyunqi/open3dbench:eval
docker image inspect shiyunqi/open3dbench:eval \
  --format '{{.Id}} {{.Architecture}} {{.Os}}'
docker save -o offline-dist/images/open3dbench-eval.docker.tar \
  shiyunqi/open3dbench:eval
```

重新生成后必须更新 `offline-dist/SHA256SUMS`，并确认镜像为 `linux/amd64`。不要在旧 checksum 下替换 archive。

### 1.2 制备 eval-only 包

在 Open3DBench 根目录执行：

```bash
bash deploy/offline/prepare_release.sh --mode eval
```

该命令负责生成部署文件。默认输出目录是：

```text
Open3DBench/offline-dist/releases/Open3DBench-eval-only/
```

其中 `Open3DBench/` 是当前仓库根目录。命令不会生成一个单独的“总压缩包”，而是生成一个自包含 release 目录。该目录可以原样复制到 ExFAT U 盘；不要只复制其中某个文件。

目录中的文件类型分别是：

- `source/Open3DBench-backend-<commit>.tar.gz`：已压缩的 backend-only 源码包；
- `docker/docker-26.1.4.tgz`：Docker 静态二进制压缩包；
- `images/open3dbench-eval.docker.tar`：未再次压缩的 Docker image archive；
- `RELEASE_MANIFEST.txt`：release 模式、源码 commit 和生成时间；
- `SHA256SUMS`：整个 release 目录内所有文件的校验值。

不建议再把整个 release 目录压缩成一个 `.tar.gz`：Docker image 和 Docker 静态包本身已经是 archive，再次压缩耗时、需要额外磁盘空间，也不利于单独校验和加载。ExFAT 可以直接保存这些大文件。

脚本默认读取：

```text
offline-dist/docker/docker-26.1.4.tgz
offline-dist/images/open3dbench-eval.docker.tar
```

输出目录必须尚不存在，避免旧 release 文件混入新的 `SHA256SUMS`。

输出示意：

```text
Open3DBench-eval-only/
├── RELEASE_MANIFEST.txt
├── SHA256SUMS
├── docker/
│   └── docker-26.1.4.tgz
├── images/
│   └── open3dbench-eval.docker.tar
└── source/
    ├── Open3DBench-backend-<commit>.tar.gz
    ├── BACKEND_SOURCE_MANIFEST.txt
    └── BACKEND_SOURCE_SHA256SUMS
```

backend source tar 只含 `OpenROAD-3D`、离线部署脚本和文档，不含 `Place-LoL`/`Place-MoL`。

### 1.3 制备 placer-complete 包

当前工程已经准备了完整的 place 镜像和 LoL 数据，直接执行：

```bash
bash deploy/offline/prepare_release.sh --mode placer
```

该命令默认生成：

```text
Open3DBench/offline-dist/releases/Open3DBench-placer-complete/
```

它同样是可以整体复制到 ExFAT U 盘的 release 目录，而不是单个压缩包。相比 eval-only，目录中还会包含完整源码/Git bundle、place 镜像和 LoL benchmark/binary archive。

placer 模式默认读取：

```text
offline-dist/docker/docker-26.1.4.tgz
offline-dist/images/open3dbench-eval.docker.tar
offline-dist/images/open3dbench-place.docker.tar
offline-dist/data/benchmarks_lol.tar.gz
offline-dist/data/binaries.tar.gz
```

`prepare_release.sh` 不再执行分卷或压缩；它要求输入 archive 是完整文件，并直接复制到 release。ExFAT U 盘可以直接保存这些大文件。

该包的 `source/` 同时包含完整源码 tar 和 Git bundle；`data/` 包含 LoL benchmark/binary archive；`images/` 包含 eval/place 两个镜像。

### 1.4 在制备机验证并转移

下面的命令只校验已经由 `prepare_release.sh` 生成的目录：

```bash
bash deploy/offline/verify_bundle.sh \
  offline-dist/releases/Open3DBench-eval-only
```

它不会生成压缩包，不会复制文件，也不会修改 release。脚本进入指定目录，读取其中的 `SHA256SUMS`，逐项重新计算 SHA256。成功时每个文件显示 `OK`，最后显示：

```text
Release verification passed. No files were created or modified.
```

placer-complete 对应的校验命令是：

```bash
bash deploy/offline/verify_bundle.sh \
  offline-dist/releases/Open3DBench-placer-complete
```

检查 manifest：

```bash
cat offline-dist/releases/Open3DBench-eval-only/RELEASE_MANIFEST.txt
```

校验成功后，将下面整个目录复制到 U 盘：

```text
offline-dist/releases/Open3DBench-eval-only/
```

如果制备的是完整方案，则复制：

```text
offline-dist/releases/Open3DBench-placer-complete/
```

可使用 Windows 文件管理器直接复制，也可以在 WSL 中复制到实际的 U 盘挂载目录。U 盘盘符和 WSL 挂载点由 Windows 环境决定，因此文档不写死。复制后建议在 U 盘或公司 WSL 中再次运行 `sha256sum --check --strict SHA256SUMS`。

如果需要通过 `scp` 或 U 盘传输单个文件，可以将整个 release 目录打包成 ZIP。以下命令使用 ZIP64，并关闭分卷；CentOS WSL 可用 `unzip` 解压，Windows 11 可用文件管理器或 7-Zip 解压：

```bash
# 如当前 Ubuntu WSL 尚未安装 zip/unzip，可先安装对应工具
command -v zip >/dev/null || echo "请先安装 zip"
command -v unzip >/dev/null || echo "请先安装 unzip"

# 二选一：eval-only 或 placer-complete
RELEASE_NAME=Open3DBench-eval-only
# RELEASE_NAME=Open3DBench-placer-complete

# 生成 offline-dist/releases/${RELEASE_NAME}.zip
(cd offline-dist/releases && \
  zip -r -0 -s 0 "${RELEASE_NAME}.zip" "${RELEASE_NAME}")

# 打包后验证 ZIP 目录结构、CRC 和整个 ZIP 的 SHA256
unzip -t "offline-dist/releases/${RELEASE_NAME}.zip"
sha256sum "offline-dist/releases/${RELEASE_NAME}.zip"
```

其中 `-0` 使用 store 模式，因为 Docker image、`.tgz` 和源码 `.tar.gz` 已经压缩，再次压缩通常只会增加时间；`-s 0` 表示不生成 `.z01`、`.z02` 等分卷，`zip` 会按 ZIP64 格式处理大文件。实际传输时复制对应的 `.zip` 文件即可；不要同时复制旧的 release 目录或重复生成同名 ZIP。公司 CentOS WSL 解压示例：

```bash
unzip Open3DBench-eval-only.zip -d /root/Workspace
```

Windows 11 可右键 ZIP 选择“全部解压”，或在 PowerShell 中执行：

```powershell
Expand-Archive .\Open3DBench-eval-only.zip -DestinationPath .\Open3DBench-eval-only
```

若 Windows 文件管理器或 `Expand-Archive` 对超大 ZIP/ZIP64 文件报错，请使用 7-Zip 解压。解压到公司 WSL 后，进入 release 目录再次执行 `sha256sum --check --strict SHA256SUMS`。

## 第二部分：在公司 CentOS WSL 部署并评估

以下以 release 位于 `/mnt/d/Wrokspace/Open3DBench-eval-only` 为例。最终源码和运行目录应位于 WSL ext4，例如 `/root/Workspace`，不要直接在 `/mnt/d` 上运行 OpenROAD。

### 2.1 验证 release

```bash
RELEASE=/mnt/d/Wrokspace/Open3DBench-eval-only
cd "$RELEASE"
sha256sum --check --strict SHA256SUMS
cat RELEASE_MANIFEST.txt
```

SHA256 必须先验证，验证失败时不要安装或加载任何内容。

### 2.2 解压源码

```bash
mkdir -p /root/Workspace/Open3DBench
tar -xzf "$RELEASE"/source/Open3DBench-backend-*.tar.gz \
  -C /root/Workspace/Open3DBench
```

确认：

```bash
test -f /root/Workspace/Open3DBench/OpenROAD-3D/flow/Makefile
test -f /root/Workspace/Open3DBench/deploy/offline/verify_host.sh
```

placer-complete 包中的完整源码 tar 自带顶层目录，可这样解压：

```bash
mkdir -p /root/Workspace
SOURCE_TAR=$(find "$RELEASE/source" -maxdepth 1 -type f \
  -name 'Open3DBench-*.tar.gz' ! -name '*-backend-*' -print -quit)
tar -xzf "$SOURCE_TAR" -C /root/Workspace
SOURCE_DIR=$(find /root/Workspace -maxdepth 1 -type d \
  -name 'Open3DBench-*' -print -quit)
mv "$SOURCE_DIR" /root/Workspace/Open3DBench
```

如果希望在公司 WSL 保留完整 Git 历史，可以改用 bundle：

```bash
BUNDLE=$(find "$RELEASE/source" -maxdepth 1 -type f \
  -name 'Open3DBench-*.bundle' -print -quit)
git clone "$BUNDLE" /root/Workspace/Open3DBench
cd /root/Workspace/Open3DBench
git switch huawei-partition
```

### 2.3 检查公司 WSL

```bash
cd /root/Workspace/Open3DBench
bash deploy/offline/verify_host.sh
```

预期为 CentOS 7.9、WSL2、`x86_64`、cgroup v2，且 rootfs 至少有 100 GiB 可用空间。

### 2.4 安装 Docker 26 静态包

```bash
bash deploy/offline/install_docker_static.sh \
  "$RELEASE"/docker/docker-26.1.4.tgz
bash deploy/offline/start_docker_wsl.sh
docker version
docker info
```

WSL 完全退出后 dockerd 会停止。以后每次重新进入公司 WSL，执行：

```bash
cd /root/Workspace/Open3DBench
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

```bash
bash deploy/offline/load_images.sh \
  "$RELEASE"/images/open3dbench-eval.docker.tar
```

验证无网络容器：

```bash
docker run --rm --network none \
  shiyunqi/open3dbench:eval \
  bash -lc 'uname -m; python3 --version; openroad -version'
```

placer-complete 包如需同时导入 place 镜像，将完整的 place archive 作为 `load_images.sh` 的第二个参数。本文件暂不展开 Place-LoL 的运行方法。

### 2.6 准备公司 placer 输出

公司 DEF 使用 freePartitioner 的扁平输出目录，放在源码仓库外。例如 `swerv_wrapper`：

```text
/root/Workspace/freePartitioner/output_openroad/
├── swerv_wrapper_top.def
└── swerv_wrapper_bot.def
```

其余 case 使用相同命名约定：`ariane_top.def`/`ariane_bot.def`、`bp_top.def`/`bp_bot.def`、`tinyRocket_top.def`/`tinyRocket_bot.def`。

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
cd /root/Workspace/Open3DBench/OpenROAD-3D
COMPANY_PLACER_OUTPUTS=/root/Workspace/freePartitioner/output_openroad \
  ./start_docker_eval.sh
```

容器中执行：

```bash
cd /workspace/OpenROAD-3D/flow
python3 util/convert_company_3d_def.py \
  --top /workspace/company-input/swerv_wrapper_top.def \
  --bottom /workspace/company-input/swerv_wrapper_bot.def \
  --output /tmp/swerv_wrapper.merged.def
```

检查 `COMPONENTS`、`PINS`、`NETS` 数量和若干 HBT 连接。若公司 DEF 与上述契约不一致，不要通过关闭校验绕过，应先更新转换规则和测试 fixture。

### 2.8 运行 backend evaluation

仍在 eval 容器中：

```bash
./run_company_3d.sh swerv_wrapper \
  /workspace/company-input/swerv_wrapper_top.def \
  /workspace/company-input/swerv_wrapper_bot.def
```

支持：

```text
ariane  bp  swerv_wrapper  tinyRocket
```

当前 `ariane` 映射到仓库的 `ariane133` backend config，`bp` 映射到 `black_parrot`。公司综合网表版本、top module、SDC 或 fakeram 类型不同，必须相应调整 `config_company.mk`。

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
$Bundle = Get-ChildItem .\Open3DBench-*.bundle | Select-Object -First 1
git clone $Bundle.FullName Open3DBench-company
Set-Location .\Open3DBench-company
git remote remove origin
git remote add origin <CODEHUB_SOURCE_REPO_URL>
git push -u origin huawei-partition
```

如果使用 backend-only tar，希望建立精简源码 repo：

```powershell
New-Item -ItemType Directory Open3DBench-company
$SourceTar = Get-ChildItem .\Open3DBench-backend-*.tar.gz | Select-Object -First 1
tar -xzf $SourceTar.FullName -C .\Open3DBench-company
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
git add .gitattributes releases
git commit -m "Add Open3DBench offline release"
git push origin main
```

在 `git add` 前执行 `git lfs track`，否则大文件可能进入普通 Git object。提交后确认：

```powershell
git lfs ls-files
git status
```

CodeHub 可能对单文件大小、LFS 总量、push 超时和代理有额外限制；以公司 CodeHub 管理策略为准。当前 release 不做分卷，直接由 ExFAT 或 Git LFS 管理大文件。

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
