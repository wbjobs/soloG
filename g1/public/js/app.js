const socket = io();

let currentRoomId = null;
let currentRole = null;
let webrtcManager = null;
let remoteControlManager = null;
let currentPermissionLevel = 'view';
let isControlSuspended = false;

const authSection = document.getElementById('auth-section');
const roomSection = document.getElementById('room-section');
const createRoomBtn = document.getElementById('create-room-btn');
const joinRoomBtn = document.getElementById('join-room-btn');
const roomIdInput = document.getElementById('room-id-input');
const currentRoomIdEl = document.getElementById('current-room-id');
const currentRoleEl = document.getElementById('current-role');
const copyRoomIdBtn = document.getElementById('copy-room-id');
const leaveRoomBtn = document.getElementById('leave-room-btn');

const hostView = document.getElementById('host-view');
const guestView = document.getElementById('guest-view');

const startShareBtn = document.getElementById('start-share-btn');
const stopShareBtn = document.getElementById('stop-share-btn');
const guestStatus = document.getElementById('guest-status');
const permissionPanel = document.getElementById('permission-panel');
const currentPermissionEl = document.getElementById('current-permission');
const controlRequest = document.getElementById('control-request');
const approveControlBtn = document.getElementById('approve-control-btn');
const denyControlBtn = document.getElementById('deny-control-btn');
const controlActive = document.getElementById('control-active');
const permissionLevelBadge = document.getElementById('permission-level-badge');
const revokeControlBtn = document.getElementById('revoke-control-btn');
const disableControlBtn = document.getElementById('disable-control-btn');
const controlSuspended = document.getElementById('control-suspended');
const resumeControlBtn = document.getElementById('resume-control-btn');
const localVideo = document.getElementById('local-video');

const guestPermissionEl = document.getElementById('guest-permission');
const requestControlBtn = document.getElementById('request-control-btn');
const releaseControlBtn = document.getElementById('release-control-btn');
const controlStatus = document.getElementById('control-status');
const controlStatusText = document.getElementById('control-status-text');
const remoteVideo = document.getElementById('remote-video');
const controlOverlay = document.getElementById('control-overlay');

const refreshLogsBtn = document.getElementById('refresh-logs-btn');
const logsContainer = document.getElementById('logs-container');

createRoomBtn.addEventListener('click', createRoom);
joinRoomBtn.addEventListener('click', joinRoom);
copyRoomIdBtn.addEventListener('click', copyRoomId);
leaveRoomBtn.addEventListener('click', leaveRoom);

startShareBtn.addEventListener('click', startScreenShare);
stopShareBtn.addEventListener('click', stopScreenShare);
approveControlBtn.addEventListener('click', () => handleControlApproval(true));
denyControlBtn.addEventListener('click', () => handleControlApproval(false));
revokeControlBtn.addEventListener('click', suspendControl);
resumeControlBtn.addEventListener('click', resumeControl);
disableControlBtn.addEventListener('click', disableControl);

requestControlBtn.addEventListener('click', requestControl);
releaseControlBtn.addEventListener('click', releaseControl);

refreshLogsBtn.addEventListener('click', refreshLogs);

function createRoom() {
    socket.emit('create-room', (response) => {
        if (response.success) {
            currentRoomId = response.roomId;
            currentRole = 'host';
            webrtcManager = new WebRTCManager(socket, currentRoomId);
            webrtcManager.setIsHost(true);
            remoteControlManager = new RemoteControlManager(socket, currentRoomId);
            showRoomSection();
        }
    });
}

function joinRoom() {
    const roomId = roomIdInput.value.trim().toUpperCase();
    if (!roomId) {
        alert('请输入房间号');
        return;
    }
    
    socket.emit('join-room', roomId, (response) => {
        if (response.success) {
            currentRoomId = roomId;
            currentRole = 'guest';
            webrtcManager = new WebRTCManager(socket, currentRoomId);
            webrtcManager.setIsHost(false);
            remoteControlManager = new RemoteControlManager(socket, currentRoomId);
            remoteControlManager.setControlOverlay(controlOverlay);
            remoteControlManager.setVideoElement(remoteVideo);
            showRoomSection();
        } else {
            alert(response.error);
        }
    });
}

