#!/usr/bin/env python3
"""下载器模块"""
import asyncio
import os
import signal
import hashlib

from concurrent.futures import ThreadPoolExecutor

class SRADownloader:
    """SRA 下载器"""
    def __init__(self, sra_ids, output_dir, concurrency=3, time_controller=None, status_manager=None):
        self.sra_ids = sra_ids
        self.output_dir = os.path.join(output_dir, 'rawdata')
        os.makedirs(self.output_dir, exist_ok=True) 
        self.concurrency = concurrency
        self.time_controller = time_controller
        self.status_manager = status_manager
        self._running_processes = {}

    async def download_all(self):
        """下载所有 SRA 文件（保持并发数）"""
        semaphore = asyncio.Semaphore(self.concurrency)
        tasks = []
        # 等待运行时段
        await self.time_controller.wait_for_running_period()
        for sra_id in self.sra_ids:
            # 只下载成功下载的文件
            status = self.status_manager.get_status(sra_id)
            if status.get("prefetch") == "success":
                print(f"跳过已下载：{sra_id}")
                continue
            # 创建下载任务
            task = asyncio.create_task(self._download_one(sra_id, semaphore))
            tasks.append(task)
        if not tasks:
            print("所有文件已下载完成，无需重复下载")
            return
        await asyncio.gather(*tasks)

    async def _download_one(self, sra_id, semaphore):
        """下载单个 SRA 文件"""
        async with semaphore:
            # 更新状态为运行中
            self.status_manager.update(sra_id, "prefetch", "running")

            # 执行 prefetch
            cmd = ["prefetch", "-O", self.output_dir, sra_id,"--max-size", "999999999"]
            process = await asyncio.create_subprocess_exec(*cmd)

            # 记录进程（用于暂停/恢复）
            self._running_processes[process.pid] = sra_id

            # 等待完成（支持暂停）
            await self._wait_with_pause(process, sra_id)

            # vdb-validate 校验
            success = False
            if process.returncode == 0:
                success = await self._validate_sra(sra_id)
            # 更新状态
            if success:
                self.status_manager.update(sra_id, "prefetch", "success")
            else:
                self.status_manager.update(sra_id, "prefetch", "failed")

            # 清理进程记录
            if process.pid in self._running_processes:
                del self._running_processes[process.pid]
    async def _validate_sra(self, sra_id):
        """使用 vdb-validate 校验 SRA 文件"""
        sra_path = os.path.join(self.output_dir, sra_id, f"{sra_id}.sra")
        
        if not os.path.exists(sra_path):
            print(f"SRA 文件不存在：{sra_path}")
            return False

        cmd = ["vdb-validate", sra_path]
        process = await asyncio.create_subprocess_exec(*cmd)
        await process.communicate()

        if process.returncode == 0:
            print(f"vdb-validate 通过：{sra_id}")
            return True
        else:
            print(f"vdb-validate 失败：{sra_id}")
            # 删除损坏的文件
            import shutil
            shutil.rmtree(os.path.join(self.output_dir, sra_id), ignore_errors=True)
            return False
    async def _wait_with_pause(self, process, sra_id):
        """等待进程完成，支持暂停/恢复"""
        was_paused = False  # 跟踪上一个状态是否暂停

        while True:
            # 检查是否需要暂停
            if self.time_controller.is_paused():
                if not was_paused:
                    # 状态从 running → paused
                    try:
                        os.kill(process.pid, signal.SIGSTOP)
                        self.status_manager.update(sra_id, "prefetch", "paused")
                    except:
                        pass
                    was_paused = True
            else:
                if was_paused:
                    # 状态从 paused → running
                    try:
                        os.kill(process.pid, signal.SIGCONT)
                        self.status_manager.update(sra_id, "prefetch", "running")
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
            await asyncio.sleep(1)

