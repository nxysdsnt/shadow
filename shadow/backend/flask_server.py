from flask import Flask, request, jsonify
from flask_cors import CORS
from redis_operator import RedisOperator
import json

# 创建Flask应用
app = Flask(__name__)
VALID_COMMANDS = {
    # 灯光类
    "light_switch": {"type": "int", "min": 0, "max": 1},
    "light_brightness": {"type": "int", "min": 0, "max": 100},
    "light_color_temp": {"type": "str", "allowed": ["warm", "natural", "cold"]},
    # 空调类
    "ac_switch": {"type": "int", "min": 0, "max": 1},
    "set_temperature": {"type": "int", "min": 16, "max": 30},
    "ac_mode": {"type": "str", "allowed": ["cool", "heat", "fan", "dry", "auto"]},
    "ac_fan_speed": {"type": "int", "min": 0, "max": 3},
    # 窗帘类
    "curtain_switch": {"type": "int", "min": 0, "max": 1},
    "curtain_percent": {"type": "int", "min": 0, "max": 100},
    # 插座类
    "socket_power": {"type": "int", "min": 0, "max": 1},
    # 门锁类
    "lock_unlock": {"type": "int", "min": 0, "max": 1},
    "alarm_switch": {"type": "int", "min": 0, "max": 1},
    # 扫地机
    "vacuum_start": {"type": "int", "min": 0, "max": 1},
    "vacuum_mode": {"type": "str", "allowed": ["quiet", "strong", "auto"]},
    # 场景类
    "scene_mode": {"type": "str", "allowed": ["home", "away", "sleep", "movie"]},
    # 运维类
    "device_reboot": {"type": "int", "min": 0, "max": 1},
    "device_reset": {"type": "int", "min": 0, "max": 1},
}
CORS(app)

# 创建Redis操作对象
redis_ops = RedisOperator()

# 模拟的设备数据
device_data = {
    "room01": {
        "deviceId": "room01",
        "temperature": 25,
        "status": "online",
        "last_command": None
    }
}


@app.route('/api/device/status', methods=['GET'])
def get_device_status():
    """获取设备状态"""
    device_id = request.args.get('deviceId', 'room01')
    
    redis_status = redis_ops.get_device_status(device_id)
    if redis_status:
        if device_id in device_data:
            device_data[device_id].update(redis_status)
        else:
            device_data[device_id] = redis_status
        device_data[device_id]['deviceId'] = device_id
    
    cached_command = redis_ops.get_command(device_id)
    has_pending = cached_command is not None
    
    result = {
        "code": 0,
        "data": {
            **device_data.get(device_id, {}),
            "hasPending": has_pending
        }
    }
    return jsonify(result)


@app.route('/api/device/command', methods=['POST'])
def send_command():
    """下发指令"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"code": 1, "message": "请求体不能为空"}), 400

        device_id = data.get('deviceId', 'room01')
        command = data.get('command')
        value = data.get('value')

        if not command:
            return jsonify({"code": 1, "message": "缺少command字段"}), 400

        if command not in VALID_COMMANDS:
            return jsonify({"code": 1, "message": f"不支持的指令：{command}"}), 400

        command_info = VALID_COMMANDS[command]
        if command_info["type"] == "int":
            try:
                value = int(value)
            except (TypeError, ValueError):
                return jsonify({"code": 1, "message": f"指令 {command} 的值必须是整数"}), 400
            if not (command_info["min"] <= value <= command_info["max"]):
                return jsonify({"code": 1, "message": f"指令 {command} 的值必须在 {command_info['min']} 到 {command_info['max']} 之间"}), 400
        elif command_info["type"] == "str":
            if not isinstance(value, str):
                return jsonify({"code": 1, "message": f"指令 {command} 的值必须是字符串"}), 400
            if value not in command_info["allowed"]:
                return jsonify({"code": 1, "message": f"指令 {command} 的值必须是 {command_info['allowed']} 中的一个"}), 400

        command_data = {
            "deviceId": device_id,
            "command": command,
            "value": value
        }
        redis_ops.save_command(device_id, command_data)

        if device_id in device_data:
            device_data[device_id]['last_command'] = command_data

        return jsonify({
            "code": 0,
            "message": "指令已保存，等待设备处理",
            "data": command_data
        })

    except Exception as e:
        return jsonify({"code": 1, "message": f"错误：{str(e)}"}), 500


@app.route('/api/device/logs', methods=['GET'])
def get_logs():
    """获取操作日志"""
    logs = [
        {"time": "10:00", "content": "系统启动", "type": "info"},
        {"time": "10:05", "content": "设备 room01 上线", "type": "success"},
        {"time": "10:10", "content": "指令已下发：设置温度26度", "type": "info"},
    ]
    return jsonify({"code": 0, "data": logs})


@app.route('/api/device/online', methods=['POST'])
def device_online():
    """设备上线通知"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"code": 1, "message": "请求体不能为空"}), 400
            
        device_id = data.get('deviceId', 'room01')
        
        redis_ops.update_device_status(device_id, {"status": "online", "temperature": 25})
        
        cached = redis_ops.get_command(device_id)
        if cached:
            return jsonify({
                "code": 0,
                "message": "设备上线，有待补发的指令",
                "hasPending": True,
                "pendingCommand": cached
            })
        
        return jsonify({"code": 0, "message": "设备上线成功", "hasPending": False})
        
    except Exception as e:
        return jsonify({"code": 1, "message": f"错误：{str(e)}"}), 500


