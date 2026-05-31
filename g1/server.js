const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const path = require('path');
const fs = require('fs');

const app = express();
const server = http.createServer(app);
const io = new Server(server, {
  cors: {
    origin: '*',
    methods: ['GET', 'POST']
  }
});

app.use(express.static(path.join(__dirname, 'public')));

const rooms = new Map();
const controlLogs = new Map();

function generateRoomId() {
  return Math.random().toString(36).substring(2, 8).toUpperCase();
}

function logControlEvent(roomId, event) {
  if (!controlLogs.has(roomId)) {
    controlLogs.set(roomId, []);
  }
  const logs = controlLogs.get(roomId);
  logs.push({
    ...event,
    timestamp: new Date().toISOString()
  });
  
  const logDir = path.join(__dirname, 'logs');
  if (!fs.existsSync(logDir)) {
    fs.mkdirSync(logDir, { recursive: true });
  }
  const logFile = path.join(logDir, `control-${roomId}.log`);
  fs.appendFileSync(logFile, JSON.stringify({ ...event, timestamp: new Date().toISOString() }) + '\n');
}

io.on('connection', (socket) => {
  console.log('Client connected:', socket.id);

  socket.on('create-room', (callback) => {
    const roomId = generateRoomId();
    rooms.set(roomId, {
      host: socket.id,
      guest: null,
      permission: {
        level: 'view',
        status: 'idle',
        requestedLevel: null,
        requestedAt: null,
        approvedAt: null,
        suspended: false
      }
    });
    socket.join(roomId);
    console.log('Room created:', roomId, 'by host:', socket.id);
    callback({ success: true, roomId });
  });

  socket.on('join-room', (roomId, callback) => {
    const room = rooms.get(roomId);
    if (!room) {
      callback({ success: false, error: '房间不存在' });
      return;
    }
    if (room.guest) {
      callback({ success: false, error: '房间已满' });
      return;
    }
    room.guest = socket.id;
    socket.join(roomId);
    console.log('Guest joined room:', roomId, 'socket:', socket.id);
    
    io.to(room.host).emit('guest-joined', { guestId: socket.id });
    callback({ success: true, roomId });
  });

  socket.on('offer', (data) => {
    const { roomId, offer } = data;
    const room = rooms.get(roomId);
    if (room && room.guest) {
      io.to(room.guest).emit('offer', { offer, hostId: room.host });
    }
  });

  socket.on('answer', (data) => {
    const { roomId, answer } = data;
    const room = rooms.get(roomId);
    if (room) {
      io.to(room.host).emit('answer', { answer, guestId: room.guest });
    }
  });

  socket.on('ice-candidate', (data) => {
    const { roomId, candidate, target } = data;
    socket.to(target).emit('ice-candidate', { candidate });
  });

  socket.on('request-control', (roomId, requestedLevel, callback) => {
    const room = rooms.get(roomId);
    if (!room) {
      callback({ success: false, error: '房间不存在' });
      return;
    }
    if (room.permission.status === 'requested') {
      callback({ success: false, error: '已有待处理的控制请求' });
      return;
    }
    room.permission.status = 'requested';
    room.permission.requestedLevel = requestedLevel || 'control';
    room.permission.requestedAt = new Date().toISOString();
    io.to(room.host).emit('control-requested', { 
      guestId: socket.id, 
      requestedLevel: room.permission.requestedLevel 
    });
    callback({ success: true, message: '已发送控制请求' });
  });

  socket.on('cancel-control-request', (roomId, callback) => {
    const room = rooms.get(roomId);
    if (!room) {
      callback({ success: false, error: '房间不存在' });
      return;
    }
    if (room.permission.status === 'requested') {
      room.permission.status = 'idle';
      room.permission.requestedLevel = null;
      room.permission.requestedAt = null;
      io.to(room.host).emit('control-request-cancelled');
    }
    callback({ success: true });
  });

  socket.on('approve-control', (roomId, approved, permissionLevel, callback) => {
    const room = rooms.get(roomId);
    if (!room) {
      callback({ success: false, error: '房间不存在' });
      return;
    }
    room.permission.status = approved ? 'approved' : 'rejected';
    room.permission.requestedLevel = null;
    room.permission.requestedAt = null;
    room.permission.suspended = false;
    
    if (approved) {
      room.permission.level = permissionLevel || 'control';
      room.permission.approvedAt = new Date().toISOString();
    }
    
    if (room.guest) {
      io.to(room.guest).emit('control-approved', { 
        approved, 
        level: room.permission.level 
      });
    }
    
    logControlEvent(roomId, {
      type: approved ? 'control-approved' : 'control-rejected',
      level: room.permission.level,
      by: 'host',
      socketId: socket.id
    });
    
    callback({ success: true, approved, level: room.permission.level });
  });

  socket.on('suspend-control', (roomId, callback) => {
    const room = rooms.get(roomId);
    if (!room) {
      callback({ success: false, error: '房间不存在' });
      return;
    }
    room.permission.suspended = true;
    if (room.guest) {
      io.to(room.guest).emit('control-suspended');
    }
    logControlEvent(roomId, {
      type: 'control-suspended',
      by: 'host',
      socketId: socket.id
    });
    callback({ success: true });
  });

  socket.on('resume-control', (roomId, callback) => {
    const room = rooms.get(roomId);
    if (!room) {
      callback({ success: false, error: '房间不存在' });
      return;
    }
    room.permission.suspended = false;
    if (room.guest) {
      io.to(room.guest).emit('control-resumed', { level: room.permission.level });
    }
    logControlEvent(roomId, {
      type: 'control-resumed',
      level: room.permission.level,
      by: 'host',
      socketId: socket.id
    });
    callback({ success: true });
  });

  socket.on('release-control', (roomId, callback) => {
    const room = rooms.get(roomId);
    if (!room) {
      callback({ success: false, error: '房间不存在' });
      return;
    }
    room.permission.level = 'view';
    room.permission.status = 'idle';
    room.permission.suspended = false;
    room.permission.approvedAt = null;
    
    if (room.host) {
      io.to(room.host).emit('control-released');
    }
    
    logControlEvent(roomId, {
      type: 'control-released',
      by: 'guest',
      socketId: socket.id
    });
    callback({ success: true });
  });

  socket.on('mouse-event', (data) => {
    const { roomId, event } = data;
    const room = rooms.get(roomId);
    if (room && room.host && 
        room.permission.status === 'approved' && 
        !room.permission.suspended &&
        (room.permission.level === 'control' || room.permission.level === 'mouse')) {
      io.to(room.host).emit('mouse-event', event);
      logControlEvent(roomId, {
        type: 'mouse',
        event: event.type,
        x: event.x,
        y: event.y,
        button: event.button,
        isNormalized: event.isNormalized,
        permissionLevel: room.permission.level,
        by: 'guest'
      });
    }
  });

  socket.on('keyboard-event', (data) => {
    const { roomId, event } = data;
    const room = rooms.get(roomId);
    if (room && room.host && 
        room.permission.status === 'approved' && 
        !room.permission.suspended &&
        room.permission.level === 'control') {
      io.to(room.host).emit('keyboard-event', event);
      logControlEvent(roomId, {
        type: 'keyboard',
        key: event.key,
        code: event.code,
        ctrlKey: event.ctrlKey,
        altKey: event.altKey,
        shiftKey: event.shiftKey,
        permissionLevel: room.permission.level,
        by: 'guest'
      });
    }
  });

  socket.on('disable-control', (roomId) => {
    const room = rooms.get(roomId);
    if (room) {
      room.permission.level = 'view';
      room.permission.status = 'idle';
      room.permission.suspended = false;
      room.permission.approvedAt = null;
      if (room.guest) {
        io.to(room.guest).emit('control-disabled');
      }
      logControlEvent(roomId, {
        type: 'control-disabled',
        by: 'host',
        socketId: socket.id
      });
    }
  });

  socket.on('get-logs', (roomId, callback) => {
    const logs = controlLogs.get(roomId) || [];
    callback({ logs });
  });

  socket.on('disconnect', () => {
    console.log('Client disconnected:', socket.id);
    rooms.forEach((room, roomId) => {
      if (room.host === socket.id) {
        if (room.guest) {
          io.to(room.guest).emit('host-left');
        }
        rooms.delete(roomId);
        console.log('Room deleted:', roomId);
      } else if (room.guest === socket.id) {
        room.guest = null;
        room.permission.level = 'view';
        room.permission.status = 'idle';
        room.permission.suspended = false;
        io.to(room.host).emit('guest-left');
        logControlEvent(roomId, {
          type: 'guest-left',
          socketId: socket.id
        });
      }
    });
  });
});

const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});
