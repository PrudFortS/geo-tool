#!/usr/bin/env python3
import argparse
from geo_tool.commands.geo import geo_command
from geo_tool.commands.ena import ena_command

def parse_time(time_str):
    """
    解析时间字符串，支持格式：
    - "HH"（如 "18"）
    - "HH:MM"（如 "18:30"）
    返回：小时数（浮点型，包含分钟）
    """
    if ':' in time_str:
        hours, minutes = time_str.split(':')
        return float(hours) + float(minutes) / 60
    else:
        return float(time_str)

def main():
    parser = argparse.ArgumentParser(
        prog="geo-tool",
        description="GEO, ENA 数据下载与处理工具"
    )
    
    # 创建父解析器，定义公共参数
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("--output-dir", required=True, help="输出目录")
    parent_parser.add_argument(
        "--run-time-start", 
        type=str, 
        default="18:00", 
        help="运行开始时间，支持格式：HH 或 HH:MM（如 18 或 18:30）"
    )
    parent_parser.add_argument(
        "--run-time-end", 
        type=str, 
        default="08:00", 
        help="运行结束时间，支持格式：HH 或 HH:MM（如 8 或 08:00）"
    )
    parent_parser.add_argument("--status-file", default="task_status.json", help="状态文件路径")
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # geo 命令（SRA 下载 + 转换）
    geo_parser = subparsers.add_parser(
        "geo", 
        help="使用 GEO 方式下载（SRA）",
        parents=[parent_parser]  # 继承公共参数
    )
    
    # 必选模式组
    mode_group = geo_parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("-d", "--download", action="store_true",
                            help="下载模式：从 GEO/SRA 下载 .sra 文件")
    mode_group.add_argument("-f", "--fastq", action="store_true",
                            help="转换模式：将已有的 .sra 转为 .fastq 文件")
    
    # 下载模式专属参数组
    download_group = geo_parser.add_argument_group('下载模式(-d) 专属参数（必须+可选）')
    download_group.add_argument("--gse-ids", required=True, help="【下载必选】GSE 编号")
    download_group.add_argument("--prefetch-concurrency", type=int, default=3, help="【下载可选】prefetch 并发数")
    
    # 转换模式专属参数组
    fastq_group = geo_parser.add_argument_group('转换模式(-f) 专属参数（必须+可选）')
    fastq_group.add_argument("--sra-dir", type=str, help="【转换可选】SRA 文件目录（默认：{output_dir}/{gse-id}/rawdata）")
    fastq_group.add_argument("--fastq-concurrency", type=int, default=3, help="【转换可选】fastq-dump 并发数")
    
    # ena 命令（ascp 直接下载）
    ena_parser = subparsers.add_parser(
        "ena", 
        help="使用 ENA 方式下载（ascp 直接下载 fastq）",
        parents=[parent_parser]  # 继承公共参数
    )
    # ena_parser.add_argument("--prjna-ids", nargs="+", required=True, help="PRJNA ID") 暂无同时处理多个prjna id的功能
    ena_parser.add_argument("--prjna-ids", required=True, help="PRJNA ID")
    ena_parser.add_argument("--ascp-concurrency", type=int, default=3, help="ascp 并发数")
    ena_parser.add_argument("--key-file", required=True, help="ascp 下载所需 key 文件路径")
    args = parser.parse_args()
    
    # 解析时间参数
    args.run_time_start = parse_time(args.run_time_start)
    args.run_time_end = parse_time(args.run_time_end)
    
    if args.command == "geo":
        if args.download:
            geo_command(args)
        elif args.fastq:
            geo_command(args)
    elif args.command == "ena":
        ena_command(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
