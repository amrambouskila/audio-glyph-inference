import { decode, encode } from "@msgpack/msgpack";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { useLiveStore } from "./store/liveStore";

vi.mock("./components/LiveCanvas", () => ({
  LiveCanvas: () => <div data-testid="live-canvas" />
}));

vi.mock("./components/ScoreChart", () => ({
  ScoreChart: () => <div data-testid="score-chart" />
}));

function jsonResponse(value: unknown, ok = true, status = 200): Response {
  return {
    ok,
    status,
    json: () => Promise.resolve(value)
  } as Response;
}

function arrayBufferFromBytes(bytes: Uint8Array): ArrayBuffer {
  const buffer = new ArrayBuffer(bytes.byteLength);
  new Uint8Array(buffer).set(bytes);
  return buffer;
}

class MockWebSocket {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSING = 2;
  static readonly CLOSED = 3;
  static instances: MockWebSocket[] = [];

  binaryType: BinaryType = "blob";
  readyState = MockWebSocket.CONNECTING;
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent<ArrayBuffer>) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  readonly sent: (string | ArrayBufferLike | Blob | ArrayBufferView)[] = [];

  constructor(readonly url: string | URL) {
    MockWebSocket.instances.push(this);
  }

  send(data: string | ArrayBufferLike | Blob | ArrayBufferView): void {
    this.sent.push(data);
  }

  close(): void {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.(new Event("close") as CloseEvent);
  }

  open(): void {
    this.readyState = MockWebSocket.OPEN;
    this.onopen?.(new Event("open"));
  }

  receive(value: unknown): void {
    this.onmessage?.(new MessageEvent("message", { data: arrayBufferFromBytes(encode(value)) }));
  }

  receiveBytes(bytes: Uint8Array): void {
    this.onmessage?.(new MessageEvent("message", { data: arrayBufferFromBytes(bytes) }));
  }
}

function createThrowingWebSocket(): typeof WebSocket {
  function ThrowingWebSocketConstructor(): never {
    throw new Error("invalid live socket url");
  }
  Object.defineProperty(ThrowingWebSocketConstructor, "OPEN", { value: 1 });
  return ThrowingWebSocketConstructor as unknown as typeof WebSocket;
}

function configuredMessage(candidateId = "candidate-1", glyphTargetId = "glyph-1"): object {
  return { type: "configured", candidate_id: candidateId, glyph_target_id: glyphTargetId };
}

class MockMediaStreamTrack {
  stopped = false;

  stop(): void {
    this.stopped = true;
  }
}

class MockMediaStreamAudioSourceNode {
  connectedTo: MockScriptProcessorNode | null = null;
  disconnected = false;

  connect(node: MockScriptProcessorNode): void {
    this.connectedTo = node;
  }

  disconnect(): void {
    this.disconnected = true;
  }
}

class MockScriptProcessorNode {
  onaudioprocess: ((event: AudioProcessingEvent) => void) | null = null;
  connectedTo: AudioNode | null = null;
  disconnected = false;

  connect(node: AudioNode): void {
    this.connectedTo = node;
  }

  disconnect(): void {
    this.disconnected = true;
  }

  process(samples: Float32Array): void {
    this.onaudioprocess?.({
      inputBuffer: {
        getChannelData: () => samples
      }
    } as unknown as AudioProcessingEvent);
  }
}

class MockAudioContext {
  static instances: MockAudioContext[] = [];

  readonly destination = {} as AudioNode;
  readonly source = new MockMediaStreamAudioSourceNode();
  readonly processor = new MockScriptProcessorNode();
  closed = false;

  constructor(readonly options: AudioContextOptions) {
    MockAudioContext.instances.push(this);
  }

  createMediaStreamSource(): MediaStreamAudioSourceNode {
    return this.source as unknown as MediaStreamAudioSourceNode;
  }

  createScriptProcessor(): ScriptProcessorNode {
    return this.processor as unknown as ScriptProcessorNode;
  }

  close(): Promise<void> {
    this.closed = true;
    return Promise.resolve();
  }
}

