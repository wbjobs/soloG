class WebRTCManager {
    constructor(socket, roomId) {
        this.socket = socket;
        this.roomId = roomId;
        this.peerConnection = null;
        this.localStream = null;
        this.remoteStream = null;
        this.isHost = false;
        this.targetId = null;
        this.onRemoteStream = null;
        this.onConnectionStateChange = null;

        this.iceServers = {
            iceServers: [
                { urls: 'stun:stun.l.google.com:19302' },
                { urls: 'stun:stun1.l.google.com:19302' },
                { urls: 'stun:stun2.l.google.com:19302' }
            ]
        };
    }

    setIsHost(isHost) {
        this.isHost = isHost;
    }

    setTargetId(targetId) {
        this.targetId = targetId;
    }

    async startScreenShare() {
        try {
            this.localStream = await navigator.mediaDevices.getDisplayMedia({
                video: {
                    cursor: 'always'
                },
                audio: false
            });

            this.localStream.getVideoTracks()[0].addEventListener('ended', () => {
                this.stopScreenShare();
            });

            return this.localStream;
        } catch (error) {
            console.error('Screen share error:', error);
            throw error;
        }
    }

    stopScreenShare() {
        if (this.localStream) {
            this.localStream.getTracks().forEach(track => track.stop());
            this.localStream = null;
        }
        if (this.peerConnection) {
            this.peerConnection.close();
            this.peerConnection = null;
        }
    }

    createPeerConnection() {
        this.peerConnection = new RTCPeerConnection(this.iceServers);

        if (this.localStream) {
            this.localStream.getTracks().forEach(track => {
                this.peerConnection.addTrack(track, this.localStream);
            });
        }

        this.peerConnection.onicecandidate = (event) => {
            if (event.candidate) {
                this.socket.emit('ice-candidate', {
                    roomId: this.roomId,
                    candidate: event.candidate,
                    target: this.targetId
                });
            }
        };

        this.peerConnection.ontrack = (event) => {
            this.remoteStream = event.streams[0];
            if (this.onRemoteStream) {
                this.onRemoteStream(this.remoteStream);
            }
        };

        this.peerConnection.onconnectionstatechange = () => {
            if (this.onConnectionStateChange) {
                this.onConnectionStateChange(this.peerConnection.connectionState);
            }
        };

        return this.peerConnection;
    }

    async createOffer() {
        if (!this.peerConnection) {
            this.createPeerConnection();
        }

        try {
            const offer = await this.peerConnection.createOffer();
            await this.peerConnection.setLocalDescription(offer);
            this.socket.emit('offer', {
                roomId: this.roomId,
                offer: offer
            });
            return offer;
        } catch (error) {
            console.error('Create offer error:', error);
            throw error;
        }
    }

    async handleOffer(offer, hostId) {
        this.targetId = hostId;
        if (!this.peerConnection) {
            this.createPeerConnection();
        }

        try {
            await this.peerConnection.setRemoteDescription(new RTCSessionDescription(offer));
            const answer = await this.peerConnection.createAnswer();
            await this.peerConnection.setLocalDescription(answer);
            this.socket.emit('answer', {
                roomId: this.roomId,
                answer: answer
            });
            return answer;
        } catch (error) {
            console.error('Handle offer error:', error);
            throw error;
        }
    }

    async handleAnswer(answer) {
        try {
            await this.peerConnection.setRemoteDescription(new RTCSessionDescription(answer));
        } catch (error) {
            console.error('Handle answer error:', error);
            throw error;
        }
    }

    async handleIceCandidate(candidate) {
        try {
            await this.peerConnection.addIceCandidate(new RTCIceCandidate(candidate));
        } catch (error) {
            console.error('Handle ICE candidate error:', error);
        }
    }

    close() {
        this.stopScreenShare();
        if (this.peerConnection) {
            this.peerConnection.close();
            this.peerConnection = null;
        }
    }
}
