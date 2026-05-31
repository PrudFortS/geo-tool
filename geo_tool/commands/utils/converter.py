#!/usr/bin/env python3
"""转换器模块"""
import os
import signal
import time
from threading import Thread
from queue import Queue

class FastqConverter:
    """Fastq 转换器（fastq-dump）"""
    def __init__(self, output, concurrency=3, time_controller=None, status_manager=None,
    srr_gsm_dict=None, sra_path_dict=None):
        self.output_dir = os.path.join(output, 'fastq')
        os.makedirs(self.output_dir, exist_ok=True)
        self.concurrency = concurrency
        self.time_controller = time_controller
        self.status_manager = status_manager
        self._running_processes = {}
        self.srr_gsm_dict = srr_gsm_dict
        self.sra_path_dict = sra_path_dict
    
    def convert_all(self, sra_ids):
        """转换所有 SRA 文件（保持并发数）"""
        # 创建任务队列
        queue = Queue()
        
        # 只添加未成功转换的 SRA
        for sra_id in self.srr_gsm_dict.keys():
            # 只转换成功下载的文件
            status = self.status_manager.get_status(sra_id)
            if status.get("fastq-dump") == "success":
                print(f"跳过已转换：{sra_id}")
                continue
            if status.get("prefetch") == "success":
                queue.put(sra_id)
        if queue.empty():
            print("所有文件已转换完成，无需重复转换")
            return
        # 添加结束标志
        for _ in range(self.concurrency):
            queue.put(None)
        
        # 启动工作线程
        threads = []
        for _ in range(self.concurrency):
            t = Thread(target=self._convert_worker, args=(queue,))
            t.daemon = True
            t.start()
            threads.append(t)
        
        # 等待所有线程完成
        for t in threads:
            t.join()
    
    def _convert_worker(self, queue):
        """转换工作线程"""
        while True:
            sra_id = queue.get()
            if sra_id is None:
                queue.task_done()
                break
            
            # 等待运行时段
            while not self.time_controller.is_running_period():
                time.sleep(300)  # 每5分钟检查一次
            
            # 更新状态
            self.status_manager.update(sra_id, "fastq-dump", "running")
            # 新增：创建 GSM 目录
            gsm_dir = os.path.join(self.output_dir, self.srr_gsm_dict[sra_id])
            os.makedirs(gsm_dir, exist_ok=True)
            # 执行 fastq-dump
            sra_file = self.sra_path_dict.get(sra_id) if self.sra_path_dict else os.path.join(self.output, 'rawdata', sra_id, sra_id + ".sra")
            cmd = ["fastq-dump", "--split-files", sra_file, "--gzip", "-O", gsm_dir]
            
            # 使用 subprocess 执行
            import subprocess
            process = subprocess.Popen(cmd)
            
            # 记录进程
            self._running_processes[process.pid] = sra_id
            
            # 等待完成（支持暂停）
            self._wait_with_pause(process, sra_id)
            
            # 更新状态
            if process.returncode == 0:
                self.status_manager.update(sra_id, "fastq-dump", "success")
            else:
                self.status_manager.update(sra_id, "fastq-dump", "failed")
            
            # 清理进程记录
            if process.pid in self._running_processes:
                del self._running_processes[process.pid]
            
            queue.task_done()
    def _wait_with_pause(self, process, sra_id):
        """等待进程完成，支持暂停/恢复"""
        was_paused = False  # 跟踪上一个状态是否暂停

        while True:
            # 检查是否需要暂停
            if self.time_controller.is_paused():
                if not was_paused:
                    # 状态从 running → paused
                    try:
                        os.kill(process.pid, signal.SIGSTOP)
                        self.status_manager.update(sra_id, "fastq-dump", "paused")
                    except:
                        pass
                    was_paused = True
            else:
                if was_paused:
                    # 状态从 paused → running
                    try:
                        os.kill(process.pid, signal.SIGCONT)
                        self.status_manager.update(sra_id, "fastq-dump", "running")
                    except:
                        pass
                    was_paused = False

            # 非阻塞等待进程状态
            try:
                ret_pid, status = os.waitpid(process.pid, os.WNOHANG)
                if ret_pid != 0:
                    # 进程已结束，直接返回
                    return
            except ChildProcessError:
                return
            # 等待一小段时间
            time.sleep(1)
