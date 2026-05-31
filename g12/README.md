# 第一人称解谜游戏 (Godot 4 + GDScript)

## 游戏介绍
这是一个使用 Godot 4 引擎开发的第一人称视角解谜游戏。玩家需要按照正确顺序触发各种机关（拉杆、按钮、压力板）来打开出口门。

## 操作说明
- **WASD**: 移动
- **空格**: 跳跃
- **鼠标**: 视角控制
- **E**: 交互（拉杆、按钮）
- **ESC**: 释放鼠标

## 游戏目标
按照以下顺序触发机关：
1. 拉动左侧的拉杆
2. 按下中间的按钮
3. 将箱子推到右侧的压力板上

完成后，出口门将会打开。

## 项目结构
```
project.godot          # 项目配置文件
icon.svg               # 项目图标
export_presets.cfg     # 导出配置
scripts/               # 游戏脚本
  player.gd            # 玩家控制器
  interactable_base.gd # 可交互物体基类
  lever.gd             # 拉杆逻辑
  button.gd            # 按钮逻辑
  pressure_plate.gd    # 压力板逻辑
  pushable_box.gd      # 可推动箱子
  door.gd              # 门的开关逻辑
  puzzle_manager.gd    # 谜题管理器
  game_manager.gd      # 游戏总管理器
scenes/                # 场景文件
  player.tscn          # 玩家场景
  lever.tscn           # 拉杆场景
  button.tscn          # 按钮场景
  pressure_plate.tscn  # 压力板场景
  pushable_box.tscn    # 箱子场景
  door.tscn            # 门场景
  main.tscn            # 主场景
```

## 导出项目

### Windows 平台
1. 在 Godot 编辑器中点击 "Project" -> "Export..."
2. 选择 "Windows Desktop" 预设
3. 点击 "Export Project"
4. 选择输出目录（默认: build/windows/）

### Web 平台
1. 在 Godot 编辑器中点击 "Project" -> "Export..."
2. 选择 "Web" 预设
3. 点击 "Export Project"
4. 选择输出目录（默认: build/web/）
5. 导出后需要使用 HTTP 服务器运行 HTML 文件（不能直接双击打开）

## 技术特性
- 第一人称控制器（CharacterBody3D）
- 物理交互系统（RayCast3D 交互检测）
- 可配置的谜题顺序系统
- 物理推动的箱子（RigidBody3D）
- 动态光照和阴影
- 完整的导出配置
