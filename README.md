# 物联网设备离线指令缓存与同步系统

##项目简介
在智能家居使用中，设备常因Wi-Fi信号不稳定、路由器重启或意外断电等原因突然离线，导致用户发出的控制指令无法送达。本项目通过 “在线即时下发 + 离线自动缓存 + 上线自动补发” 的机制，确保用户对设备的每一次操作都能最终被执行，不再受设备离线困扰。

##技术栈

- 前端：HTML + CSS + JavaScript
- 后端：Flask
- 通信：MQTT
- 缓存：Redis
- 模拟设备：Python

##系统架构
<img width="767" height="521" alt="image" src="https://github.com/user-attachments/assets/60a64038-d06c-4d19-9442-06000cbe83e3" />

##功能特性
设备在线控制：设备在线时指令通过MQTT实时下发；
离线指令缓存：设备离线时指令自动存入Redis队列，不丢失；
上线自动补发：设备上线后按顺序逐条补发全部指令，无需用户干预；
异常断线检测：利用MQTT遗嘱消息机制，实时监听设备状态；
多设备类型支持：覆盖5个房间共21种智能设备，涵盖照明、温控、影音、安防、清洁、家电等品类。

##快速开始 ###环境要求
Python 3.8 或更高版本
Redis 5.0 或更高版本
Mosquitto 2.0 或更高版本（MQTT Broker）
web浏览器（Chrome、Firefox、Edge等）

###安装步骤

```bash
# 1. 克隆项目
git clone https://github.com/nxysdsnt/shadow.git
# 2. 进入项目目录
cd
# 3. 安装依赖
pip install -r requirements.txt
# 4. 启动Redis
redis-server
# 5. 启动MQTT Broker
mosquitto -v
# 6. 启动后端
python flask_server.py
# 7. 启动监听器（新开一个终端窗口）
python mqtt_listener.py
# 8. 启动模拟设备（新开一个终端窗口）
python device_simulator.py
# 9. 打开前端
双击 index.html
```
