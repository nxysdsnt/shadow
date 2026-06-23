import paho.mqtt.client as mqtt
import json
import time

# 配置
BROKER = "localhost"
PORT = 1883

# 创建客户端
client = mqtt.Client()
client.connect(BROKER, PORT, 60)

def publish_message(topic, data):
    """发送消息"""
    payload = json.dumps(data)
    result = client.publish(topic, payload)
    if result.rc == 0:
        print(f"✅ 消息发送成功 - 主题: {topic}")
        print(f"   内容: {payload}")
    else:
        print(f"❌ 消息发送失败，错误码: {result.rc}")
    time.sleep(0.5)

# ===== 发送测试消息 =====

# 1. 模拟设备上线
print("\n--- 发送上线消息 ---")
publish_message("device/room01/online", {"deviceId": "room01"})

# 2. 模拟设备上报状态
print("\n--- 发送状态消息 ---")
publish_message("device/room01/state", {
    "deviceId": "room01",
    "temperature": 25,
    "status": "online",
    "timestamp": "2026-06-23 10:30:00"
})

# 3. 模拟用户下发指令
print("\n--- 发送指令消息 ---")
publish_message("device/room01/command", {
    "deviceId": "room01",
    "command": "set_temperature",
    "value": 26,
    "timestamp": "2026-06-23 10:30:00"
})

# 4. 模拟设备离线
print("\n--- 发送离线消息 ---")
publish_message("device/room01/offline", {"deviceId": "room01"})

print("\n✅ 所有测试消息发送完成！")
client.disconnect()