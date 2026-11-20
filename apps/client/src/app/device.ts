// What the webview can tell about the device. Used only for the diagnostics on the
// About page; values the platform does not expose stay undefined (never guessed).

export interface DeviceReport {
  userAgent: string;
  model?: string;
  osVersion?: string;
  browser?: string;
  cores?: number;
  memoryGb?: number;
}

interface UAData {
  getHighEntropyValues(hints: string[]): Promise<{
    model?: string;
    platform?: string;
    platformVersion?: string;
    fullVersionList?: { brand: string; version: string }[];
  }>;
}

export async function deviceReport(): Promise<DeviceReport> {
  const nav = navigator as Navigator & { userAgentData?: UAData; deviceMemory?: number };
  const ua = nav.userAgent;
  const report: DeviceReport = {
    userAgent: ua,
    cores: nav.hardwareConcurrency || undefined,
    memoryGb: nav.deviceMemory,
  };
  // From the user agent: "Android 14; SM-A546E" and "Chrome/131.0.6778.135".
  const android = /Android ([\d.]+)(?:; ([^;)]+))?/.exec(ua);
  if (android) {
    report.osVersion = `Android ${android[1]}`;
    if (android[2] && android[2].trim() !== "K") report.model = android[2].trim();
  }
  const windows = /Windows NT ([\d.]+)/.exec(ua);
  if (windows) report.osVersion = `Windows NT ${windows[1]}`;
  const chrome = /(?:Chrome|Edg)\/([\d.]+)/.exec(ua);
  if (chrome) report.browser = `Chromium ${chrome[1]}`;
  // Newer Chromium hides the model in the user agent; ask for it explicitly.
  try {
    const high = await nav.userAgentData?.getHighEntropyValues(["model", "platformVersion", "fullVersionList"]);
    if (high?.model) report.model = high.model;
    if (high?.platform === "Android" && high.platformVersion) report.osVersion = `Android ${high.platformVersion}`;
    const webview = high?.fullVersionList?.find((b) => /WebView|Chromium|Edge/i.test(b.brand));
    if (webview) report.browser = `${webview.brand} ${webview.version}`;
  } catch {
    // Not available on this platform.
  }
  return report;
}
