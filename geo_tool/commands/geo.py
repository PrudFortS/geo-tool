#!/usr/bin/env python3
"""GEO 命令实现（SRA 下载 + fastq-dump 转换）"""
import asyncio
import os
from geo_tool.commands.utils.time_control import TimeController
from geo_tool.commands.utils.status_manager import StatusManager
from geo_tool.commands.utils.downloader import SRADownloader
from geo_tool.commands.utils.converter import FastqConverter
from geo_tool.commands.utils.data_info import get_info, load_srr_gsm_from_local
# from .util.data_info import get_info

def geo_command(args):
    """GEO 命令入口（自动判断模式）"""
    if args.download:
        _download_only(args)
    elif args.fastq:
        _convert_only(args)
    else:
        raise ValueError("必须指定 -d（下载）或 -f（转换）模式")

def _download_only(args):
    """仅下载模式"""
    all_sra_ids = []
    """for gse_id in args.gse_ids:"""
    sra_gsm = get_info(args.gse_ids,
                    os.path.join(args.output_dir,args.gse_ids),database_name='geo')
    all_sra_ids.extend(sra_gsm.keys())
    
    if not all_sra_ids:
        raise ValueError("未找到任何 SRA ID")
    
    print(f"从 GSE ID 解析出 {len(all_sra_ids)} 个 SRA ID")
    
    time_controller = TimeController(
        run_time_start=args.run_time_start,
        run_time_end=args.run_time_end
    )
    status_manager = StatusManager(args.status_file, base_dir=os.path.join(args.output_dir,args.gse_ids))
    
    downloader = SRADownloader(
        sra_ids=all_sra_ids,
        output_dir=os.path.join(args.output_dir,args.gse_ids),
        concurrency=args.prefetch_concurrency,
        time_controller=time_controller,
        status_manager=status_manager
    )
    
    asyncio.run(downloader.download_all())

def _convert_only(args):
    """仅转换模式"""
    import glob
    
    time_controller = TimeController(
        run_time_start=args.run_time_start,
        run_time_end=args.run_time_end
    )
    status_manager = StatusManager(args.status_file, base_dir=args.output_dir)
    
    srr_gsm_dict = load_srr_gsm_from_local(
                            os.path.join(args.output_dir,args.gse_ids),
                            args.gse_ids
                        )
    if not srr_gsm_dict:
        raise ValueError(f"在 {os.path.join(args.output_dir,args.gse_ids)} 中未找到有效的 SRR-GSM 映射")
    
    sra_dir = args.sra_dir if args.sra_dir else os.path.join(args.output_dir, args.gse_ids, 'rawdata')
    sra_files = glob.glob(os.path.join(sra_dir, '*', '*.sra'))
    
    if not sra_files:
        raise FileNotFoundError(f"在 {sra_dir} 中未找到 .sra 文件")
    
    sra_ids = [os.path.basename(f).replace(".sra", "") for f in sra_files]
    sra_path_dict = {os.path.basename(f).replace(".sra", ""): f for f in sra_files}
    print(f"找到 {len(sra_ids)} 个 SRA 文件待转换")
    
    converter = FastqConverter(
        output_dir=os.path.join(args.output_dir,args.gse_ids),
        concurrency=args.fastq_concurrency,
        time_controller=time_controller,
        status_manager=status_manager,
        srr_gsm_dict=srr_gsm_dict,
        sra_path_dict=sra_path_dict
    )
    
    converter.convert_all(sra_ids)
