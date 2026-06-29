import redis
import json
from datetime import datetime


class RedisOperator:
    """
    Redis操作类 - 设备指令队列、设备状态、在线标记
    """

    ONLINE_KEY = "online_devices"

    def __init__(self):
        try:
            self.client = redis.Redis(
                host='localhost',
                port=6379,
                db=0,
                decode_responses=True
            )
            self.client.ping()
            print("✅ Redis连接成功！")
        except Exception as e:
            print(f"❌ Redis连接失败：{e}")
            self.client = None

    # ========== 指令队列 ==========
    def push_command(self, device_id, command_data):
        """追加指令到队列尾部"""
        if not self.client:
            return False
        try:
            key = f"cmd_queue:{device_id}"
            command_data = dict(command_data)
            command_data.setdefault('timestamp', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            self.client.rpush(key, json.dumps(command_data))
            print(f"📦 指令已入队：{device_id} -> {command_data}")
            return True
        except Exception as e:
            print(f"❌ 缓存指令失败：{e}")
            return False

    def pop_all_commands(self, device_id):
        """取出并清空全部待发指令（FIFO）"""
        if not self.client:
            return []
        try:
            key = f"cmd_queue:{device_id}"
            items = self.client.lrange(key, 0, -1)
            self.client.delete(key)
            return [json.loads(item) for item in items] if items else []
        except Exception as e:
            print(f"❌ 取出指令失败：{e}")
            return []

    def peek_all_commands(self, device_id):
        """查看队列内容（不清空）"""
        if not self.client:
            return []
        try:
            key = f"cmd_queue:{device_id}"
            items = self.client.lrange(key, 0, -1)
            return [json.loads(item) for item in items] if items else []
        except Exception as e:
            print(f"❌ 读取指令失败：{e}")
            return []

    def has_pending_commands(self, device_id):
        if not self.client:
            return False
        try:
            key = f"cmd_queue:{device_id}"
            return self.client.llen(key) > 0
        except Exception as e:
            return False

    def clear_commands(self, device_id):
        if not self.client:
            return False
        try:
            key = f"cmd_queue:{device_id}"
            self.client.delete(key)
            return True
        except Exception as e:
            return False

    # ========== 设备状态 ==========
    def update_device_status(self, device_id, status_data):
        """更新设备状态（合并现有数据）"""
        if not self.client:
            return False
        try:
            key = f"status:{device_id}"
            existing = self.get_device_status(device_id) or {}
            existing.update(status_data)
            existing['last_update'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.client.set(key, json.dumps(existing))
            return True
        except Exception as e:
            print(f"❌ 更新状态失败：{e}")
            return False

    def get_device_status(self, device_id):
        if not self.client:
            return None
        try:
            key = f"status:{device_id}"
            data = self.client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            print(f"❌ 获取状态失败：{e}")
            return None

    # ========== 在线设备集合 ==========
    def set_online(self, device_id):
        if not self.client:
            return False
        try:
            self.client.sadd(self.ONLINE_KEY, device_id)
            return True
        except Exception as e:
            return False

    def set_offline(self, device_id):
        if not self.client:
            return False
        try:
            self.client.srem(self.ONLINE_KEY, device_id)
            return True
        except Exception as e:
            return False

    def is_online(self, device_id):
        if not self.client:
            return False
        try:
            return self.client.sismember(self.ONLINE_KEY, device_id)
        except Exception as e:
            return False

    def get_online_devices(self):
        if not self.client:
            return set()
        try:
            return self.client.smembers(self.ONLINE_KEY)
        except Exception as e:
            return set()