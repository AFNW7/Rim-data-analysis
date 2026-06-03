import { app, BrowserWindow, Menu, ipcMain } from "electron";
import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const appRoot = path.resolve(__dirname, "..", "..");
const repoRoot = path.resolve(appRoot, "..", "..");
const apiPort = 8765;
let apiProcess: ChildProcessWithoutNullStreams | null = null;
let apiStatus = "starting";

function resolvePythonExecutable(): string {
  if (process.env.RIM_ANALYSIS_PYTHON) {
    return process.env.RIM_ANALYSIS_PYTHON;
  }
  const venvPython = path.join(repoRoot, ".venv", "Scripts", "python.exe");
  if (existsSync(venvPython)) {
    return venvPython;
  }
  return "python";
}

function resolvePackagedBackendExecutable(): string | null {
  if (!app.isPackaged) {
    return null;
  }
  const backendExecutable = path.join(
    process.resourcesPath,
    "backend",
    "rim-analysis-web-api.exe"
  );
  return existsSync(backendExecutable) ? backendExecutable : null;
}

function startPythonApi(): void {
  const packagedBackend = resolvePackagedBackendExecutable();
  if (app.isPackaged && packagedBackend === null) {
    apiStatus = "error: packaged backend executable not found";
    return;
  }

  const command = packagedBackend ?? resolvePythonExecutable();
  const pythonPath = path.join(repoRoot, "src");
  apiProcess = spawn(
    command,
    packagedBackend
      ? ["--host", "127.0.0.1", "--port", String(apiPort)]
      : [
          "-m",
          "rim_data_analysis",
          "web-api",
          "--host",
          "127.0.0.1",
          "--port",
          String(apiPort)
        ],
    {
      cwd: packagedBackend ? app.getPath("userData") : repoRoot,
      env: packagedBackend
        ? { ...process.env, PYTHONUNBUFFERED: "1" }
        : {
            ...process.env,
            PYTHONUNBUFFERED: "1",
            PYTHONPATH: process.env.PYTHONPATH
              ? `${pythonPath}${path.delimiter}${process.env.PYTHONPATH}`
              : pythonPath
          },
      windowsHide: true
    }
  );

  apiProcess.on("spawn", () => {
    apiStatus = "running";
  });
  apiProcess.stdout.on("data", () => {
    apiStatus = "running";
  });
  apiProcess.stderr.on("data", (chunk) => {
    const message = String(chunk);
    apiStatus = message.includes("Address already in use") ? "already-running" : "error";
  });
  apiProcess.on("error", (error) => {
    apiStatus = `error: ${error.message}`;
  });
  apiProcess.on("exit", () => {
    apiStatus = "stopped";
    apiProcess = null;
  });
}

function createWindow(): void {
  const preload = path.join(__dirname, "preload.js");
  const window = new BrowserWindow({
    width: 430,
    height: 780,
    minWidth: 360,
    minHeight: 360,
    title: "Rim 数据分析",
    backgroundColor: "#12171a",
    webPreferences: {
      preload,
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  window.setTitle("Rim 数据分析");
  window.loadFile(path.join(appRoot, "dist", "renderer", "index.html"));
}

app.whenReady().then(() => {
  Menu.setApplicationMenu(null);
  startPythonApi();
  ipcMain.handle("api-status", () => apiStatus);
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("before-quit", () => {
  apiProcess?.kill();
});
