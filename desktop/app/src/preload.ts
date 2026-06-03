import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("rimBridge", {
  apiBaseUrl: "http://127.0.0.1:8765",
  getApiStatus: () => ipcRenderer.invoke("api-status")
});
