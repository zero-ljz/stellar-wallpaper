# 星澜壁纸 (Stellar Wallpaper) Windows 桌面客户端

基于 Fluent 2 视觉语言构建的高颜值、轻量级、去中心化 Windows 桌面超高清壁纸管理与自动轮播客户端。

[![GitHub Repository](https://img.shields.io/badge/GitHub-stellar--wallpaper-blue?logo=github)](https://github.com/zero-ljz/stellar-wallpaper)
[![Release](https://img.shields.io/badge/version-v1.1.0-brightgreen.svg)](https://github.com/zero-ljz/stellar-wallpaper/releases)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![GUI](https://img.shields.io/badge/GUI-PySide6%206.8.3-green.svg)](https://wiki.qt.io/Qt_for_Python)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-0078D4.svg)](https://microsoft.com/windows)

---

## ✨ 特性亮点

1. **🎨 现代 Windows 11 Fluent 2 视觉体验**
   - 无边框圆角窗体、自定义沉浸式标题栏（置顶、最小化、最大化、关闭、拖拽支持）。
   - 采用 Windows 11 Fluent Light 清爽明亮配色与 MiSans 清晰高品质字库。
   - 可折叠侧边导航栏（`NavigationView`）。

2. **🗂️ 18 大精选主题与多元图源全量支持**
   - **必应历年历史大图库 (`bing`)**：收录 869+ 张历年官方 4K 超清历史精选壁纸，每日自动同步追加，配有地名背景故事与日期。
   - **Lorem Picsum 艺术摄影库 (`picsum`)**：993 张全球精选艺术摄影大片，支持 **正序 / 倒序 / 随机洗牌** 3 种排序模式自由切换。
   - **360 官方 15 大精选分类**：`4K专区 (36)`、`风景大片 (9)`、`动漫卡通 (26)`、`游戏壁纸 (5)`、`汽车天下 (12)`、`萌宠动物 (14)`、`美女模特 (6)`、`炫酷时尚 (10)`、`小清新 (15)`、`影视剧照 (7)`、`爱情美图 (30)`、`明星风尚 (11)`、`军事天地 (22)`、`劲爆体育 (16)`、`文字控 (35)`。
   - 直连高分辨率官方图库与 CDN 极速下载。

3. **🔀 多分类混合随机切换与智能去重**
   - 自由勾选任意多个分类池（如同时勾选【必应壁纸】+【Picsum 图库】+【4K专区】+【动漫卡通】）。
   - **智能去重机制**：内存追踪 + SQLite 历史数据库双重比对过滤，杜绝重复随机。
   - 更换全流程进度条与分步状态提示（连接中 -> 下载原图 % -> 应用 Windows 壁纸 -> 完成提示）。

4. **⏰ 定时自动轮播 (Auto Scheduler)**
   - 支持多档位轮播间隔（1分钟测试、5分钟、15分钟、30分钟、1小时、2小时、6小时、12小时、1天或自定义分钟）。
   - 动态倒计时面板（时:分:秒 实时倒计时 + 进度动画）。
   - 轮播源支持从【多选分类池】或【我的收藏】中轮播。

5. **🖥️ Windows 10 & 11 原生壁纸设置**
   - Win32 API (`SystemParametersInfoW`) 与注册表深度结合。
   - 支持 6 种呈现样式：**填充 (Fill)**、**适应 (Fit)**、**拉伸 (Stretch)**、**平铺 (Tile)**、**居中 (Center)**、**跨屏 (Span)**。

6. **🔍 高清画廊与大图预览**
   - 分类画廊网格瀑布流浏览，支持关键字搜索与分页翻页。
   - 异步多线程缩略图加载与本地磁盘缓存。
   - 悬浮快捷操作（一键设为壁纸、收藏、下载保存）。
   - 超高清大图预览弹窗与详细元数据展示（分辨率、标签、专区、拍摄信息）。

7. **📁 保存壁纸一键打开所在目录**
   - 在画廊卡片或大图预览中保存壁纸成功后，弹窗支持 **「打开所在目录」**，一键唤起 Windows 资源管理器并自动高亮选中文件。

8. **❤️ 收藏夹与 📜 历史记录**
   - 本地 SQLite 数据库持久化存储收藏与历史设置记录。
   - 支持从收藏夹随机一键设为壁纸、历史记录回溯与清空。

9. **🔔 系统托盘与后台常驻**
   - 完整的系统托盘图标（`QSystemTrayIcon`）与右键菜单。
   - 托盘快捷切换下一张、暂停/恢复定时轮播、打开保存目录。
   - 壁纸更换完成桌面气泡通知与关闭时最小化到托盘。

---

## 🛠️ 环境要求

- **操作系统**: Windows 10 / Windows 11 (64-bit)
- **Python**: 3.12+
- **GUI 框架**: PySide6 6.8.3
- **现代化组件**: pyside6-modern-widgets 0.1.2

---

## 🚀 快速启动

### 1. 安装依赖

```bash
uv sync
```

### 2. 启动应用

```bash
uv run python main.py
```

### 3. 运行单元测试

```bash
uv run pytest
```

### 4. 打包单文件独立版

```bash
uv run python build.py --onefile
```

打包完成后，生成的单文件可执行程序 `StellarWallpaper.exe` 将输出在 `dist/` 目录下。

---

## 📄 开源许可

本项目遵循 MIT 开源许可证。源码地址：[https://github.com/zero-ljz/stellar-wallpaper](https://github.com/zero-ljz/stellar-wallpaper)


