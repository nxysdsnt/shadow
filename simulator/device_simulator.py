import paho.mqtt.client as mqtt
import json
import time
import sys
import signal
import requests
import atexit

BROKER = "localhost"
PORT = 1883
FLASK_URL = "http://127.0.0.1:5000"

ALL_DEVICES = [
    "living_light1", "living_light2", "living_tv", "living_ac",
    "living_speaker", "living_vacuum", "living_curtain",
    "kitchen_dishwasher", "kitchen_hood", "kitchen_fridge",
    "kitchen_water", "kitchen_stove",
    "bedroom_ac", "bedroom_light", "bedroom_curtain", "bedroom_humidifier",
    "entrance_lock", "entrance_light", "entrance_alarm",
    "balcony_rack", "balcony_light"
]

DEVICE_NAMES = {
    "living_light1": "客厅灯1", "living_light2": "客厅灯2",
    "living_tv": "电视", "living_ac": "客厅空调",
    "living_speaker": "音箱", "living_vacuum": "扫地机器人",
    "living_curtain": "客厅窗帘",
    "kitchen_dishwasher": "洗碗机", "kitchen_hood": "油烟机",
    "kitchen_fridge": "冰箱", "kitchen_water": "热水器",
    "kitchen_stove": "灶台",
    "bedroom_ac": "卧室空调", "bedroom_light": "吸顶灯",
    "bedroom_curtain": "卧室窗帘", "bedroom_humidifier": "加湿器",
    "entrance_lock": "智能锁", "entrance_light": "玄关灯",
    "entrance_alarm": "安防模式",
    "balcony_rack": "晾衣架", "balcony_light": "阳台灯"
}

clients = {}
running = True


def signal_handler(sig, frame):
    global running
    print("\n🛑 正在关闭所有设备...")
    running = False
    for device_id, client in clients.items():
        try:
            client.publish(f"device/{device_id}/offline", "offline")
            client.disconnect()
            print(f"   {DEVICE_NAMES.get(device_id, device_id)} 已离线")
        except:
            pass
    print("✅ 所有设备已关闭")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)

def cleanup():
    """程序退出时自动执行（包括直接关窗口）"""
    print("\n🔄 程序退出，发送离线通知...")
    for device_id, client in clients.items():
        try:
            client.publish(f"device/{device_id}/offline", "offline")
            print(f"   {DEVICE_NAMES.get(device_id, device_id)} 已发送离线")
        except:
            pass
    time.sleep(0.3)

