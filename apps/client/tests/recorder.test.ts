import { afterEach, describe, expect, it, vi } from "vitest";
import { isSpeed, speeds } from "../src/pronunciation/player";
import { RecorderError, reasonOf, recordingSupported, startRecording } from "../src/pronunciation/recorder";

class FakeRecorder extends EventTarget {
  static isTypeSupported = (t: string) => t === "audio/webm;codecs=opus";
  static last: FakeRecorder | null = null;
  state: "inactive" | "recording" = "inactive";
  constructor(readonly stream: unknown, readonly options?: { mimeType?: string }) {
    super();
    FakeRecorder.last = this;
  }
  get mimeType() {
    return this.options?.mimeType ?? "";
  }
  start() {
    this.state = "recording";
  }
  stop(bytes = 3) {
    this.state = "inactive";
    const data = new Blob([new Uint8Array(bytes)]);
    this.dispatchEvent(Object.assign(new Event("dataavailable"), { data }));
    this.dispatchEvent(new Event("stop"));
  }
}

function stubMedia(getUserMedia: () => Promise<unknown>) {
  const stopped = { count: 0 };
  vi.stubGlobal("MediaRecorder", FakeRecorder);
  vi.stubGlobal("navigator", { mediaDevices: { getUserMedia } });
  return stopped;
}

function fakeStream(stopped: { count: number }) {
  return { getTracks: () => [{ stop: () => stopped.count++ }] };
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("own-voice recorder", () => {
  it("knows when the device cannot record", async () => {
    vi.stubGlobal("navigator", {});
    expect(recordingSupported()).toBe(false);
    await expect(startRecording()).rejects.toMatchObject({ reason: "unsupported" });
  });

  it("maps microphone errors to what the learner can fix", () => {
    expect(reasonOf({ name: "NotAllowedError" })).toBe("denied");
    expect(reasonOf({ name: "SecurityError" })).toBe("denied");
    expect(reasonOf({ name: "NotFoundError" })).toBe("no_mic");
    expect(reasonOf({ name: "NotReadableError" })).toBe("busy");
    expect(reasonOf(new RecorderError("empty"))).toBe("empty");
    expect(reasonOf(new Error("x"))).toBe("failed");
  });

  it("reports a denied microphone", async () => {
    stubMedia(() => Promise.reject(Object.assign(new Error("no"), { name: "NotAllowedError" })));
    await expect(startRecording()).rejects.toMatchObject({ reason: "denied" });
  });

  it("records until stopped and releases the microphone", async () => {
    const stopped = { count: 0 };
    stubMedia(() => Promise.resolve(fakeStream(stopped)));
    const recording = await startRecording();
    expect(FakeRecorder.last?.mimeType).toBe("audio/webm;codecs=opus");
    recording.stop();
    const blob = await recording.done;
    expect(blob.size).toBe(3);
    expect(blob.type).toBe("audio/webm;codecs=opus");
    expect(stopped.count).toBe(1);
  });

  it("stops by itself after the time limit", async () => {
    vi.useFakeTimers();
    const stopped = { count: 0 };
    stubMedia(() => Promise.resolve(fakeStream(stopped)));
    const recording = await startRecording(2);
    expect(FakeRecorder.last?.state).toBe("recording");
    vi.advanceTimersByTime(2000);
    await expect(recording.done).resolves.toBeInstanceOf(Blob);
    expect(FakeRecorder.last?.state).toBe("inactive");
  });

  it("does not hand back an empty recording", async () => {
    stubMedia(() => Promise.resolve(fakeStream({ count: 0 })));
    const recording = await startRecording();
    FakeRecorder.last!.stop(0);
    await expect(recording.done).rejects.toMatchObject({ reason: "empty" });
  });
});

describe("listening speed", () => {
  it("offers normal, three-quarter and half speed only", () => {
    expect([...speeds]).toEqual([1, 0.75, 0.5]);
    expect(isSpeed(0.75)).toBe(true);
    expect(isSpeed(0)).toBe(false);
    expect(isSpeed("1")).toBe(false);
  });
});
