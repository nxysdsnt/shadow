from flask import Flask, request, jsonify
from flask_cors import CORS
from redis_operator import RedisOperator
import json
from datetime import datetime
import paho.mqtt.client as mqtt

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})
redis_ops = RedisOperator()

mqtt_client = None
mqtt_connected = False

def init_mqtt_client():
    global mqtt_client, mqtt_connected
    try:
        mqtt_client = mqtt.Client()
        mqtt_client.connect("localhost", 1883, 60)
        mqtt_client.loop_start()
        mqtt_connected = True
        print("✅ MQTT全局客户端已初始化")
    except Exception as e:
        print(f"⚠️ MQTT初始化失败: {e}")
        mqtt_connected = False

init_mqtt_client()

ALL_DEVICES = {
    '客厅': [
        {'id': 'living_light1', 'name': '灯1'},
        {'id': 'living_light2', 'name': '灯2'},
        {'id': 'living_tv', 'name': '电视'},
        {'id': 'living_ac', 'name': '立式空调'},
        {'id': 'living_speaker', 'name': '音箱'},
        {'id': 'living_vacuum', 'name': '扫地机器人'},
        {'id': 'living_curtain', 'name': '窗帘'}
    ],
    '厨房': [
        {'id': 'kitchen_dishwasher', 'name': '洗碗机'},
        {'id': 'kitchen_hood', 'name': '油烟机'},
        {'id': 'kitchen_fridge', 'name': '冰箱'},
        {'id': 'kitchen_water', 'name': '热水器'},
        {'id': 'kitchen_stove', 'name': '灶台'}
    ],
    '卧室': [
        {'id': 'bedroom_ac', 'name': '空调'},
        {'id': 'bedroom_light', 'name': '吸顶灯'},
        {'id': 'bedroom_curtain', 'name': '窗帘'},
        {'id': 'bedroom_humidifier', 'name': '加湿器'}
    ],
    '玄关': [
        {'id': 'entrance_lock', 'name': '智能锁'},
        {'id': 'entrance_light', 'name': '灯'},
        {'id': 'entrance_alarm', 'name': '安防模式'}
    ],
    '阳台': [
        {'id': 'balcony_rack', 'name': '晾衣架'},
        {'id': 'balcony_light', 'name': '灯'}
    ]
}

VALID_COMMANDS = {
    "switch": {"type": "int", "min": 0, "max": 1},
    "set_brightness": {"type": "int", "min": 0, "max": 100},
    "set_volume": {"type": "int", "min": 0, "max": 100},
    "set_channel": {"type": "int", "min": 1, "max": 999},
    "set_timer": {"type": "int", "min": 0, "max": 999},
    "set_temperature": {"type": "int", "min": 16, "max": 30},           # 空调/热水器用
    "set_fridge_temp": {"type": "int", "min": 0, "max": 10},            # 冰箱冷藏
    "set_freezer_temp": {"type": "int", "min": -25, "max": -10},        # 冰箱冷冻
    "set_mode": {"type": "str", "allowed": ["制冷", "制热", "送风", "除湿", "自动"]},
    "set_fan_speed": {"type": "int", "min": 0, "max": 3},
    "set_wind_direction": {"type": "str", "allowed": ["上下", "左右", "关闭"]},
    "set_percent": {"type": "int", "min": 0, "max": 100},
    "set_power": {"type": "int", "min": 0, "max": 100},
    "set_mist": {"type": "int", "min": 0, "max": 100},
    "set_light": {"type": "int", "min": 0, "max": 1},
    "set_speaker_mode": {"type": "str", "allowed": ["标准", "流行", "摇滚", "古典", "爵士"]},
    "set_vacuum_mode": {"type": "str", "allowed": ["自动", "强力", "安静", "拖地"]},
    "set_dishwasher_mode": {"type": "str", "allowed": ["标准", "强力", "节能", "快速", "玻璃", "杀菌"]},
    "set_fridge_mode": {"type": "str", "allowed": ["智能", "速冻", "假日"]},
    "set_rack_position": {"type": "int", "min": 0, "max": 100},
    "set_rack_light": {"type": "int", "min": 0, "max": 1},
    "lock_unlock": {"type": "int", "min": 0, "max": 1},
    "alarm_switch": {"type": "int", "min": 0, "max": 2},
}

LOG_KEY = "system_logs"
MAX_LOG_COUNT = 50

def add_log(content, log_type="info"):
    if not redis_ops.client:
        return
    try:
        log_entry = {"time": datetime.now().strftime("%H:%M:%S"), "content": content, "type": log_type}
        logs = redis_ops.client.lrange(LOG_KEY, 0, -1) or []
        log_list = [json.loads(log) for log in logs] if logs else []
        log_list.append(log_entry)
        if len(log_list) > MAX_LOG_COUNT:
            log_list = log_list[-MAX_LOG_COUNT:]
        redis_ops.client.delete(LOG_KEY)
        for log in log_list:
            redis_ops.client.rpush(LOG_KEY, json.dumps(log))
    except Exception as e:
        print(f"⚠️ 添加日志失败: {e}")


