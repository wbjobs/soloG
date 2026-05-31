class RemoteControlManager {
    constructor(socket, roomId) {
        this.socket = socket;
        this.roomId = roomId;
        this.controlEnabled = false;
        this.controlOverlay = null;
        this.videoElement = null;
        this.onMouseEvent = null;
        this.onKeyboardEvent = null;
        this.hostScreenWidth = 0;
        this.hostScreenHeight = 0;
    }

    setHostScreenResolution(width, height) {
        this.hostScreenWidth = width;
        this.hostScreenHeight = height;
    }

    setControlOverlay(overlay) {
        this.controlOverlay = overlay;
    }

    setVideoElement(video) {
        this.videoElement = video;
    }

    enableGuestControl() {
        this.controlEnabled = true;
        if (this.controlOverlay) {
            this.controlOverlay.classList.remove('hidden');
            this.attachGuestListeners();
        }
        document.addEventListener('keydown', this.handleGuestKeydown.bind(this));
        document.addEventListener('keyup', this.handleGuestKeyup.bind(this));
    }

    disableGuestControl() {
        this.controlEnabled = false;
        if (this.controlOverlay) {
            this.controlOverlay.classList.add('hidden');
            this.detachGuestListeners();
        }
        document.removeEventListener('keydown', this.handleGuestKeydown.bind(this));
        document.removeEventListener('keyup', this.handleGuestKeyup.bind(this));
    }

    attachGuestListeners() {
        if (!this.controlOverlay) return;
        
        this.controlOverlay.addEventListener('mousemove', this.handleGuestMouseMove.bind(this));
        this.controlOverlay.addEventListener('mousedown', this.handleGuestMouseDown.bind(this));
        this.controlOverlay.addEventListener('mouseup', this.handleGuestMouseUp.bind(this));
        this.controlOverlay.addEventListener('click', this.handleGuestClick.bind(this));
        this.controlOverlay.addEventListener('dblclick', this.handleGuestDblClick.bind(this));
        this.controlOverlay.addEventListener('contextmenu', this.handleGuestContextMenu.bind(this));
        this.controlOverlay.addEventListener('wheel', this.handleGuestWheel.bind(this));
    }

    detachGuestListeners() {
        if (!this.controlOverlay) return;
        
        this.controlOverlay.removeEventListener('mousemove', this.handleGuestMouseMove.bind(this));
        this.controlOverlay.removeEventListener('mousedown', this.handleGuestMouseDown.bind(this));
        this.controlOverlay.removeEventListener('mouseup', this.handleGuestMouseUp.bind(this));
        this.controlOverlay.removeEventListener('click', this.handleGuestClick.bind(this));
        this.controlOverlay.removeEventListener('dblclick', this.handleGuestDblClick.bind(this));
        this.controlOverlay.removeEventListener('contextmenu', this.handleGuestContextMenu.bind(this));
        this.controlOverlay.removeEventListener('wheel', this.handleGuestWheel.bind(this));
    }

    getRelativePosition(e) {
        if (!this.controlOverlay || !this.videoElement) return { x: 0, y: 0 };
        
        const overlayRect = this.controlOverlay.getBoundingClientRect();
        const videoWidth = this.videoElement.videoWidth;
        const videoHeight = this.videoElement.videoHeight;
        
        if (!videoWidth || !videoHeight) {
            return { x: 0, y: 0 };
        }
        
        const videoRect = this.videoElement.getBoundingClientRect();
        const containerRatio = videoRect.width / videoRect.height;
        const videoRatio = videoWidth / videoHeight;
        
        let renderWidth, renderHeight, offsetX, offsetY;
        
        if (containerRatio > videoRatio) {
            renderHeight = videoRect.height;
            renderWidth = renderHeight * videoRatio;
            offsetX = (videoRect.width - renderWidth) / 2;
            offsetY = 0;
        } else {
            renderWidth = videoRect.width;
            renderHeight = renderWidth / videoRatio;
            offsetX = 0;
            offsetY = (videoRect.height - renderHeight) / 2;
        }
        
        const clickX = e.clientX - videoRect.left - offsetX;
        const clickY = e.clientY - videoRect.top - offsetY;
        
        if (clickX < 0 || clickX > renderWidth || clickY < 0 || clickY > renderHeight) {
            return null;
        }
        
        const normX = clickX / renderWidth;
        const normY = clickY / renderHeight;
        
        return {
            x: normX,
            y: normY,
            isNormalized: true
        };
    }

    sendMouseEvent(type, e) {
        if (!this.controlEnabled) return;
        
        const pos = this.getRelativePosition(e);
        if (!pos) return;
        
        const event = {
            type: type,
            x: pos.x,
            y: pos.y,
            button: e.button,
            buttons: e.buttons,
            movementX: e.movementX,
            movementY: e.movementY,
            isNormalized: true
        };
        
        this.socket.emit('mouse-event', {
            roomId: this.roomId,
            event: event
        });
    }

    handleGuestMouseMove(e) {
        e.preventDefault();
        this.sendMouseEvent('mousemove', e);
    }

    handleGuestMouseDown(e) {
        e.preventDefault();
        this.sendMouseEvent('mousedown', e);
    }

    handleGuestMouseUp(e) {
        e.preventDefault();
        this.sendMouseEvent('mouseup', e);
    }

    handleGuestClick(e) {
        e.preventDefault();
        this.sendMouseEvent('click', e);
    }

    handleGuestDblClick(e) {
        e.preventDefault();
        this.sendMouseEvent('dblclick', e);
    }

    handleGuestContextMenu(e) {
        e.preventDefault();
        this.sendMouseEvent('contextmenu', e);
    }

    handleGuestWheel(e) {
        if (!this.controlEnabled) return;
        e.preventDefault();
        
        const event = {
            type: 'wheel',
            deltaX: e.deltaX,
            deltaY: e.deltaY,
            deltaZ: e.deltaZ,
            deltaMode: e.deltaMode
        };
        
        this.socket.emit('mouse-event', {
            roomId: this.roomId,
            event: event
        });
    }

    sendKeyboardEvent(type, e) {
        if (!this.controlEnabled) return;
        
        const event = {
            type: type,
            key: e.key,
            code: e.code,
            keyCode: e.keyCode,
            ctrlKey: e.ctrlKey,
            altKey: e.altKey,
            shiftKey: e.shiftKey,
            metaKey: e.metaKey,
            repeat: e.repeat
        };
        
        this.socket.emit('keyboard-event', {
            roomId: this.roomId,
            event: event
        });
    }

    handleGuestKeydown(e) {
        if (!this.controlEnabled) return;
        if (['F5', 'F12'].includes(e.key)) return;
        e.preventDefault();
        this.sendKeyboardEvent('keydown', e);
    }

    handleGuestKeyup(e) {
        if (!this.controlEnabled) return;
        e.preventDefault();
        this.sendKeyboardEvent('keyup', e);
    }

    handleHostMouseEvent(event) {
        let processedEvent = { ...event };
        
        if (event.isNormalized && this.hostScreenWidth > 0 && this.hostScreenHeight > 0) {
            processedEvent.x = Math.round(event.x * this.hostScreenWidth);
            processedEvent.y = Math.round(event.y * this.hostScreenHeight);
            processedEvent.normalizedX = event.x;
            processedEvent.normalizedY = event.y;
        }
        
        if (this.onMouseEvent) {
            this.onMouseEvent(processedEvent);
        }
        console.log('Host received mouse event:', processedEvent);
    }

    handleHostKeyboardEvent(event) {
        if (this.onKeyboardEvent) {
            this.onKeyboardEvent(event);
        }
        console.log('Host received keyboard event:', event);
    }

    close() {
        this.disableGuestControl();
        this.controlEnabled = false;
    }
}