def connect_device(device_id):
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print(f"✅ {DEVICE_NAMES.get(device_id, device_id)} ({device_id}) 已上线")
            client.publish(f"device/{device_id}/online", "online")
            client.subscribe(f"device/{device_id}/command")
        else:
            print(f"❌ {device_id} 连接失败，错误码: {rc}")

    def on_message(client, userdata, msg):
        try:
            payload = msg.payload.decode()
            print("-" * 50)
            print(f"📩 设备: {DEVICE_NAMES.get(device_id, device_id)} ({device_id})")
            print(f"📋 原始消息: {payload}")
            
            try:
                data = json.loads(payload)
                command = data.get('command')
                value = data.get('value')
            except:
                print(f"⚠️ 无法解析JSON: {payload}")
                return

            name = DEVICE_NAMES.get(device_id, device_id)
            print(f"📋 指令: {command}")
            print(f"📊 数值: {value}")

            # ===== 处理各类设备指令 =====
            if device_id in ["living_light1", "living_light2", "bedroom_light", "entrance_light", "balcony_light"]:
                if command == 'switch':
                    print(f"   💡 {name} {'开启' if value == 1 else '关闭'}")
                elif command == 'set_brightness':
                    print(f"   💡 {name} 亮度 → {value}%")

            elif device_id == "living_tv":
                if command == 'switch':
                    print(f"   📺 {name} {'开机' if value == 1 else '关机'}")
                elif command == 'set_volume':
                    print(f"   📺 {name} 音量 → {value}%")
                elif command == 'set_channel':
                    print(f"   📺 {name} 频道 → {value}")
                elif command == 'set_timer':
                    print(f"   📺 {name} 定时 → {value}分钟" if value > 0 else f"   📺 {name} 定时关闭")

            elif device_id in ["living_ac", "bedroom_ac"]:
                if command == 'switch':
                    print(f"   ❄️ {name} {'开启' if value == 1 else '关闭'}")
                elif command == 'set_temperature':
                    print(f"   ❄️ {name} 温度 → {value}°C")
                elif command == 'set_mode':
                    try:
                        requests.post(
                            f"{FLASK_URL}/api/device/state",
                            json={"deviceId": device_id, "mode": value},
                            timeout=1
                        )
                    except:
                        pass
                    print(f"   ❄️ {name} 模式 → {value}")
                elif command == 'set_fan_speed':
                    fan_map = {0: '自动', 1: '低', 2: '中', 3: '高'}
                    print(f"   ❄️ {name} 风速 → {fan_map.get(value, value)}")
                elif command == 'set_wind_direction':
                    print(f"   ❄️ {name} 风向 → {value}")

            elif device_id == "living_speaker":
                if command == 'switch':
                    print(f"   🔊 {name} {'开启' if value == 1 else '关闭'}")
                elif command == 'set_volume':
                    print(f"   🔊 {name} 音量 → {value}%")
                elif command == 'set_speaker_mode':
                    try:
                        requests.post(
                            f"{FLASK_URL}/api/device/state",
                            json={"deviceId": device_id, "speaker_mode": value},
                            timeout=1
                        )
                    except:
                        pass
                    print(f"   🔊 {name} 音效 → {value}")

            elif device_id == "living_vacuum":
                if command == 'switch':
                    print(f"   🤖 {name} {'开启' if value == 1 else '关闭'}")
                elif command == 'set_vacuum_mode':
                    try:
                        requests.post(
                            f"{FLASK_URL}/api/device/state",
                            json={"deviceId": device_id, "vacuum_mode": value},
                            timeout=1
                        )
                    except:
                        pass
                    print(f"   🤖 {name} 模式 → {value}")

            elif device_id in ["living_curtain", "bedroom_curtain"]:
                if command == 'switch':
                    print(f"   🪟 {name} {'开启' if value == 1 else '关闭'}")
                elif command == 'set_percent':
                    print(f"   🪟 {name} 开合度 → {value}%")

            elif device_id == "kitchen_dishwasher":
                if command == 'switch':
                    print(f"   🧼 {name} {'开启' if value == 1 else '关闭'}")
                elif command == 'set_dishwasher_mode':
                    try:
                        requests.post(
                            f"{FLASK_URL}/api/device/state",
                            json={"deviceId": device_id, "dishwasher_mode": value},
                            timeout=1
                        )
                    except:
                        pass
                    print(f"   🧼 {name} 模式 → {value}")

            elif device_id == "kitchen_hood":
                if command == 'switch':
                    print(f"   💨 {name} {'开启' if value == 1 else '关闭'}")
                elif command == 'set_fan_speed':
                    fan_map = {0: '关闭', 1: '低', 2: '中', 3: '高'}
                    print(f"   💨 {name} 风量 → {fan_map.get(value, value)}")
                elif command == 'set_light':
                    print(f"   💨 {name} 照明 → {'开启' if value == 1 else '关闭'}")

            elif device_id == "kitchen_fridge":
                if command == 'switch':
                    print(f"   🧊 {name} {'开启' if value == 1 else '关闭'}")
                elif command == 'set_fridge_mode':
                    # ===== 根据模式设置温度 =====
                    if value == '智能':
                        temp = 4
                        freezer = -18
                    elif value == '速冻':
                        temp = 2
                        freezer = -25
                    elif value == '假日':
                        temp = 6
                        freezer = -15
                    else:
                        temp = 4
                        freezer = -18
                    
                    # ===== 上报模式 + 温度到Redis =====
                    try:
                        requests.post(
                            f"{FLASK_URL}/api/device/state",
                            json={"deviceId": device_id, "fridge_mode": value, "temperature": temp, "freezerTemp": freezer},
                            timeout=1
                        )
                    except:
                        pass
                    print(f"   🧊 {name} 模式 → {value}（冷藏{temp}°C，冷冻{freezer}°C）")
                elif command == 'set_fridge_temp':
                    print(f"   🧊 {name} 冷藏温度 → {value}°C")
                elif command == 'set_freezer_temp':
                    print(f"   🧊 {name} 冷冻温度 → {value}°C")
                elif command == 'set_temperature':
                    print(f"   🧊 {name} 温度 → {value}°C")

            elif device_id == "kitchen_water":
                if command == 'switch':
                    print(f"   🔥 {name} {'开启' if value == 1 else '关闭'}")
                elif command == 'set_temperature':
                    print(f"   🔥 {name} 温度 → {value}°C")

            elif device_id == "kitchen_stove":
                if command == 'switch':
                    print(f"   🍳 {name} {'开启' if value == 1 else '关闭'}")
                elif command == 'set_power':
                    print(f"   🍳 {name} 火力 → {value}%")

            elif device_id == "bedroom_humidifier":
                if command == 'switch':
                    print(f"   💨 {name} {'开启' if value == 1 else '关闭'}")
                elif command == 'set_mist':
                    print(f"   💨 {name} 雾量 → {value}%")

            elif device_id == "entrance_lock":
                if command == 'switch' or command == 'lock_unlock':
                    print(f"   🔐 {name} {'开锁' if value == 1 else '上锁'}")

            elif device_id == "entrance_alarm":
                if command == 'switch' or command == 'alarm_switch':
                    if value == 0:
                        print(f"   🔔 {name} → 撤防")
                    elif value == 1:
                        print(f"   🔔 {name} → 布防")
                    else:
                        print(f"   🔔 {name} → 报警中")

            elif device_id == "balcony_rack":
                if command == 'switch':
                    print(f"   👕 {name} {'开启' if value == 1 else '关闭'}")
                elif command == 'set_rack_light':
                    print(f"   👕 {name} 照明 → {'开启' if value == 1 else '关闭'}")
                elif command == 'set_rack_position':
                    print(f"   👕 {name} 位置 → {value}%")

            else:
                print(f"   📋 {name} {command} = {value}")

            print(f"✅ {name} 执行完成")
            print("-" * 50)

            # ===== 上报状态 =====
            state_msg = {
                "deviceId": device_id,
                "status": "online",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }

            if command == 'switch':
                state_msg["power"] = 'on' if value == 1 else 'off'
            elif command == 'set_brightness':
                state_msg["power"] = 'on' if value > 0 else 'off'
                state_msg["brightness"] = value
            elif command == 'set_volume':
                state_msg["power"] = 'on'
                state_msg["volume"] = value
            elif command == 'set_channel':
                state_msg["power"] = 'on'
                state_msg["channel"] = value
            elif command == 'set_timer':
                state_msg["power"] = 'on'
                state_msg["timer"] = value
            elif command == 'set_temperature':
                state_msg["power"] = 'on'
                state_msg["temperature"] = value
            elif command == 'set_freezer_temp':
                state_msg["power"] = 'on'
                state_msg["freezerTemp"] = value
            elif command == 'set_fridge_temp':
                state_msg["power"] = 'on'
                state_msg["temperature"] = value
            elif command == 'set_mode':
                state_msg["power"] = 'on'
                state_msg["mode"] = value
            elif command == 'set_fan_speed':
                state_msg["power"] = 'on'
                state_msg["fanSpeed"] = value
            elif command == 'set_wind_direction':
                state_msg["power"] = 'on'
                state_msg["windDirection"] = value
            elif command == 'set_percent':
                state_msg["power"] = 'on' if value > 0 else 'off'
                state_msg["percent"] = value
            elif command == 'set_power':
                state_msg["power"] = 'on' if value > 0 else 'off'
                state_msg["powerLevel"] = value
            elif command == 'set_mist':
                state_msg["power"] = 'on' if value > 0 else 'off'
                state_msg["mistLevel"] = value
            elif command == 'set_light':
                state_msg["power"] = 'on'
                state_msg["light"] = value == 1
            elif command == 'set_speaker_mode':
                state_msg["power"] = 'on'
                state_msg["speaker_mode"] = value
            elif command == 'set_vacuum_mode':
                state_msg["power"] = 'on'
                state_msg["vacuum_mode"] = value
            elif command == 'set_dishwasher_mode':
                state_msg["power"] = 'on'
                state_msg["dishwasher_mode"] = value
            elif command == 'set_fridge_mode':
                state_msg["power"] = 'on'
                state_msg["fridge_mode"] = value
                # 如果是冰箱模式切换，还要带上温度
                if 'temp' in locals():
                    state_msg["temperature"] = temp
                    state_msg["freezerTemp"] = freezer
            elif command == 'set_rack_light':
                state_msg["power"] = 'on'
                state_msg["light"] = value == 1
            elif command == 'set_rack_position':
                state_msg["power"] = 'on'
                state_msg["position"] = value
            elif command == 'lock_unlock':
                state_msg["power"] = 'on'
                state_msg["lock_state"] = 'unlocked' if value == 1 else 'locked'
            elif command == 'alarm_switch':
                state_msg["power"] = 'on'
                if value == 0:
                    state_msg["alarm_state"] = 'disarmed'
                elif value == 1:
                    state_msg["alarm_state"] = 'armed'
                else:
                    state_msg["alarm_state"] = 'alarming'
            else:
                state_msg["power"] = 'on'
                state_msg["temperature"] = 26

            client.publish(f"device/{device_id}/state", json.dumps(state_msg))

        except Exception as e:
            print(f"⚠️ {device_id} 处理指令出错: {e}")
            import traceback
            traceback.print_exc()

    def on_disconnect(client, userdata, rc):
        print(f"⚠️ {DEVICE_NAMES.get(device_id, device_id)} 断开连接")

    try:
        client = mqtt.Client()
        # 当设备异常断线时，MQTT Broker 自动发布这条消息
        client.will_set(
            topic=f"device/{device_id}/offline",
            payload="offline",
            qos=1,
            retain=True
        )
        client.on_connect = on_connect
        client.on_message = on_message
        client.on_disconnect = on_disconnect
        client.connect(BROKER, PORT, 60)
        client.loop_start()
        clients[device_id] = client
        return True
    except Exception as e:
        print(f"❌ {device_id} 启动失败: {e}")
        return False


def main():
    print("=" * 60)
    print("🏠 智能家居设备模拟器")
    print("=" * 60)
    print(f"📡 MQTT Broker: {BROKER}:{PORT}")
    print(f"📋 共 {len(ALL_DEVICES)} 个设备")
    print("=" * 60)
    print()

    print("🔄 正在连接所有设备...")
    for device_id in ALL_DEVICES:
        connect_device(device_id)
        time.sleep(0.1)

    # ===== 注册退出清理函数（直接关窗口也能触发） =====
    atexit.register(cleanup)

    print()
    print("=" * 60)
    print("✅ 所有设备已上线！")
    print("=" * 60)
    print()
    print("📌 操作说明:")
    print("   • 在网页上控制设备，终端会显示收到的指令")
    print("   • 按 Ctrl+C 让所有设备离线")
    print("   • 直接关闭窗口也会自动发送离线通知")
    print()
    print("=" * 60)
    print("🔄 等待指令中...")
    print()

    while running:
        time.sleep(1)


if __name__ == "__main__":
    try:
        import paho.mqtt.client as mqtt
    except ImportError:
        print("❌ 请先安装 paho-mqtt: pip install paho-mqtt")
        sys.exit(1)

    main()