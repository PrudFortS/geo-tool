#!/usr/bin/env python3
"""状态管理模块 先初始化所有sra status,不然当sra很多时，有的下载转换失败了，很难排查；不过也有一个问题，如果又重新运行，这里需要重新初始化所有sra status，否则会报错"""
import json
import os
import threading

class StatusManager:
    """状态管理器（安全写入JSON文件）"""
    def __init__(self, status_file, base_dir=None):
        if base_dir and not os.path.isabs(status_file):
            # 相对路径 → 拼接到 base_dir 下面
            self.status_file = os.path.join(base_dir, status_file)
        else:
            # 绝对路径 → 直接使用
            self.status_file = status_file
        self._lock = threading.Lock()
        self._init_status()
    
    def _init_status(self):
        """初始化状态文件（如果不存在）"""
        if not os.path.exists(self.status_file):
            with open(self.status_file, 'w') as f:
                json.dump({}, f)
    
    def update(self, sra_id, task_type, status):
        """更新任务状态（线程安全）"""
        with self._lock:
            # 读取当前状态
            with open(self.status_file, 'r') as f:
                data = json.load(f)
            
            # 更新状态
            if sra_id not in data:
                data[sra_id] = {}
            data[sra_id][task_type] = status
            
            # 安全写入（先写临时文件，再重命名）
            temp_file = self.status_file + ".tmp"
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2)
            os.replace(temp_file, self.status_file)
    
    def get_status(self, sra_id):
        """获取任务状态"""
        with self._lock:
            if os.path.exists(self.status_file):
                with open(self.status_file, 'r') as f:
                    data = json.load(f)
                return data.get(sra_id, {})
            return {}
    
    def get_all_status(self):
        """获取所有任务状态"""
        with self._lock:
            if os.path.exists(self.status_file):
                with open(self.status_file, 'r') as f:
                    return json.load(f)
            return {}