@app.route('/api/device/status', methods=['GET'])
def get_device_status():
    """获取所有设备状态"""
    try:
        all_status = {}
        for room, devices in ALL_DEVICES.items():
            all_status[room] = []
            for device in devices:
                status_data = redis_ops.get_device_status(device['id']) or {}
                is_online = redis_ops.is_online(device['id'])
                has_pending = redis_ops.has_pending_commands(device['id'])
                
                all_status[room].append({
                    "id": device['id'],
                    "name": device['name'],
                    "status": "online" if is_online else "offline",
                    "power": status_data.get('power', 'off'),
                    "pending": has_pending,
                    "volume": status_data.get('volume'),
                    "channel": status_data.get('channel'),
                    "timer": status_data.get('timer'),
                    "temperature": status_data.get('temperature'),
                    "freezerTemp": status_data.get('freezerTemp'),
                    "mode": status_data.get('mode'),
                    "fanSpeed": status_data.get('fanSpeed'),
                    "windDirection": status_data.get('windDirection'),
                    "brightness": status_data.get('brightness'),
                    "percent": status_data.get('percent'),
                    "powerLevel": status_data.get('powerLevel'),
                    "mistLevel": status_data.get('mistLevel'),
                    "battery": status_data.get('battery'),
                    "position": status_data.get('position'),
                    "light": status_data.get('light'),
                    "speaker_mode": status_data.get('speaker_mode'),
                    "vacuum_mode": status_data.get('vacuum_mode'),
                    "dishwasher_mode": status_data.get('dishwasher_mode'),
                    "fridge_mode": status_data.get('fridge_mode'),
                    "lock_state": status_data.get('lock_state'),
                    "alarm_state": status_data.get('alarm_state')
                })
        return jsonify({"code": 0, "data": all_status})
    except Exception as e:
        return jsonify({"code": 1, "message": str(e)}), 500


