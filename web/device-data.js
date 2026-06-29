// ================================================================
//  设备数据 - 默认数据（仅作为后端未连接时的备用数据）
// ================================================================

const DEFAULT_DEVICES = {
    '客厅': [
        { id: 'living_light1', name: '灯1', icon: '💡', status: 'online', power: 'on', brightness: 100, pending: false },
        { id: 'living_light2', name: '灯2', icon: '💡', status: 'online', power: 'off', brightness: 0, pending: false },
        { id: 'living_tv', name: '电视', icon: '📺', status: 'online', power: 'on', volume: 30, channel: 5, timer: 0, pending: false },
        { id: 'living_ac', name: '立式空调', icon: '❄️', status: 'online', power: 'on', temperature: 26, mode: '制冷', fanSpeed: 2, windDirection: '上下', timer: 0, pending: false },
        { id: 'living_speaker', name: '音箱', icon: '🔊', status: 'online', power: 'off', volume: 50, mode: '标准', pending: false },
        { id: 'living_vacuum', name: '扫地机器人', icon: '🤖', status: 'online', power: 'charging', battery: 80, mode: '自动', pending: false },
        { id: 'living_curtain', name: '窗帘', icon: '🪟', status: 'online', power: 'on', percent: 50, pending: false }
    ],
    '厨房': [
        { id: 'kitchen_dishwasher', name: '洗碗机', icon: '🧼', status: 'online', power: 'off', mode: '标准', progress: 0, timeRemaining: 0, pending: false },
        { id: 'kitchen_hood', name: '油烟机', icon: '💨', status: 'online', power: 'off', fanSpeed: 0, light: false, pending: false },
        { id: 'kitchen_fridge', name: '冰箱', icon: '🧊', status: 'online', power: 'on', temperature: 4, freezerTemp: -18, mode: '智能', pending: false },
        { id: 'kitchen_water', name: '热水器', icon: '🔥', status: 'online', power: 'on', temperature: 55, pending: false },
        { id: 'kitchen_stove', name: '灶台', icon: '🍳', status: 'online', power: 'off', powerLevel: 0, pending: false }
    ],
    '卧室': [
        { id: 'bedroom_ac', name: '空调', icon: '❄️', status: 'online', power: 'on', temperature: 25, mode: '制冷', fanSpeed: 2, windDirection: '上下', timer: 0, pending: false },
        { id: 'bedroom_light', name: '吸顶灯', icon: '💡', status: 'online', power: 'on', brightness: 100, pending: false },
        { id: 'bedroom_curtain', name: '窗帘', icon: '🪟', status: 'online', power: 'off', percent: 0, pending: false },
        { id: 'bedroom_humidifier', name: '加湿器', icon: '💨', status: 'online', power: 'on', mistLevel: 60, pending: false }
    ],
    '玄关': [
        { id: 'entrance_lock', name: '智能锁', icon: '🔐', status: 'online', power: 'locked', battery: 85, pending: false },
        { id: 'entrance_light', name: '灯', icon: '💡', status: 'online', power: 'on', brightness: 100, pending: false },
        { id: 'entrance_alarm', name: '安防模式', icon: '🔔', status: 'online', power: 'disarmed', pending: false }
    ],
    '阳台': [
        { id: 'balcony_rack', name: '晾衣架', icon: '👕', status: 'online', power: 'on', position: 50, light: false, isMoving: false, pending: false },
        { id: 'balcony_light', name: '灯', icon: '💡', status: 'online', power: 'off', brightness: 0, pending: false }
    ]
};

let allDevices = {};

function loadFromStorage() {
    try {
        const saved = localStorage.getItem('iot_devices_data');
        if (saved) {
            const parsed = JSON.parse(saved);
            const rooms = Object.keys(DEFAULT_DEVICES);
            let hasAllRooms = true;
            for (const room of rooms) {
                if (!parsed[room]) { hasAllRooms = false; break; }
            }
            if (hasAllRooms) {
                // ===== 修复：检查并修正冰箱温度 =====
                for (const room of rooms) {
                    const fridge = parsed[room].find(d => d.id === 'kitchen_fridge');
                    if (fridge) {
                        // 如果冷藏温度大于10度（异常），修正为4度
                        if (fridge.temperature > 10) {
                            fridge.temperature = 4;
                            console.log('🔧 已自动修正冰箱冷藏温度: 26 → 4');
                        }
                        // 如果冷冻温度大于0度（异常），修正为-18度
                        if (fridge.freezerTemp > 0) {
                            fridge.freezerTemp = -18;
                            console.log('🔧 已自动修正冰箱冷冻温度: → -18');
                        }
                    }
                }
                
                allDevices = parsed;
                // 保存修正后的数据到 localStorage
                saveToStorage();
                console.log('✅ 从 localStorage 加载数据成功（已修正异常值）');
                return true;
            }
        }
    } catch (e) {
        console.warn('读取 localStorage 失败:', e);
    }
    return false;
}

function saveToStorage() {
    try {
        localStorage.setItem('iot_devices_data', JSON.stringify(allDevices));
    } catch (e) {
        console.warn('保存数据失败:', e);
    }
}

function resetToDefault() {
    allDevices = JSON.parse(JSON.stringify(DEFAULT_DEVICES));
    saveToStorage();
}

// 初始化
if (!loadFromStorage()) {
    resetToDefault();
}

function getAllDevicesList() {
    const result = [];
    for (const room in allDevices) {
        allDevices[room].forEach(device => {
            result.push({ ...device, room: room });
        });
    }
    return result;
}

function getOnlineCount() {
    return getAllDevicesList().filter(d => d.status === 'online').length;
}

function getTotalCount() {
    return getAllDevicesList().length;
}

// 暴露全局
window.allDevices = allDevices;
window.saveToStorage = saveToStorage;
window.loadFromStorage = loadFromStorage;
window.resetToDefault = resetToDefault;
window.getOnlineCount = getOnlineCount;
window.getTotalCount = getTotalCount;
window.getAllDevicesList = getAllDevicesList;