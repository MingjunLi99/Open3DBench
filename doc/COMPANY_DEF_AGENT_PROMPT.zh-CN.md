# 公司 DEF 转换器适配 Agent Prompt

将下面整段提示词复制给公司电脑上的代码 agent，并把实际报错和命令输出一并提供给它。请先让 agent 阅读仓库和 DEF，再允许它修改代码。

```text
你正在公司 Windows 11 上运行本地代码 agent，适配 Open3DBench 的公司 DEF 转换流程。请直接操作位于公司 CentOS 7.9 WSL2 ext4 中的唯一源码工作树 `/root/Workspace/Open3DBench`（Windows 可通过 `\\wsl$\<CentOS发行版>\root\Workspace\Open3DBench` 访问）。该工作树是从 Ubuntu tar 包解压得到的，可能尚未初始化 Git。真实公司 placer 输出位于：

/root/Workspace/freePartitioner/output_openroad/
  <case>_top.def
  <case>_bot.def

支持 case：ariane、bp、swerv_wrapper、tinyRocket。当前失败命令、完整 stderr/stdout 和失败 case 是：
（在这里粘贴实际命令和完整报错，不要只粘贴最后一行。）

目标：修改 OpenROAD-3D/flow/util/convert_company_3d_def.py，使公司的 top/bottom DEF 能转换为 Open3DBench/OpenROAD-3D 后端需要的单个双 die DEF；不得重新实现 Place-LoL，也不得修改公司 placer。

必须先完成以下只读调查，并把关键事实写出来：
1. 阅读 convert_company_3d_def.py 全文及其 argparse、输入约束、输出规则。
2. 阅读 OpenROAD-3D/flow/test/test_convert_company_3d_def.py 全部测试。
3. 阅读 doc/README.zh-CN.md 第 2.4–2.5 节、OpenROAD-3D/flow/run_company_3d.sh 和相关 nangate45_3D/config_company.mk。
4. 检查 nangate45_3D LEF/Lib 中实际存在的 master、site、layer、HBT/伪 cell 命名；不要凭经验假设 Nangate45 语法。
5. 对每个实际 DEF 只读提取并报告：DESIGN、UNITS DISTANCE MICRONS、DIEAREA、COMPONENTS、PINS、NETS、SPECIALNETS（如有）、ROWS（如有）；统计 section 声明数量与实际 entry 数量。
6. 检查 top/bottom 的实例名、master 名、PIN 名、坐标、方向、net 名是否符合当前脚本契约，并指出第一个不一致的位置。

当前设计契约（除非实际 DEF 和 OpenROAD-3D 代码证明需要调整，否则保持不变）：
- top/bottom instance 合并后分别使用 _top、_bot 后缀；
- cell/fakeram master 分别使用 _upper、_bottom 后缀，以匹配 nangate45_3D LEF/Lib；
- 成对的 HBT[n] DEF PIN 转换为一个 HBT_n pseudo-cell；HBT 两侧坐标应一致，方向应互补，并连接存在的 top/bottom local net；
- top/bottom local net 分别使用 _TOP、_BOT，连接 HBT 的 TOP/BOT pin；
- 普通外部 IO PIN 不得在合并后重名；
- 输出 DEF 必须满足 OpenROAD 3D 读取器的 COMPONENTS/PINS/NETS 数量、语法、DIEAREA 和 master 引用要求。

修改原则：
- 先建立最小可复现 fixture 或新增回归测试，再修改解析/转换逻辑；
- 优先修复真实格式差异，不要通过删除校验、静默跳过 entry、关闭错误检查或硬编码单个 case 来绕过问题；
- 保持现有正常输入、HBT 配对、重复 IO、坐标不一致等测试行为；
- 只修改必要源码、测试和文档；不要把公司 DEF、ODB、日志、Docker 数据、license、内部路径或运行结果复制进 Git；
- 修改前备份原脚本，完成后展示修改前后差异，并解释每个规则变化及其对 OpenROAD-3D 的影响。

验证要求：
1. python3 -m py_compile OpenROAD-3D/flow/util/convert_company_3d_def.py
2. python3 -m unittest discover -s OpenROAD-3D/flow/test -p 'test_*.py'
3. 对失败 case 重新运行 convert_company_3d_def.py，检查输出 DEF 可被 OpenROAD 读取；报告 COMPONENTS/PINS/NETS 数量和 HBT 连接抽查结果。
4. 运行对应 run_company_3d.sh 的最小 backend smoke test（若资源允许）；报告实际命令、退出码和结果文件位置。
5. 检查修改文件没有语法错误、临时调试内容或公司 DEF 数据。

除非我明确要求，不要删除原始 DEF、修改 Docker/placer 配置、初始化 Git、commit 或 push。CodeHub repo 将在全部测试通过后由我从 Win11 手动创建。最后输出：根因、修改文件、关键差异、所有验证命令及结果、仍需我确认的 DEF/网表约定。
```
