# Open3DBench Company Backend

This branch contains the OpenROAD-3D backend flow used to evaluate placement results from the company 3D placer. Public Place-LoL and Place-MoL flows are not included.

```text
Open3DBench/
├── OpenROAD-3D/       # DEF conversion and OpenROAD backend evaluation
├── script/            # CentOS WSL Docker deployment scripts
├── doc/               # Chinese deployment guide and changelog
└── docker/            # Local Docker 26 archive and eval image
```

Supported company cases:

```text
ariane  bp  swerv_wrapper  tinyRocket
```

The company placer supplies separate `<design>_top.def` and `<design>_bot.def` files. `OpenROAD-3D/flow/util/convert_company_3d_def.py` merges them and converts `HBT[n]` DEF pins to Open3DBench HBT pseudo-cells before backend evaluation.

The two large files under `docker/` are kept out of the public GitHub fork. They are included in the offline transfer archive and added through Git LFS only when the company CodeHub repository is initialized.

For the complete offline deployment, evaluation and CodeHub workflow, see [doc/DEPLOY_README.zh-CN.md](doc/DEPLOY_README.zh-CN.md).
