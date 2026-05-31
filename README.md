# geo-tool

[![Python](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

GEO/ENA 数据下载与处理工具 - 从 GEO 和 ENA 数据库自动下载、高通量测序数据转换和校验的命令行工具。

## 功能特点

- **双数据源支持**：支持从 GEO (SRA) 和 ENA (ascp) 两个数据库下载数据
- **SRA → FASTQ 转换**：内置 `fastq-dump` 转换功能
- **并发控制**：支持 `prefetch` 和 `fastq-dump` 并发数自定义
- **时间控制**：支持设置运行时段（如夜间），自动暂停/恢复任务
- **断点续传**：自动记录任务状态，中断后可继续执行
- **进度追踪**：实时记录任务状态到 JSON 文件

## 安装

### 从源码安装

```bash
git clone https://github.com/yourusername/geo-tool.git
cd geo-tool
pip install -e .
```

### 使用 pip

```bash
pip install geo-tool
```

## 依赖

- Python >= 3.7
- [SRA Toolkit](https://github.com/ncbi/sra-tools) (需提前安装并配置 `prefetch` 和 `fastq-dump`)
- ascp (ENA 下载模式需要，可选)

## 使用方法

### GEO 下载模式

从 GEO 数据库下载 SRA 文件：

```bash
geo-tool geo -d --gse-ids GSE12345 --output-dir /data/output
```

### SRA 转 FASTQ 模式

将已下载的 SRA 文件转换为 FASTQ：

```bash
geo-tool geo -f --sra-dir /data/rawdata --output-dir /data/output
```

### ENA 下载模式

从 ENA 数据库直接下载 FASTQ 文件：

```bash
geo-tool ena --prjna-ids PRJNA123456 --key-file /path/to/asperaweb_id_dsa.putty --output-dir /data/output
```

### 时间控制

设置运行时段（默认 18:00 - 次日 08:00）：

```bash
geo-tool geo -d --gse-ids GSE12345 \
    --output-dir /data/output \
    --run-time-start 22.0 \
    --run-time-end 6.0
```

## 命令行参数

### geo 命令

```
usage: geo-tool geo [-h] --output-dir OUTPUT_DIR
                    [--run-time-start RUN_TIME_START]
                    [--run-time-end RUN_TIME_END]
                    [--status-file STATUS_FILE]
                    (-d | -f)
                    [--gse-ids GSE_IDS]
                    [--prefetch-concurrency PREFETCH_CONCURRENCY]
                    [--sra-dir SRA_DIR]
                    [--fastq-concurrency FASTQ_CONCURRENCY]

必选参数:
  -d, --download    下载模式：从 GEO/SRA 下载 .sra 文件
  -f, --fastq       转换模式：将已有的 .sra 转为 .fastq 文件

下载模式(-d) 专属参数:
  --gse-ids GSE_IDS               GSE 编号
  --prefetch-concurrency           prefetch 并发数（默认：3）

转换模式(-f) 专属参数:
  --sra-dir SRA_DIR               SRA 文件目录（默认：{output_dir}/{gse-id}/rawdata）
  --fastq-concurrency             fastq-dump 并发数（默认：3）

公共参数:
  --output-dir OUTPUT_DIR         输出目录
  --run-time-start                运行开始时间（默认：18.0）
  --run-time-end                  运行结束时间（默认：08.0）
  --status-file STATUS_FILE       状态文件路径（默认：task_status.json）
```

## 项目结构

```
geo-tool/
├── geo_tool/
│   ├── __main__.py              # 入口文件
│   ├── cli.py                   # 命令行解析
│   ├── commands/
│   │   ├── geo.py               # GEO 下载/转换逻辑
│   │   ├── ena.py               # ENA 下载逻辑
│   │   └── utils/
│   │       ├── converter.py     # SRA → FASTQ 转换器
│   │       ├── data_info.py     # GEO/ENA 数据解析
│   │       ├── downloader.py    # SRA 下载器
│   │       ├── status_manager.py # 任务状态管理
│   │       └── time_control.py   # 时间控制器
│   └── __init__.py
├── setup.py                     # 安装配置
└── README.md                    # 本文档
```

## 工作流程

```
┌─────────────────────────────────────────────────────────────────┐
│                         geo-tool                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐         ┌──────────────┐         ┌───────────┐│
│  │   GEO/SRA    │ ──────► │  下载 .sra   │ ──────► │   rawdata ││
│  │  GSE12345    │         │  (prefetch)  │         │  目录     ││
│  └──────────────┘         └──────────────┘         └─────┬─────┘│
│                                                          │      │
│                                                          ▼      │
│         ┌──────────────┐         ┌──────────────┐         ┌───┐ │
│         │   输出目录   │ ◄────── │ 转换 .fastq  │ ◄────── │   │ │
│         │  (按GSM组织) │         │(fastq-dump) │         │   │ │
│         └──────────────┘         └──────────────┘         │   │ │
│                                                            └───┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
