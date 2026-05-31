#!/usr/bin/env python3
"""ENA 命令实现（ascp 直接下载 fastq）"""
import asyncio
import os
import json
from geo_tool.commands.utils.time_control import TimeController
from geo_tool.commands.utils.status_manager import StatusManager
from geo_tool.commands.utils.downloader import FastqDownloader
from geo_tool.commands.utils.data_info import get_info

def ena_command(args):
    """执行 ENA 命令"""
    # 读取元数据
    metadata_dict = get_info(args.prjna_ids,os.path.join(args.output_dir,args.prjna_ids),database_name='ena')
    
    # 初始化组件
    time_controller = TimeController(
        run_time_start=args.run_time_start,
        run_time_end=args.run_time_end
    )
    status_manager = StatusManager(args.status_file, base_dir=os.path.join(args.output_dir,args.prjna_ids))
    downloader = FastqDownloader(
        metadata_dict=metadata_dict,
        output_dir=os.path.join(args.output_dir,args.prjna_ids),
        concurrency=args.ascp_concurrency,
        time_controller=time_controller,
        status_manager=status_manager,
        key_file=args.key_file
    )
    
    # 运行流程
    asyncio.run(downloader.download_all())
