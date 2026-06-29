import paho.mqtt.client as mqtt
import json
import requests

BROKER = "localhost"
PORT = 1883
FLASK_URL = "http://127.0.0.1:5000"


def on_connect(client, userdata, flags, rc):
    print(f"✅ MQTT连接成功，结果码: {rc}")
    client.subscribe("device/+/online")
    client.subscribe("device/+/offline")
    client.subscribe("device/+/state")
    print("📡 已订阅: device/+/online, device/+/offline, device/+/state")


def on_message(client, userdata, msg):
    print(f"📩 收到消息 - 主题: {msg.topic}")
    
    try:
        payload = msg.payload.decode()
        print(f"   原始内容: {payload}")
        
        # ===== 修复：尝试解析JSON，失败则当作纯文本处理 =====
        try:
            data = json.loads(payload)
            is_json = True
        except:
            data = {"raw": payload}
            is_json = False
        
        topic_parts = msg.topic.split("/")
        if len(topic_parts) < 3:
            print(f"⚠️ 主题格式错误: {msg.topic}")
            return
            
        device_id = topic_parts[1]
        event_type = topic_parts[2]
        
        print(f"   📌 {event_type}: {device_id}")
        
        if event_type == "online":
            # ===== 修复：直接发送deviceId，不需要解析JSON =====
            resp = requests.post(
                f"{FLASK_URL}/api/device/online",
                json={"deviceId": device_id},
                timeout=2
            )
            if resp.status_code == 200:
                result = resp.json()
                if result.get("hasPending"):
                    pending_list = result.get("pendingCommands", [])
                    print(f"   📦 有 {len(pending_list)} 条待补发指令")
                    for cmd in pending_list:
                        client.publish(f"device/{device_id}/command", json.dumps(cmd))
                        print(f"      ✅ 补发: {cmd.get('command')} = {cmd.get('value')}")
                    
                    # ===== 新增：补发完成后，清空Redis队列 =====
                    clear_resp = requests.post(
                        f"{FLASK_URL}/api/device/clear_command",
                        json={"deviceId": device_id},
                        timeout=2
                    )
                    if clear_resp.status_code == 200:
                        print(f"   ✅ Redis队列已清空")
                    else:
                        print(f"   ⚠️ 清空队列失败: {clear_resp.status_code}")
                else:
                    print(f"   ✅ 无待补发指令")
            else:
                print(f"   ⚠️ 通知Flask失败: {resp.status_code}")
        
        elif event_type == "offline":
            print(f"   📤 收到离线消息: {device_id}")
            resp = requests.post(
                f"{FLASK_URL}/api/device/offline",
                json={"deviceId": device_id},
                timeout=2
            )
            if resp.status_code == 200:
                print(f"   ✅ 已通知Flask设备离线")
            else:
                print(f"   ⚠️ 通知Flask离线失败: {resp.status_code}")
        
        elif event_type == "state":
            # state 消息是JSON格式
            if is_json and isinstance(data, dict):
                resp = requests.post(
                    f"{FLASK_URL}/api/device/state",
                    json=data,
                    timeout=2
                )
                if resp.status_code == 200:
                    print(f"   ✅ 状态已上报")
                else:
                    print(f"   ⚠️ 状态上报失败: {resp.status_code}")
            else:
                print(f"   ⚠️ state消息不是JSON: {payload}")
        
        elif event_type == "command":
            print(f"   📝 指令: {data.get('command') if is_json else '非JSON格式'}")
        
        else:
            print(f"   ⚠️ 未知事件类型: {event_type}")
            
    except Exception as e:
        print(f"⚠️ 处理消息出错: {e}")
        import traceback
        traceback.print_exc()


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT, 60)

print("🚀 MQTT监听器启动，等待消息...")
client.loop_forever()