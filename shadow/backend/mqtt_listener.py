import paho.mqtt.client as mqtt
import json

# MQTT配置
BROKER = "localhost"
PORT = 1883

# 设备状态缓存
device_status = {}

def on_connect(client, userdata, flags, rc):
    print(f"✅ MQTT连接成功，结果码: {rc}")
    client.subscribe("device/+/state")
    client.subscribe("device/+/online")
    client.subscribe("device/+/offline")

def on_message(client, userdata, msg):
    print(f"📩 收到消息 - 主题: {msg.topic}")
    try:
        payload = json.loads(msg.payload.decode())
        print(f"   内容: {json.dumps(payload, indent=2, ensure_ascii=False)}")
        
        # 提取设备ID
        topic_parts = msg.topic.split("/")
        if len(topic_parts) >= 3:
            device_id = topic_parts[1]
            event_type = topic_parts[2]
            
            if event_type == "online":
                device_status[device_id] = "online"
                print(f"🟢 设备 {device_id} 上线")
            elif event_type == "offline":
                device_status[device_id] = "offline"
                print(f"🔴 设备 {device_id} 离线")
            elif event_type == "state":
                device_status[device_id] = "online"
                print(f"📊 设备 {device_id} 状态更新: {payload}")
    except Exception as e:
        print(f"⚠️ 解析消息出错: {e}")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER, PORT, 60)

print("🚀 MQTT监听器启动，等待消息...")
client.loop_forever()
