# 星澜壁纸 (Stellar Wallpaper)

基于 Fluent 2 视觉语言构建的超高清桌面壁纸管理与自动轮播客户端，支持 Windows 和 macOS。

[![GitHub Repository](https://img.shields.io/badge/GitHub-stellar--wallpaper-blue?logo=github)](https://github.com/zero-ljz/stellar-wallpaper)
[![Release](https://img.shields.io/badge/version-v1.2.3-brightgreen.svg)](https://github.com/zero-ljz/stellar-wallpaper/releases)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![GUI](https://img.shields.io/badge/GUI-PySide6%206.8.3-green.svg)](https://wiki.qt.io/Qt_for_Python)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11%20%7C%20macOS%2012%2B-0078D4.svg)](#环境要求)
[![Download](https://img.shields.io/badge/download-latest%20release-0078D4.svg?logo=github)](https://github.com/zero-ljz/stellar-wallpaper/releases/latest)

---

## 📥 下载

- **Windows** 可下载单文件版 [StellarWallpaper.exe](https://github.com/zero-ljz/stellar-wallpaper/releases/latest/download/StellarWallpaper.exe)。
- **macOS** 使用同时支持 Apple Silicon 和 Intel 的 Universal 2 DMG。目前 GitHub Release 提供 Windows 版，macOS 版可按下文从源码打包。

---

## ✨ 特性亮点

1. **🎨 Fluent 2 视觉体验**
   - 无边框圆角窗体、自定义沉浸式标题栏（置顶、最小化、最大化、关闭、拖拽支持）。
   - 采用 Windows 11 Fluent Light 清爽明亮配色与 霞鹜文楷 Lite 精简版常规体（LXGW WenKai Lite Regular）高品质字库。
   - 可折叠侧边导航栏（`NavigationView`）。

2. **🗂️ 18 大精选主题与多元图源全量支持**
   - **必应历年历史大图库 (`bing`)**：收录 869+ 张历年官方 4K 超清历史精选壁纸，每日自动同步追加，配有地名背景故事与日期。
   - **Lorem Picsum 艺术摄影库 (`picsum`)**：993 张全球精选艺术摄影大片，支持 **正序 / 倒序 / 随机洗牌** 3 种排序模式自由切换。
   - **360 官方 15 大精选分类**：`4K专区 (36)`、`风景大片 (9)`、`动漫卡通 (26)`、`游戏壁纸 (5)`、`汽车天下 (12)`、`萌宠动物 (14)`、`美女模特 (6)`、`炫酷时尚 (10)`、`小清新 (15)`、`影视剧照 (7)`、`爱情美图 (30)`、`明星风尚 (11)`、`军事天地 (22)`、`劲爆体育 (16)`、`文字控 (35)`。
   - 直连高分辨率官方图库与 CDN 极速下载。

3. **🔀 多分类混合随机切换与智能去重**
   - 自由勾选任意多个分类池（如同时勾选【必应壁纸】+【Picsum 图库】+【4K专区】+【动漫卡通】）。
   - **智能去重机制**：内存追踪 + SQLite 历史数据库双重比对过滤，杜绝重复随机。
   - 更换全流程进度条与分步状态提示（连接中 → 下载原图 → 应用壁纸 → 完成提示）。

4. **⏰ 定时自动轮播 (Auto Scheduler)**
   - 支持多档位轮播间隔（1分钟测试、5分钟、15分钟、30分钟、1小时、2小时、6小时、12小时、1天或自定义分钟）。
   - 动态倒计时面板（时:分:秒 实时倒计时 + 进度动画）。
   - 轮播源支持从【多选分类池】或【我的收藏】中轮播。

5. **🖥️ 原生壁纸设置**
   - Windows 通过 Win32 API (`SystemParametersInfoW`) 更换壁纸，支持**填充、适应、拉伸、平铺、居中和跨屏**六种呈现样式。
   - macOS 通过「系统事件」更换壁纸，呈现样式由系统管理。如果 macOS 请求自动化权限，请允许星澜壁纸控制「系统事件」。

6. **🔍 高清画廊与大图预览**
   - 分类画廊网格瀑布流浏览，支持关键字搜索与分页翻页。
   - 异步多线程缩略图加载与本地磁盘缓存。
   - 悬浮快捷操作（一键设为壁纸、收藏、下载保存）。
   - 批量勾选多张壁纸并后台下载，支持跨页选择、进度显示、取消和自动跳过已有文件。
   - 超高清大图预览弹窗与详细元数据展示（分辨率、标签、专区、拍摄信息）。

7. **📁 保存壁纸一键打开所在目录**
   - 在画廊卡片或大图预览中保存壁纸成功后，点击 **「打开所在目录」**，即可在 Windows 文件资源管理器或 macOS「访达」中选中文件。

8. **❤️ 收藏夹与 📜 历史记录**
   - 本地 SQLite 数据库持久化存储收藏与历史设置记录。
   - 收藏夹支持跨页批量勾选、全选全部收藏、下载进度、取消任务和自动跳过已有文件。
   - 支持从收藏夹随机一键设为壁纸、历史记录回溯与清空。

9. **🔔 系统托盘与后台常驻**
   - 完整的系统托盘图标（`QSystemTrayIcon`）与右键菜单。
   - 托盘快捷切换下一张、暂停/恢复定时轮播、打开保存目录。
   - Windows 支持使用全局快捷键切换下一张壁纸，默认 `Ctrl+Alt+N`，可在设置中心修改。
   - 支持随 Windows 开机启动，或在登录 macOS 后自动运行。
   - 壁纸更换完成桌面气泡通知与关闭时最小化到托盘。
   - 支持单实例运行；重复启动时会自动唤醒并恢复已有窗口。

---

## 环境要求

- **Windows** 10 或 11（64 位）。
- **macOS** 12 Monterey 或更高版本，支持 Apple Silicon 和 Intel。[Qt 6.8 的 macOS 支持范围](https://doc.qt.io/qt-6.8/macos.html)
- 从源码运行或构建需要 Python 3.12 或更高版本、PySide6 6.8.3 和 pyside6-modern-widgets。

---

## 🚀 快速启动

### 1. 获取源码

```bash
git clone --branch main https://github.com/zero-ljz/stellar-wallpaper.git
cd stellar-wallpaper
```

### 2. 安装依赖

```bash
uv sync
```

### 3. 启动应用

```bash
uv run python main.py
```

### 4. 运行单元测试

```bash
uv run pytest
```

### 5. 打包 Windows 单文件版

```bash
uv run python build.py --onefile
```

打包完成后，生成的单文件可执行程序 `StellarWallpaper.exe` 将输出在 `dist/` 目录下。

打包时会从应用文案、组件库翻译和可打印 ASCII 自动生成霞鹜文楷 Lite 字体子集。壁纸标题、文件名和输入内容中超出子集的字符由 Qt 回退到系统字体。

### 6. 打包 Windows 7z 便携版

Windows 上安装 7-Zip 后可生成体积更小的 `dist/StellarWallpaper-<版本号>-windows-x64-portable.7z`。使用时先解压整个目录，再双击其中的 `StellarWallpaper.exe`。

```bash
uv run python build.py --archive
```

### 7. 打包 macOS 通用版

在 Mac 上安装 uv、Xcode 命令行工具（`xcode-select --install`）和 Universal 2 Python 3.12。[Python.org 安装包](https://www.python.org/downloads/release/python-31210/)

在项目根目录执行以下命令。

```bash
uv run --locked --python /Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 python build.py --dmg
```

产物为 `dist/StellarWallpaper-<版本号>-macos-universal.dmg`，同时支持 Apple Silicon 和 Intel。打开镜像，把 `StellarWallpaper.app` 拖到「应用程序」即可安装。

应用使用 PyInstaller 的 ad hoc 签名。从网上下载未经 Apple 公证的副本时，Gatekeeper 可能会拦截首次打开。面向公众发布时，可使用 Developer ID 签名并提交 Apple 公证。

---

## 📄 开源许可

本项目遵循 MIT 开源许可证。源码地址：[https://github.com/zero-ljz/stellar-wallpaper](https://github.com/zero-ljz/stellar-wallpaper)

霞鹜文楷 Lite 及其字体子集采用 [SIL Open Font License 1.1](app/resources/fonts/OFL-LXGWWenKaiLite.txt)。