@app.route('/api/device/command', methods=['POST'])
def send_command():
    """下发指令：在线→MQTT，离线→Redis队列"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"code": 1, "message": "请求体不能为空"}), 400

        device_id = data.get('deviceId')
        command = data.get('command')
        value = data.get('value')

        if not device_id or not command:
            return jsonify({"code": 1, "message": "缺少deviceId或command"}), 400

        # 指令白名单校验
        if command not in VALID_COMMANDS:
            return jsonify({"code": 1, "message": f"不支持的指令：{command}"}), 400

        cmd_info = VALID_COMMANDS[command]
        if cmd_info["type"] == "int":
            try:
                value = int(value)
            except (TypeError, ValueError):
                return jsonify({"code": 1, "message": f"指令 {command} 的值必须是整数"}), 400
            if not (cmd_info["min"] <= value <= cmd_info["max"]):
                return jsonify({"code": 1, "message": f"指令 {command} 的值必须在 {cmd_info['min']} 到 {cmd_info['max']} 之间"}), 400
        elif cmd_info["type"] == "str":
            if not isinstance(value, str) or value not in cmd_info["allowed"]:
                return jsonify({"code": 1, "message": f"指令 {command} 的值必须是 {cmd_info['allowed']} 中的一个"}), 400

        command_data = {
            "deviceId": device_id,
            "command": command,
            "value": value,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # ===== 核心：判断设备是否在线 =====
        is_online = redis_ops.is_online(device_id)

        if is_online:
            # 在线：立即通过MQTT下发
            global mqtt_client, mqtt_connected
            if mqtt_connected and mqtt_client:
                try:
                    mqtt_client.publish(f"device/{device_id}/command", json.dumps(command_data))
                    add_log(f"📤 {device_id} {command}={value} (在线下发)", "info")
                    return jsonify({"code": 0, "message": "指令已下发", "status": "delivered", "data": command_data})
                except Exception as e:
                    print(f"⚠️ MQTT下发失败: {e}")
                    redis_ops.push_command(device_id, command_data)
                    add_log(f"📦 {device_id} {command}={value} (MQTT失败，转为缓存)", "warning")
                    return jsonify({"code": 0, "message": "MQTT失败，已缓存", "status": "cached", "data": command_data})
            else:
                redis_ops.push_command(device_id, command_data)
                add_log(f"📦 {device_id} {command}={value} (MQTT未连接，已缓存)", "warning")
                return jsonify({"code": 0, "message": "MQTT未连接，已缓存", "status": "cached", "data": command_data})
        else:
            # 离线：缓存到Redis队列
            redis_ops.push_command(device_id, command_data)
            add_log(f"📦 {device_id} {command}={value} (设备离线，已缓存)", "warning")
            return jsonify({"code": 0, "message": "设备离线，已缓存", "status": "cached", "data": command_data})

    except Exception as e:
        return jsonify({"code": 1, "message": str(e)}), 500


@app.route('/api/device/online', methods=['POST'])
def device_online():
    """设备上线通知 - 由MQTT监听器调用"""
    try:
        data = request.get_json()
        device_id = data.get('deviceId') if data else None
        if not device_id:
            return jsonify({"code": 1, "message": "缺少deviceId"}), 400

        # 标记在线
        redis_ops.set_online(device_id)

        # 获取待补发指令
        pending = redis_ops.peek_all_commands(device_id)
        print(f"🟢 设备 {device_id} 上线，待补发指令: {len(pending)}条")

        # 更新状态
        status = redis_ops.get_device_status(device_id) or {}
        status['status'] = 'online'
        redis_ops.update_device_status(device_id, status)

        add_log(f"🟢 设备 {device_id} 上线", "success")

        if pending:
            return jsonify({
                "code": 0,
                "message": "设备上线，有待补发指令",
                "hasPending": True,
                "pendingCommands": pending
            })
        return jsonify({"code": 0, "message": "设备上线成功", "hasPending": False})

    except Exception as e:
        return jsonify({"code": 1, "message": str(e)}), 500


@app.route('/api/device/offline', methods=['POST'])
def device_offline():
    """设备离线通知 - 由MQTT监听器调用"""
    try:
        data = request.get_json()
        device_id = data.get('deviceId') if data else None
        if not device_id:
            return jsonify({"code": 1, "message": "缺少deviceId"}), 400

        # 标记离线
        redis_ops.set_offline(device_id)

        # 更新状态
        status = redis_ops.get_device_status(device_id) or {}
        status['status'] = 'offline'
        status['power'] = 'off'
        redis_ops.update_device_status(device_id, status)

        add_log(f"🔴 设备 {device_id} 离线", "error")
        print(f"🔴 设备 {device_id} 已标记离线")
        return jsonify({"code": 0, "message": "设备已离线"})

    except Exception as e:
        return jsonify({"code": 1, "message": str(e)}), 500


@app.route('/api/device/state', methods=['POST'])
def device_state():
    """设备状态上报 - 由MQTT监听器调用"""
    try:
        data = request.get_json()
        device_id = data.get('deviceId') if data else None
        if not device_id:
            return jsonify({"code": 1, "message": "缺少deviceId"}), 400

        # 提取所有状态字段
        status_fields = [
            'status', 'power', 'temperature','freezerTemp', 'volume', 'channel', 'timer',
            'mode', 'fanSpeed', 'windDirection', 'brightness', 'percent',
            'powerLevel', 'mistLevel', 'battery', 'position', 'light',
            'speaker_mode', 'vacuum_mode', 'dishwasher_mode', 'fridge_mode',
            'lock_state', 'alarm_state'
        ]
        status_data = {}
        for field in status_fields:
            if field in data and data[field] is not None:
                status_data[field] = data[field]

        if status_data:
            redis_ops.update_device_status(device_id, status_data)

        # 确保在线标记存在
        redis_ops.set_online(device_id)

        print(f"✅ 设备 {device_id} 状态已保存")
        return jsonify({"code": 0, "message": "状态上报成功"})

    except Exception as e:
        print(f"❌ 状态上报失败: {e}")
        return jsonify({"code": 1, "message": str(e)}), 500


@app.route('/api/device/logs', methods=['GET'])
def get_logs():
    try:
        if not redis_ops.client:
            return jsonify({"code": 0, "data": [{"time": "--:--:--", "content": "Redis未连接", "type": "error"}]})
        logs = redis_ops.client.lrange(LOG_KEY, 0, -1) or []
        log_list = [json.loads(log) for log in logs] if logs else []
        if not log_list:
            log_list = [{"time": datetime.now().strftime("%H:%M:%S"), "content": "系统启动", "type": "info"}]
        return jsonify({"code": 0, "data": log_list})
    except Exception as e:
        return jsonify({"code": 1, "message": str(e)}), 500


@app.route('/api/device/list', methods=['GET'])
def get_device_list():
    devices = []
    for room, room_devices in ALL_DEVICES.items():
        for device in room_devices:
            devices.append({"id": device['id'], "name": device['name'], "room": room})
    return jsonify({"code": 0, "data": devices})


@app.route('/api/device/clear', methods=['POST'])
def clear_all():
    try:
        if redis_ops.client:
            redis_ops.client.flushall()
            return jsonify({"code": 0, "message": "所有数据已清空"})
        return jsonify({"code": 1, "message": "Redis未连接"}), 500
    except Exception as e:
        return jsonify({"code": 1, "message": str(e)}), 500

@app.route('/api/device/clear_command', methods=['POST'])
def clear_command_queue():
    """清空指定设备的指令队列"""
    try:
        data = request.get_json()
        device_id = data.get('deviceId') if data else None
        if not device_id:
            return jsonify({"code": 1, "message": "缺少deviceId"}), 400

        redis_ops.clear_commands(device_id)
        print(f"🗑️ 已清空 {device_id} 的指令队列")
        return jsonify({"code": 0, "message": "队列已清空"})
    except Exception as e:
        return jsonify({"code": 1, "message": str(e)}), 500

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Flask服务器启动中...")
    print("📡 访问地址: http://localhost:5000")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)