function showRoomSection() {
    authSection.classList.add('hidden');
    roomSection.classList.remove('hidden');
    currentRoomIdEl.textContent = currentRoomId;
    currentRoleEl.textContent = currentRole === 'host' ? '主持人（共享方）' : '访客（观看方）';
    
    if (currentRole === 'host') {
        hostView.classList.remove('hidden');
        guestView.classList.add('hidden');
    } else {
        hostView.classList.add('hidden');
        guestView.classList.remove('hidden');
    }
    
    setupSocketListeners();
}

function setupSocketListeners() {
    socket.on('guest-joined', (data) => {
        guestStatus.classList.remove('hidden');
        permissionPanel.classList.remove('hidden');
        webrtcManager.setTargetId(data.guestId);
        if (webrtcManager.localStream) {
            webrtcManager.createOffer();
        }
    });

    socket.on('guest-left', () => {
        guestStatus.classList.add('hidden');
        permissionPanel.classList.add('hidden');
        controlRequest.classList.add('hidden');
        controlActive.classList.add('hidden');
        controlSuspended.classList.add('hidden');
        currentPermissionLevel = 'view';
        updatePermissionDisplay();
        if (webrtcManager) {
            webrtcManager.close();
            webrtcManager.createPeerConnection();
        }
    });

    socket.on('host-left', () => {
        alert('主持人已离开房间');
        leaveRoom();
    });

    socket.on('offer', async (data) => {
        if (currentRole === 'guest') {
            await webrtcManager.handleOffer(data.offer, data.hostId);
        }
    });

    socket.on('answer', async (data) => {
        if (currentRole === 'host') {
            await webrtcManager.handleAnswer(data.answer);
        }
    });

    socket.on('ice-candidate', async (data) => {
        await webrtcManager.handleIceCandidate(data.candidate);
    });

    socket.on('control-requested', (data) => {
        controlRequest.classList.remove('hidden');
        const levelText = data.requestedLevel === 'control' ? '完全控制' : '仅鼠标控制';
        controlRequest.querySelector('p').textContent = `访客请求 ${levelText} 权限`;
    });

    socket.on('control-request-cancelled', () => {
        controlRequest.classList.add('hidden');
    });

    socket.on('control-approved', (data) => {
        if (data.approved) {
            currentPermissionLevel = data.level;
            isControlSuspended = false;
            updatePermissionDisplay();
            
            controlStatus.classList.remove('hidden');
            controlStatus.classList.remove('warning');
            controlStatus.classList.add('success');
            const levelText = data.level === 'control' ? '完全控制' : '仅鼠标控制';
            controlStatusText.textContent = `已获得 ${levelText} 权限`;
            requestControlBtn.classList.add('hidden');
            releaseControlBtn.classList.remove('hidden');
            
            remoteControlManager.enableGuestControl();
        } else {
            controlStatus.classList.remove('hidden');
            controlStatus.classList.remove('success');
            controlStatus.classList.add('warning');
            controlStatusText.textContent = '控制请求被拒绝';
            setTimeout(() => {
                controlStatus.classList.add('hidden');
            }, 3000);
        }
    });

    socket.on('control-suspended', () => {
        isControlSuspended = true;
        controlStatus.classList.remove('hidden');
        controlStatus.classList.remove('success');
        controlStatus.classList.add('warning');
        controlStatusText.textContent = '控制已被主持人暂停';
        remoteControlManager.disableGuestControl();
    });

    socket.on('control-resumed', (data) => {
        isControlSuspended = false;
        currentPermissionLevel = data.level;
        controlStatus.classList.remove('hidden');
        controlStatus.classList.remove('warning');
        controlStatus.classList.add('success');
        const levelText = data.level === 'control' ? '完全控制' : '仅鼠标控制';
        controlStatusText.textContent = `控制已恢复 (${levelText})`;
        remoteControlManager.enableGuestControl();
    });

    socket.on('control-released', () => {
        currentPermissionLevel = 'view';
        isControlSuspended = false;
        updatePermissionDisplay();
        controlActive.classList.add('hidden');
        controlSuspended.classList.add('hidden');
        controlRequest.classList.add('hidden');
    });

    socket.on('control-disabled', () => {
        currentPermissionLevel = 'view';
        isControlSuspended = false;
        updatePermissionDisplay();
        
        controlStatus.classList.remove('hidden');
        controlStatus.classList.remove('success');
        controlStatus.classList.add('warning');
        controlStatusText.textContent = '控制权限已被收回';
        requestControlBtn.classList.remove('hidden');
        releaseControlBtn.classList.add('hidden');
        remoteControlManager.disableGuestControl();
        
        setTimeout(() => {
            controlStatus.classList.add('hidden');
        }, 3000);
    });

    socket.on('mouse-event', (event) => {
        if (currentRole === 'host') {
            remoteControlManager.handleHostMouseEvent(event);
        }
    });

    socket.on('keyboard-event', (event) => {
        if (currentRole === 'host') {
            remoteControlManager.handleHostKeyboardEvent(event);
        }
    });
}