@app.route('/api/device/offline', methods=['POST'])
def device_offline():
    """设备离线通知"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"code": 1, "message": "请求体不能为空"}), 400
            
        device_id = data.get('deviceId', 'room01')
        
        redis_ops.update_device_status(device_id, {"status": "offline", "temperature": 0})
        
        return jsonify({"code": 0, "message": "设备已离线"})
        
    except Exception as e:
        return jsonify({"code": 1, "message": f"错误：{str(e)}"}), 500

@app.route('/api/device/fetch', methods=['GET'])
def device_fetch_command():
    """
    设备轮询获取待执行的指令（获取后从缓存中删除）
    请求示例：GET /api/device/fetch?deviceId=room01
    """
    try:
        device_id = request.args.get('deviceId', 'room01')
        cached = redis_ops.get_command(device_id)
        if cached:
            # 取到指令后立即删除（影子系统：取走即视为设备将执行）
            redis_ops.delete_command(device_id)
            return jsonify({"code": 0, "hasPending": True, "pendingCommand": cached})
        return jsonify({"code": 0, "hasPending": False})
    except Exception as e:
        return jsonify({"code": 1, "message": f"错误：{str(e)}"}), 500

@app.route('/api/device/ack', methods=['POST'])
def device_ack():
    """
    设备确认已执行指令（可选，客户端调用）
    请求体：{"deviceId": "room01", "result": "ok"}
    """
    try:
        data = request.get_json()
        device_id = data.get('deviceId', 'room01')
        # 在 fetch 接口已经删除了命令，这里作为幂等接口仅用于记录/日志
        # 可以在这里更新设备的 last_command 或写入持久日志
        return jsonify({"code": 0, "message": "ack 已接收"})
    except Exception as e:
        return jsonify({"code": 1, "message": f"错误：{str(e)}"}), 500


@app.route('/api/device/delete_command', methods=['POST'])
def delete_command():
    """删除设备指令"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"code": 1, "message": "请求体不能为空"}), 400
            
        device_id = data.get('deviceId', 'room01')
        
        redis_ops.delete_command(device_id)
        
        return jsonify({"code": 0, "message": f"设备 {device_id} 的指令已删除"})
        
    except Exception as e:
        return jsonify({"code": 1, "message": f"错误：{str(e)}"}), 500


if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Flask服务器启动中...")
    print("📡 访问地址: http://localhost:5000")
    print("=" * 50)
    print("📋 可用接口:")
    print("  1. GET  /api/device/status?deviceId=room01")
    print("  2. POST /api/device/command")
    print("  3. GET  /api/device/logs")
    print("  4. POST /api/device/online")
    print("  5. POST /api/device/offline")
    print("  6. POST /api/device/delete_command")
    print("=" * 50)
    print("按 Ctrl+C 停止服务器")
    app.run(host='0.0.0.0', port=5000, debug=True)
