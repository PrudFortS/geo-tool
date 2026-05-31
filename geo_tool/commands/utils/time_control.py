#!/usr/bin/env python3
"""时间控制模块"""
import asyncio
import time
import threading
from datetime import datetime

class TimeController:
    """时间控制器（管理运行时段和暂停/恢复）"""
    def __init__(self, run_time_start=18.0, run_time_end=8.0):
        self.run_time_start = run_time_start  # 运行时段开始时间（浮点型，如 18.5 表示 18:30）
        self.run_time_end = run_time_end      # 运行时段结束时间（浮点型，如 8.0167 表示 8:01）
        self._pause_flag = False              # 暂停标志
        self._running = True                  # 运行标志
        self._monitor_thread = None           # 监控线程
    
    def is_running_period(self):
        """判断是否在运行时段"""
        now = datetime.now()
        # 将当前时间转换为浮点小时数（包含分钟）
        current_time = now.hour + now.minute / 60
        
        # 处理跨午夜的情况（如 18:00 - 08:00）
        if self.run_time_start > self.run_time_end:
            return current_time >= self.run_time_start or current_time < self.run_time_end
        else:
            return self.run_time_start <= current_time < self.run_time_end
    
    async def wait_for_running_period(self):
        """等待进入运行时段"""
        while not self.is_running_period():
            await asyncio.sleep(1800)  # 每30分钟检查一次（更精确）
    
    def _monitor_loop(self):
        """时间监控循环（后台线程）"""
        while self._running:
            # 检查时间
            in_period = self.is_running_period()
            
            # 如果进入非运行时段，设置暂停标志
            if not in_period and not self.is_paused():
                self._pause_flag = True
                print(f"[{datetime.now()}] 进入非运行时段，暂停所有任务")
            
            # 如果进入运行时段，清除暂停标志
            if in_period and self.is_paused():
                self._pause_flag = False
                print(f"[{datetime.now()}] 进入运行时段，恢复所有任务")
            
            # 每分钟检查一次（更精确）
            time.sleep(60)
    
    def start_monitor(self):
        """启动时间监控线程"""
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
    
    def stop_monitor(self):
        """停止时间监控线程"""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)

    def is_paused(self):
        """判断是否处于暂停状态"""
        return self._pause_flag