function installCatalogFetch(): void {
  const fetchMock = vi
    .fn<(input: RequestInfo | URL, init?: RequestInit) => Promise<Response>>()
    .mockResolvedValueOnce(
      jsonResponse([{ id: "glyph-1", letter: "\u05d0", glyph_form: "\u05d0", font_name: "StamAshkenazCLM.ttf", num_contours: 1 }])
    )
    .mockResolvedValueOnce(
      jsonResponse([
        {
          id: "run-1",
          name: "live-smoke-seed",
          family: "lissajous",
          search_strategy: "grid",
          completed_at: "2026-06-04T00:00:00Z",
          best_candidate_id: "candidate-1"
        }
      ])
    )
    .mockResolvedValueOnce(
      jsonResponse({
        run: {
          id: "run-1",
          name: "live-smoke-seed",
          family: "lissajous",
          search_strategy: "grid",
          completed_at: "2026-06-04T00:00:00Z",
          best_candidate_id: "candidate-1"
        },
        best_candidate: {
          id: "candidate-1",
          family: "lissajous",
          mean_shape_distance: 1.0,
          lookup_ratio: 1.0
        },
        candidate_count: 1
      })
    );
  vi.stubGlobal("fetch", fetchMock);
}

async function waitForCatalogSelection(): Promise<void> {
  await waitFor(() => {
    expect(screen.getByLabelText("Candidate")).toHaveValue("candidate-1");
    expect(screen.getByLabelText("Glyph target")).toHaveValue("glyph-1");
    expect(screen.getByLabelText("Letter")).toHaveValue("\u05d0");
  });
}