function updatePermissionDisplay() {
    const levelText = {
        'view': '仅查看',
        'mouse': '仅鼠标控制',
        'control': '完全控制'
    }[currentPermissionLevel] || '仅查看';
    
    if (currentRole === 'host') {
        currentPermissionEl.textContent = levelText;
        if (currentPermissionLevel !== 'view') {
            controlActive.classList.remove('hidden');
            permissionLevelBadge.textContent = levelText;
            permissionLevelBadge.className = 'permission-badge ' + 
                (currentPermissionLevel === 'control' ? 'success' : 'info');
        } else {
            controlActive.classList.add('hidden');
        }
    } else {
        guestPermissionEl.textContent = levelText;
        guestPermissionEl.className = 'permission-badge ' + 
            (currentPermissionLevel === 'view' ? '' : 
             currentPermissionLevel === 'control' ? 'success' : 'info');
    }
}

async function startScreenShare() {
    try {
        const stream = await webrtcManager.startScreenShare();
        localVideo.srcObject = stream;
        startShareBtn.classList.add('hidden');
        stopShareBtn.classList.remove('hidden');
        
        const videoTrack = stream.getVideoTracks()[0];
        if (videoTrack) {
            const settings = videoTrack.getSettings();
            remoteControlManager.setHostScreenResolution(settings.width, settings.height);
            console.log('Host screen resolution:', settings.width, 'x', settings.height);
        }
        
        webrtcManager.onRemoteStream = (stream) => {
            remoteVideo.srcObject = stream;
        };
        
        if (webrtcManager.targetId) {
            webrtcManager.createOffer();
        }
    } catch (error) {
        console.error('Failed to start screen share:', error);
        alert('无法开始屏幕共享，请确保已授权屏幕录制权限');
    }
}

function stopScreenShare() {
    if (webrtcManager) {
        webrtcManager.stopScreenShare();
    }
    if (currentPermissionLevel !== 'view') {
        socket.emit('disable-control', currentRoomId);
    }
    localVideo.srcObject = null;
    startShareBtn.classList.remove('hidden');
    stopShareBtn.classList.add('hidden');
    controlActive.classList.add('hidden');
    controlRequest.classList.add('hidden');
    controlSuspended.classList.add('hidden');
    currentPermissionLevel = 'view';
    updatePermissionDisplay();
}

function requestControl() {
    socket.emit('request-control', currentRoomId, 'control', (response) => {
        if (response.success) {
            controlStatus.classList.remove('hidden');
            controlStatus.classList.remove('success', 'warning');
            controlStatusText.textContent = '正在等待主持人批准...';
        } else {
            alert(response.error || '发送请求失败');
        }
    });
}

function releaseControl() {
    socket.emit('release-control', currentRoomId, () => {
        remoteControlManager.disableGuestControl();
        controlStatus.classList.add('hidden');
        requestControlBtn.classList.remove('hidden');
        releaseControlBtn.classList.add('hidden');
        currentPermissionLevel = 'view';
        updatePermissionDisplay();
    });
}

function handleControlApproval(approved) {
    controlRequest.classList.add('hidden');
    const selectedLevel = document.querySelector('input[name="permission-level"]:checked')?.value || 'control';
    socket.emit('approve-control', currentRoomId, approved, selectedLevel, (response) => {
        if (approved && response.success) {
            currentPermissionLevel = response.level;
            isControlSuspended = false;
            updatePermissionDisplay();
        }
    });
}

function suspendControl() {
    socket.emit('suspend-control', currentRoomId, () => {
        isControlSuspended = true;
        controlActive.classList.add('hidden');
        controlSuspended.classList.remove('hidden');
    });
}

