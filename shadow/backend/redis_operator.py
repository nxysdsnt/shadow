
import redis
import json
from datetime import datetime


class RedisOperator:
    """
    Redis操作类 - 专门负责指令的保存、查询、删除
    """

    def __init__(self):
        """
        连接到Redis数据库
        """
        try:
            # 连接到本地的Redis服务
            self.client = redis.Redis(
                host='localhost',  # Redis服务器地址
                port=6379,         # Redis端口号
                db=0,              # 数据库编号
                decode_responses=True  # 自动解码返回的数据
            )
            # 测试连接是否成功
            self.client.ping()
            print("✅ Redis连接成功！")
        except Exception as e:
            print(f"❌ Redis连接失败：{e}")
            print("请确认Redis已经启动（双击redis-server.exe）")
            self.client = None

    def save_command(self, device_id, command_data):
        """
        保存设备指令到Redis
        :param device_id: 设备ID（例如 "room01"）
        :param command_data: 指令数据（字典格式）
        :return: True/False
        """
        if not self.client:
            return False

        try:
            # 将设备ID作为key，指令数据转为JSON字符串作为value
            key = f"cmd:{device_id}"
            command_data['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.client.set(key, json.dumps(command_data))
            print(f"✅ 指令已缓存：{device_id} -> {command_data}")
            return True
        except Exception as e:
            print(f"❌ 保存指令失败：{e}")
            return False

    def get_command(self, device_id):
        """
        获取设备缓存的指令
        :param device_id: 设备ID
        :return: 指令数据（字典）或 None
        """
        if not self.client:
            return None

        try:
            key = f"cmd:{device_id}"
            data = self.client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            print(f"❌ 获取指令失败：{e}")
            return None

    def delete_command(self, device_id):
        """
        删除设备缓存的指令
        :param device_id: 设备ID
        :return: True/False
        """
        if not self.client:
            return False

        try:
            key = f"cmd:{device_id}"
            self.client.delete(key)
            print(f"✅ 指令已删除：{device_id}")
            return True
        except Exception as e:
            print(f"❌ 删除指令失败：{e}")
            return False

    def update_device_status(self, device_id, status_data):
        """
        更新设备在线状态
        :param device_id: 设备ID
        :param status_data: 状态数据（字典）
        :return: True/False
        """
        if not self.client:
            return False

        try:
            key = f"status:{device_id}"
            status_data['last_update'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.client.set(key, json.dumps(status_data))
            print(f"✅ 设备状态更新：{device_id} -> {status_data}")
            return True
        except Exception as e:
            print(f"❌ 更新状态失败：{e}")
            return False

    def get_device_status(self, device_id):
        """
        获取设备状态
        :param device_id: 设备ID
        :return: 状态数据（字典）或 None
        """
        if not self.client:
            return None

        try:
            key = f"status:{device_id}"
            data = self.client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            print(f"❌ 获取状态失败：{e}")
            return None


# 测试代码（单独运行这个文件时执行）
if __name__ == "__main__":
    # 创建Redis操作对象
    redis_ops = RedisOperator()

    # 测试保存指令
    test_command = {"deviceId": "room01", "command": "set_temperature", "value": 26}
    redis_ops.save_command("room01", test_command)

    # 测试获取指令
    saved = redis_ops.get_command("room01")
    print(f"获取到的指令：{saved}")

    # 测试删除指令
    redis_ops.delete_command("room01")

    # 测试更新状态
    test_status = {"temperature": 25, "status": "online"}
    redis_ops.update_device_status("room01", test_status)

    # 测试获取状态
    status = redis_ops.get_device_status("room01")
    print(f"获取到的状态：{status}")