class FastqDownloader:
    """Fastq 下载器（ascp）"""
    def __init__(self, metadata_dict, output_dir, concurrency=3, time_controller=None, status_manager=None, key_file=None):
        self.metadata = metadata_dict
        self.output_dir = os.path.join(output_dir, 'rawdata')
        os.makedirs(self.output_dir, exist_ok=True) 
        self.concurrency = concurrency
        self.time_controller = time_controller
        self.status_manager = status_manager
        self._running_processes = {}
        self.key_file = key_file
        self.executor = ThreadPoolExecutor(max_workers=concurrency)

    async def download_all(self):
        """下载所有 fastq 文件（保持并发数）"""
        semaphore = asyncio.Semaphore(self.concurrency)
        tasks = []

        # 等待运行时段（只检查一次）
        await self.time_controller.wait_for_running_period()

        for sra_id, info in self.metadata.items():
            # 只下载成功下载的文件
            status = self.status_manager.get_status(sra_id)
            # 获取样本别名
            sample_alias = info.get('sample_alias')
            two_files_downloaded = True
            for i in range(len(info['fastq_aspera'])):
                if status.get(f"ascp_{i}") != "success":
                    two_files_downloaded = False
                    break
            if two_files_downloaded:
                print(f"跳过已下载：{sra_id}")
                continue
            # 创建下载任务
            # 创建下载任务
            for i, fastq_url in enumerate(info['fastq_aspera']):
                # 检查单个文件是否已下载
                if status.get(f"ascp_{i}") == "success":
                    print(f"跳过已下载：{sra_id}_{i}")
                    continue
                
                task = asyncio.create_task(self._download_one(sra_id, fastq_url, i, semaphore,sample_alias))
                tasks.append(task)
        if not tasks:
            print("所有文件已下载完成，无需重复下载")
            return
        await asyncio.gather(*tasks)

    async def _download_one(self, sra_id, fastq_url, file_index, semaphore,sample_alias):
        """下载单个 fastq 文件"""
        async with semaphore:
            # 更新状态为运行中
            self.status_manager.update(sra_id, f"ascp_{file_index}", "running")
            # 创建输出目录
            sample_dir = os.path.join(self.output_dir, sample_alias)
            os.makedirs(sample_dir, exist_ok=True)
            
            expected_md5 = None
            md5_list = self.metadata[sra_id].get('fastq_md5', [])
            if file_index < len(md5_list):
                expected_md5 = md5_list[file_index]
            # 执行 ascp
            cmd = [
                "ascp", "-QT", "-l", "300m", "-P33001",
                "-i", self.key_file, 'era-fasp@'+fastq_url, sample_dir
            ]
            process = await asyncio.create_subprocess_exec(*cmd)
            # 记录进程
            self._running_processes[process.pid] = sra_id
            # 等待完成（支持暂停）
            await self._wait_with_pause(process, sra_id,file_index)
            # 4. MD5校验（线程池执行，不阻塞事件循环）
            filename = fastq_url.split('/')[-1]
            file_path = os.path.join(sample_dir, filename)
            
            loop = asyncio.get_event_loop()
            actual_md5 = await loop.run_in_executor(
                self.executor,  # 线程池
                self._calculate_md5,
                file_path
            )
            # MD5 校验
            success = False
            if process.returncode == 0:
                filename = fastq_url.split('/')[-1]
                file_path = os.path.join(sample_dir, filename)
                actual_md5 = self._calculate_md5(file_path)
                
                if expected_md5 and actual_md5 == expected_md5:
                    print(f"MD5 校验通过：{sra_id}_{file_index}")
                    success = True
                elif not expected_md5:
                    print(f"无预期 MD5，跳过校验：{sra_id}_{file_index}")
                    success = True
                else:
                    print(f"MD5 校验失败：{sra_id}_{file_index}")
                    print(f"  预期: {expected_md5}")
                    print(f"  实际: {actual_md5}")
                    os.remove(file_path)
            else:
                print(f"下载失败：{sra_id}_{file_index}")
            # 更新状态
            if success:
                # 更新状态为成功
                self.status_manager.update(sra_id, f"ascp_{file_index}", "success")
            else:
                self.status_manager.update(sra_id, f"ascp_{file_index}", "failed")

            # 清理进程记录
            if process.pid in self._running_processes:
                del self._running_processes[process.pid]
    def _calculate_md5(self, file_path):
        """计算文件 MD5（同步函数，在线程池执行）"""
        md5_hash = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()
        
    async def _wait_with_pause(self, process, sra_id,file_index):
        """等待进程完成，支持暂停/恢复"""
        was_paused = False  # 跟踪上一个状态是否暂停

        while True:
            # 检查是否需要暂停
            if self.time_controller.is_paused():
                if not was_paused:
                    # 状态从 running → paused
                    try:
                        os.kill(process.pid, signal.SIGSTOP)
                        self.status_manager.update(sra_id, f"ascp_{file_index}", "paused")
                    except:
                        pass
                    was_paused = True
            else:
                if was_paused:
                    # 状态从 paused → running
                    try:
                        os.kill(process.pid, signal.SIGCONT)
                        self.status_manager.update(sra_id, f"ascp_{file_index}", "running")
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
            await asyncio.sleep(1)
