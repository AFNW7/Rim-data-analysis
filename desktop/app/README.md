# Rim 数据分析 Electron 桌面端

这是当前正式的桌面 UI 入口。用户不需要打开浏览器页面，也不需要访问 `127.0.0.1:8765`。

## 开发运行

在项目根目录执行：

```powershell
python -m pip install -e .[dev]

cd desktop\app
npm install
npm start
```

`npm start` 会构建前端并启动 Electron 窗口。Electron 主进程会自动尝试启动 Python 本地 API，渲染层通过该 API 调用现有 Python 计算逻辑。

## Windows 打包

不要直接在本目录手动拼接发布包。推荐从项目根目录执行统一脚本：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-windows-release.ps1 -Version 1.0.0
```

该脚本会先用 PyInstaller 构建 `rim-analysis-web-api.exe`，再用 Electron Builder 生成 `win-unpacked` 目录，并压缩为：

```text
desktop\app\release\RimDataAnalysis-v1.0.0-windows-x64.zip
```

## 当前接入状态

- 已接入人物创建、场景设计、结果对比、数据导入、资源管理五个页面。
- 桌面端通过本地 JSON API 调用 Python 计算与存储逻辑。
- 打包版内置本地 API 后端 exe，普通用户无需安装 Python。