describe("App", () => {
  beforeEach(() => {
    MockWebSocket.instances = [];
    MockAudioContext.instances = [];
    vi.stubGlobal("WebSocket", MockWebSocket);
    useLiveStore.setState({
      candidateId: "",
      glyphTargetId: "",
      status: "idle",
      selectedLetter: "",
      generated: [],
      target: [],
      scoreHistory: [],
      error: null
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("auto-selects the first fetched candidate and glyph target when fields are empty", async () => {
    installCatalogFetch();
    render(<App />);

    await waitForCatalogSelection();
    expect(screen.getByRole("button", { name: "Connect" })).toBeEnabled();
  });

  it("marks the socket connected only after the backend confirms configuration", async () => {
    installCatalogFetch();
    render(<App />);
    await waitForCatalogSelection();

    fireEvent.click(screen.getByRole("button", { name: "Connect" }));
    expect(MockWebSocket.instances).toHaveLength(1);
    const socket = MockWebSocket.instances[0];

    act(() => socket.open());

    expect(screen.getByText("IDLE")).toBeInTheDocument();
    expect(socket.sent).toHaveLength(1);
    expect(decode(socket.sent[0] as ArrayBufferLike)).toEqual({
      type: "configure",
      candidate_id: "candidate-1",
      glyph_target_id: "glyph-1",
      scoring_metric: "procrustes"
    });

    act(() => socket.receive(configuredMessage()));

    await waitFor(() => expect(screen.getByText("CONNECTED")).toBeInTheDocument());
  });

  it("rejects a configured response for the wrong glyph target", async () => {
    installCatalogFetch();
    render(<App />);
    await waitForCatalogSelection();

    fireEvent.click(screen.getByRole("button", { name: "Connect" }));
    const socket = MockWebSocket.instances[0];
    act(() => socket.open());
    act(() => socket.receive(configuredMessage("candidate-1", "glyph-2")));

    await waitFor(() => expect(screen.getByText("configured glyph target mismatch")).toBeInTheDocument());
    expect(screen.getByText("ERROR")).toBeInTheDocument();
    expect(socket.readyState).toBe(MockWebSocket.CLOSED);
  });

  it("reuses an in-flight connection when connect is clicked repeatedly", async () => {
    installCatalogFetch();
    render(<App />);
    await waitForCatalogSelection();

    const connectButton = screen.getByRole("button", { name: "Connect" });
    fireEvent.click(connectButton);
    fireEvent.click(connectButton);

    expect(MockWebSocket.instances).toHaveLength(1);
    const socket = MockWebSocket.instances[0];
    act(() => socket.open());
    expect(socket.sent).toHaveLength(1);

    act(() => socket.receive(configuredMessage()));

    await waitFor(() => expect(screen.getByText("CONNECTED")).toBeInTheDocument());
  });

  it("surfaces live socket construction failures when connecting", async () => {
    installCatalogFetch();
    vi.stubGlobal("WebSocket", createThrowingWebSocket());
    render(<App />);
    await waitForCatalogSelection();

    fireEvent.click(screen.getByRole("button", { name: "Connect" }));

    await waitFor(() => expect(screen.getByText("invalid live socket url")).toBeInTheDocument());
    expect(screen.getByText("ERROR")).toBeInTheDocument();
  });

  it("labels score history with the configured glyph letter when the free-text letter changes", async () => {
    installCatalogFetch();
    render(<App />);
    await waitForCatalogSelection();

    fireEvent.click(screen.getByRole("button", { name: "Connect" }));
    const socket = MockWebSocket.instances[0];
    act(() => socket.open());
    act(() => socket.receive(configuredMessage()));
    await waitFor(() => expect(screen.getByText("CONNECTED")).toBeInTheDocument());

    fireEvent.change(screen.getByLabelText("Letter"), { target: { value: "\u05d1" } });
    act(() =>
      socket.receive({
        type: "score",
        shape_distance: 0.25,
        contours: [
          [0, 0],
          [1, 0]
        ],
        target_contours: [
          [0, 0],
          [0, 1]
        ]
      })
    );

    await waitFor(() => expect(useLiveStore.getState().scoreHistory).toHaveLength(1));
    const scoreSample = useLiveStore.getState().scoreHistory[0];
    expect(scoreSample.atMs).toBeGreaterThan(0);
    expect(scoreSample.distance).toBe(0.25);
    expect(scoreSample.letter).toBe("\u05d0");
  });

  it("does not request microphone access when configuration fails", async () => {
    installCatalogFetch();
    const getUserMedia = vi.fn<() => Promise<MediaStream>>();
    vi.stubGlobal("navigator", { mediaDevices: { getUserMedia } });
    render(<App />);
    await waitForCatalogSelection();

    fireEvent.click(screen.getByRole("button", { name: "Start microphone" }));
    expect(MockWebSocket.instances).toHaveLength(1);
    const socket = MockWebSocket.instances[0];

    act(() => socket.open());
    act(() => socket.receive({ type: "error", message: "bad candidate" }));

    await waitFor(() => expect(screen.getByText("bad candidate")).toBeInTheDocument());
    expect(getUserMedia).not.toHaveBeenCalled();
    expect(socket.readyState).toBe(MockWebSocket.CLOSED);
  });

  it("does not request microphone access when live socket construction fails", async () => {
    installCatalogFetch();
    const getUserMedia = vi.fn<() => Promise<MediaStream>>();
    vi.stubGlobal("navigator", { mediaDevices: { getUserMedia } });
    vi.stubGlobal("WebSocket", createThrowingWebSocket());
    render(<App />);
    await waitForCatalogSelection();

    fireEvent.click(screen.getByRole("button", { name: "Start microphone" }));

    await waitFor(() => expect(screen.getByText("invalid live socket url")).toBeInTheDocument());
    expect(getUserMedia).not.toHaveBeenCalled();
    expect(screen.getByText("ERROR")).toBeInTheDocument();
  });

  it("streams microphone audio as MessagePack PCM16 and releases resources on stop", async () => {
    installCatalogFetch();
    const track = new MockMediaStreamTrack();
    const stream = {
      getTracks: () => [track]
    } as unknown as MediaStream;
    const getUserMedia = vi.fn<() => Promise<MediaStream>>().mockResolvedValue(stream);
    vi.stubGlobal("navigator", { mediaDevices: { getUserMedia } });
    vi.stubGlobal("AudioContext", MockAudioContext);
    render(<App />);
    await waitForCatalogSelection();

    fireEvent.click(screen.getByRole("button", { name: "Start microphone" }));
    expect(MockWebSocket.instances).toHaveLength(1);
    const socket = MockWebSocket.instances[0];
    act(() => socket.open());
    act(() => socket.receive(configuredMessage()));

    await waitFor(() => expect(screen.getByText("STREAMING")).toBeInTheDocument());
    expect(getUserMedia).toHaveBeenCalledWith({ audio: true });
    expect(MockAudioContext.instances).toHaveLength(1);
    const context = MockAudioContext.instances[0];
    expect(context.options).toEqual({ sampleRate: 16000 });
    expect(context.source.connectedTo).toBe(context.processor);
    expect(context.processor.connectedTo).toBe(context.destination);

    act(() => context.processor.process(new Float32Array([-1, 0, 1])));

    expect(socket.sent).toHaveLength(2);
    expect(decode(socket.sent[1] as ArrayBufferLike)).toEqual({
      type: "audio",
      sample_rate_hz: 16000,
      pcm16: new Uint8Array([0, 128, 0, 0, 255, 127])
    });

    fireEvent.click(screen.getByRole("button", { name: "Stop" }));

    await waitFor(() => expect(screen.getByText("IDLE")).toBeInTheDocument());
    expect(context.processor.disconnected).toBe(true);
    expect(context.source.disconnected).toBe(true);
    expect(track.stopped).toBe(true);
    expect(context.closed).toBe(true);
    expect(socket.readyState).toBe(MockWebSocket.CLOSED);
  });

  it("ignores repeated microphone starts while startup is already in flight", async () => {
    installCatalogFetch();
    const track = new MockMediaStreamTrack();
    const stream = {
      getTracks: () => [track]
    } as unknown as MediaStream;
    const getUserMedia = vi.fn<() => Promise<MediaStream>>().mockResolvedValue(stream);
    vi.stubGlobal("navigator", { mediaDevices: { getUserMedia } });
    vi.stubGlobal("AudioContext", MockAudioContext);
    render(<App />);
    await waitForCatalogSelection();

    const startButton = screen.getByRole("button", { name: "Start microphone" });
    fireEvent.click(startButton);
    fireEvent.click(startButton);
    expect(MockWebSocket.instances).toHaveLength(1);

    const socket = MockWebSocket.instances[0];
    act(() => socket.open());
    act(() => socket.receive(configuredMessage()));

    await waitFor(() => expect(screen.getByText("STREAMING")).toBeInTheDocument());
    expect(getUserMedia).toHaveBeenCalledTimes(1);
    expect(MockAudioContext.instances).toHaveLength(1);
  });

  it("stops the microphone stream and allows retry when audio graph setup fails", async () => {
    installCatalogFetch();
    function FailingAudioContext(): never {
      throw new Error("audio graph failed");
    }
    const failedTrack = new MockMediaStreamTrack();
    const retryTrack = new MockMediaStreamTrack();
    const failedStream = {
      getTracks: () => [failedTrack]
    } as unknown as MediaStream;
    const retryStream = {
      getTracks: () => [retryTrack]
    } as unknown as MediaStream;
    const getUserMedia = vi.fn<() => Promise<MediaStream>>().mockResolvedValueOnce(failedStream).mockResolvedValueOnce(retryStream);
    vi.stubGlobal("navigator", { mediaDevices: { getUserMedia } });
    vi.stubGlobal("AudioContext", FailingAudioContext);
    render(<App />);
    await waitForCatalogSelection();

    fireEvent.click(screen.getByRole("button", { name: "Start microphone" }));
    const socket = MockWebSocket.instances[0];
    act(() => socket.open());
    act(() => socket.receive(configuredMessage()));

    await waitFor(() => expect(screen.getByText("audio graph failed")).toBeInTheDocument());
    expect(failedTrack.stopped).toBe(true);
    expect(getUserMedia).toHaveBeenCalledTimes(1);

    vi.stubGlobal("AudioContext", MockAudioContext);
    fireEvent.click(screen.getByRole("button", { name: "Start microphone" }));

    await waitFor(() => expect(screen.getByText("STREAMING")).toBeInTheDocument());
    expect(getUserMedia).toHaveBeenCalledTimes(2);
    expect(MockAudioContext.instances).toHaveLength(1);
    expect(retryTrack.stopped).toBe(false);
  });

  it("releases microphone resources when the live socket closes during streaming", async () => {
    installCatalogFetch();
    const track = new MockMediaStreamTrack();
    const stream = {
      getTracks: () => [track]
    } as unknown as MediaStream;
    const getUserMedia = vi.fn<() => Promise<MediaStream>>().mockResolvedValue(stream);
    vi.stubGlobal("navigator", { mediaDevices: { getUserMedia } });
    vi.stubGlobal("AudioContext", MockAudioContext);
    render(<App />);
    await waitForCatalogSelection();

    fireEvent.click(screen.getByRole("button", { name: "Start microphone" }));
    const socket = MockWebSocket.instances[0];
    act(() => socket.open());
    act(() => socket.receive(configuredMessage()));

    await waitFor(() => expect(screen.getByText("STREAMING")).toBeInTheDocument());
    const context = MockAudioContext.instances[0];

    act(() => socket.close());

    await waitFor(() => expect(screen.getByText("live socket closed")).toBeInTheDocument());
    expect(context.processor.disconnected).toBe(true);
    expect(context.source.disconnected).toBe(true);
    expect(track.stopped).toBe(true);
    expect(context.closed).toBe(true);
  });

  it("closes the live socket and releases microphone resources when the live socket errors during streaming", async () => {
    installCatalogFetch();
    const track = new MockMediaStreamTrack();
    const stream = {
      getTracks: () => [track]
    } as unknown as MediaStream;
    const getUserMedia = vi.fn<() => Promise<MediaStream>>().mockResolvedValue(stream);
    vi.stubGlobal("navigator", { mediaDevices: { getUserMedia } });
    vi.stubGlobal("AudioContext", MockAudioContext);
    render(<App />);
    await waitForCatalogSelection();

    fireEvent.click(screen.getByRole("button", { name: "Start microphone" }));
    const socket = MockWebSocket.instances[0];
    act(() => socket.open());
    act(() => socket.receive(configuredMessage()));

    await waitFor(() => expect(screen.getByText("STREAMING")).toBeInTheDocument());
    const context = MockAudioContext.instances[0];

    act(() => socket.onerror?.(new Event("error")));

    await waitFor(() => expect(screen.getByText("live socket error")).toBeInTheDocument());
    expect(context.processor.disconnected).toBe(true);
    expect(context.source.disconnected).toBe(true);
    expect(track.stopped).toBe(true);
    expect(context.closed).toBe(true);
    expect(socket.readyState).toBe(MockWebSocket.CLOSED);
  });

  it("closes the live socket and releases microphone resources after a malformed live response", async () => {
    installCatalogFetch();
    const track = new MockMediaStreamTrack();
    const stream = {
      getTracks: () => [track]
    } as unknown as MediaStream;
    const getUserMedia = vi.fn<() => Promise<MediaStream>>().mockResolvedValue(stream);
    vi.stubGlobal("navigator", { mediaDevices: { getUserMedia } });
    vi.stubGlobal("AudioContext", MockAudioContext);
    render(<App />);
    await waitForCatalogSelection();

    fireEvent.click(screen.getByRole("button", { name: "Start microphone" }));
    const socket = MockWebSocket.instances[0];
    act(() => socket.open());
    act(() => socket.receive(configuredMessage()));

    await waitFor(() => expect(screen.getByText("STREAMING")).toBeInTheDocument());
    const context = MockAudioContext.instances[0];

    act(() => socket.receiveBytes(new Uint8Array([0xc1])));

    await waitFor(() => expect(screen.getByText("IDLE")).toBeInTheDocument());
    expect(screen.getByText(/Unrecognized type byte/)).toBeInTheDocument();
    expect(context.processor.disconnected).toBe(true);
    expect(context.source.disconnected).toBe(true);
    expect(track.stopped).toBe(true);
    expect(context.closed).toBe(true);
    expect(socket.readyState).toBe(MockWebSocket.CLOSED);
  });

  it("closes the live socket and releases microphone resources after a backend live error", async () => {
    installCatalogFetch();
    const track = new MockMediaStreamTrack();
    const stream = {
      getTracks: () => [track]
    } as unknown as MediaStream;
    const getUserMedia = vi.fn<() => Promise<MediaStream>>().mockResolvedValue(stream);
    vi.stubGlobal("navigator", { mediaDevices: { getUserMedia } });
    vi.stubGlobal("AudioContext", MockAudioContext);
    render(<App />);
    await waitForCatalogSelection();

    fireEvent.click(screen.getByRole("button", { name: "Start microphone" }));
    const socket = MockWebSocket.instances[0];
    act(() => socket.open());
    act(() => socket.receive(configuredMessage()));

    await waitFor(() => expect(screen.getByText("STREAMING")).toBeInTheDocument());
    const context = MockAudioContext.instances[0];

    act(() => socket.receive({ type: "error", message: "shape distance failed" }));

    await waitFor(() => expect(screen.getByText("IDLE")).toBeInTheDocument());
    expect(screen.getByText("shape distance failed")).toBeInTheDocument();
    expect(context.processor.disconnected).toBe(true);
    expect(context.source.disconnected).toBe(true);
    expect(track.stopped).toBe(true);
    expect(context.closed).toBe(true);
    expect(socket.readyState).toBe(MockWebSocket.CLOSED);
  });

  it("releases microphone resources before reconfiguring a streaming session", async () => {
    installCatalogFetch();
    const track = new MockMediaStreamTrack();
    const stream = {
      getTracks: () => [track]
    } as unknown as MediaStream;
    const getUserMedia = vi.fn<() => Promise<MediaStream>>().mockResolvedValue(stream);
    vi.stubGlobal("navigator", { mediaDevices: { getUserMedia } });
    vi.stubGlobal("AudioContext", MockAudioContext);
    render(<App />);
    await waitForCatalogSelection();

    fireEvent.click(screen.getByRole("button", { name: "Start microphone" }));
    const streamingSocket = MockWebSocket.instances[0];
    act(() => streamingSocket.open());
    act(() => streamingSocket.receive(configuredMessage()));

    await waitFor(() => expect(screen.getByText("STREAMING")).toBeInTheDocument());
    const context = MockAudioContext.instances[0];

    fireEvent.change(screen.getByLabelText("Candidate"), { target: { value: "candidate-2" } });
    fireEvent.click(screen.getByRole("button", { name: "Connect" }));

    expect(context.processor.disconnected).toBe(true);
    expect(context.source.disconnected).toBe(true);
    expect(track.stopped).toBe(true);
    expect(context.closed).toBe(true);
    expect(streamingSocket.readyState).toBe(MockWebSocket.CLOSED);
    expect(MockWebSocket.instances).toHaveLength(2);
    expect(screen.getByText("IDLE")).toBeInTheDocument();

    const reconfiguredSocket = MockWebSocket.instances[1];
    act(() => reconfiguredSocket.open());

    expect(decode(reconfiguredSocket.sent[0] as ArrayBufferLike)).toEqual({
      type: "configure",
      candidate_id: "candidate-2",
      glyph_target_id: "glyph-1",
      scoring_metric: "procrustes"
    });

    act(() => reconfiguredSocket.receive(configuredMessage("candidate-2")));

    await waitFor(() => expect(screen.getByText("CONNECTED")).toBeInTheDocument());
  });

  it("releases microphone and socket resources on unmount", async () => {
    installCatalogFetch();
    const track = new MockMediaStreamTrack();
    const stream = {
      getTracks: () => [track]
    } as unknown as MediaStream;
    const getUserMedia = vi.fn<() => Promise<MediaStream>>().mockResolvedValue(stream);
    vi.stubGlobal("navigator", { mediaDevices: { getUserMedia } });
    vi.stubGlobal("AudioContext", MockAudioContext);
    const { unmount } = render(<App />);
    await waitForCatalogSelection();

    fireEvent.click(screen.getByRole("button", { name: "Start microphone" }));
    const socket = MockWebSocket.instances[0];
    act(() => socket.open());
    act(() => socket.receive(configuredMessage()));

    await waitFor(() => expect(screen.getByText("STREAMING")).toBeInTheDocument());
    const context = MockAudioContext.instances[0];

    unmount();

    expect(context.processor.disconnected).toBe(true);
    expect(context.source.disconnected).toBe(true);
    expect(track.stopped).toBe(true);
    expect(context.closed).toBe(true);
    expect(socket.readyState).toBe(MockWebSocket.CLOSED);
  });
});