function resumeControl() {
    socket.emit('resume-control', currentRoomId, () => {
        isControlSuspended = false;
        controlSuspended.classList.add('hidden');
        controlActive.classList.remove('hidden');
    });
}

function disableControl() {
    socket.emit('disable-control', currentRoomId);
    controlActive.classList.add('hidden');
    controlSuspended.classList.add('hidden');
    currentPermissionLevel = 'view';
    isControlSuspended = false;
    updatePermissionDisplay();
}

function copyRoomId() {
    navigator.clipboard.writeText(currentRoomId).then(() => {
        const originalText = copyRoomIdBtn.textContent;
        copyRoomIdBtn.textContent = '已复制!';
        setTimeout(() => {
            copyRoomIdBtn.textContent = originalText;
        }, 2000);
    });
}

function refreshLogs() {
    socket.emit('get-logs', currentRoomId, (response) => {
        displayLogs(response.logs);
    });
}

function displayLogs(logs) {
    if (!logs || logs.length === 0) {
        logsContainer.innerHTML = '<p class="empty-logs">暂无日志</p>';
        return;
    }
    
    logsContainer.innerHTML = logs.map(log => {
        const time = new Date(log.timestamp).toLocaleTimeString();
        let typeClass = '';
        let message = '';
        
        if (log.type === 'mouse') {
            typeClass = 'log-type-mouse';
            let posStr;
            if (log.isNormalized) {
                posStr = `(${(log.x * 100).toFixed(1)}%, ${(log.y * 100).toFixed(1)}%)`;
            } else {
                posStr = `(${log.x}, ${log.y})`;
            }
            message = `[鼠标] ${log.event} at ${posStr}` + (log.button !== undefined ? ` button: ${log.button}` : '');
        } else if (log.type === 'keyboard') {
            typeClass = 'log-type-keyboard';
            const mods = [];
            if (log.ctrlKey) mods.push('Ctrl');
            if (log.altKey) mods.push('Alt');
            if (log.shiftKey) mods.push('Shift');
            const modStr = mods.length > 0 ? mods.join('+') + '+' : '';
            message = `[键盘] ${modStr}${log.key} (${log.code})`;
        } else if (log.type.startsWith('control-')) {
            typeClass = 'log-type-control';
            const actionText = {
                'control-approved': '批准控制',
                'control-rejected': '拒绝控制',
                'control-suspended': '暂停控制',
                'control-resumed': '恢复控制',
                'control-released': '释放控制',
                'control-disabled': '收回控制',
                'control-enabled': '启用控制'
            }[log.type] || log.type;
            const levelText = log.level ? ` (${log.level === 'control' ? '完全控制' : log.level === 'mouse' ? '仅鼠标' : '查看'})` : '';
            message = `[控制] ${actionText}${levelText} by ${log.by}`;
        } else {
            message = `[${log.type}] ${log.socketId || ''}`;
        }
        
        return `<div class="log-entry">
            <span class="log-time">${time}</span>
            <span class="${typeClass}">${message}</span>
        </div>`;
    }).join('');
    
    logsContainer.scrollTop = logsContainer.scrollHeight;
}

function leaveRoom() {
    if (webrtcManager) {
        webrtcManager.close();
    }
    if (remoteControlManager) {
        remoteControlManager.close();
    }
    
    currentRoomId = null;
    currentRole = null;
    webrtcManager = null;
    remoteControlManager = null;
    currentPermissionLevel = 'view';
    isControlSuspended = false;
    
    localVideo.srcObject = null;
    remoteVideo.srcObject = null;
    
    authSection.classList.remove('hidden');
    roomSection.classList.add('hidden');
    hostView.classList.add('hidden');
    guestView.classList.add('hidden');
    guestStatus.classList.add('hidden');
    permissionPanel.classList.add('hidden');
    controlRequest.classList.add('hidden');
    controlActive.classList.add('hidden');
    controlSuspended.classList.add('hidden');
    controlStatus.classList.add('hidden');
    startShareBtn.classList.remove('hidden');
    stopShareBtn.classList.add('hidden');
    requestControlBtn.classList.remove('hidden');
    releaseControlBtn.classList.add('hidden');
    roomIdInput.value = '';
    
    socket.disconnect();
    socket.connect();
}

setInterval(() => {
    if (currentRoomId) {
        refreshLogs();
    }
}, 2000);
