import { Activity, Mic, PlugZap, RefreshCw, Square } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { LiveCanvas } from "./components/LiveCanvas";
import { ScoreChart } from "./components/ScoreChart";
import { useLiveStore } from "./store/liveStore";
import type { CandidateOption, GlyphTargetSummary } from "./types/catalog";
import { fetchCandidateOptions, fetchGlyphTargets } from "./utils/apiCatalog";
import { parseAudioSampleRateHz } from "./utils/audioSampleRate";
import { encodeAudio, encodeConfigure, decodeLiveResponse, toPoints } from "./utils/liveMessages";
import { floatToPcm16 } from "./utils/pcm";
import { updateRateHz } from "./utils/scoreHistory";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8220";
const WS_URL = import.meta.env.VITE_WS_URL ?? "ws://localhost:8220/ws/live";
const SAMPLE_RATE_HZ = parseAudioSampleRateHz(import.meta.env.VITE_AUDIO_SAMPLE_RATE_HZ);

export function App(): JSX.Element {
  const socketRef = useRef<WebSocket | null>(null);
  const configuredSessionRef = useRef<string | null>(null);
  const configuredLetterRef = useRef<string | null>(null);
  const pendingConnectionRef = useRef<{ readonly sessionKey: string; readonly promise: Promise<WebSocket> } | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioStartingRef = useRef(false);
  const [glyphTargets, setGlyphTargets] = useState<GlyphTargetSummary[]>([]);
  const [candidateOptions, setCandidateOptions] = useState<CandidateOption[]>([]);
  const [catalogLoading, setCatalogLoading] = useState(false);
  const {
    candidateId,
    glyphTargetId,
    selectedLetter,
    status,
    error,
    generated,
    target,
    scoreHistory,
    setCandidateId,
    setGlyphTargetId,
    setSelectedLetter,
    setStatus,
    setError,
    acceptScore
  } = useLiveStore();
  const latestDistance = scoreHistory.at(-1)?.distance ?? 0;
  const latestScoreAtMs = scoreHistory.at(-1)?.atMs ?? 0;
  const scoreRateHz = updateRateHz(scoreHistory, latestScoreAtMs);
  const canConnect = candidateId.trim().length > 0 && glyphTargetId.trim().length > 0;
  const statusLabel = useMemo(() => status.toUpperCase(), [status]);
  const candidateIdRef = useRef(candidateId);
  const glyphTargetIdRef = useRef(glyphTargetId);
  candidateIdRef.current = candidateId;
  glyphTargetIdRef.current = glyphTargetId;

  const loadCatalog = useCallback(async (): Promise<void> => {
    setCatalogLoading(true);
    try {
      const [glyphs, candidates] = await Promise.all([
        fetchGlyphTargets(API_BASE_URL),
        fetchCandidateOptions(API_BASE_URL)
      ]);
      setGlyphTargets(glyphs);
      setCandidateOptions(candidates);
      if (candidateIdRef.current.trim().length === 0 && candidates.length > 0) {
        setCandidateId(candidates[0].id);
      }
      if (glyphTargetIdRef.current.trim().length === 0 && glyphs.length > 0) {
        setGlyphTargetId(glyphs[0].id);
        setSelectedLetter(glyphs[0].glyph_form);
      }
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "failed to load catalog");
    } finally {
      setCatalogLoading(false);
    }
  }, [setCandidateId, setError, setGlyphTargetId, setSelectedLetter]);

  useEffect(() => {
    void loadCatalog();
  }, [loadCatalog]);

  function selectGlyphTarget(value: string): void {
    setGlyphTargetId(value);
    const glyph = glyphTargets.find((target) => target.id === value);
    if (glyph !== undefined) {
      setSelectedLetter(glyph.glyph_form);
    }
  }

  const releaseAudioResources = useCallback((): void => {
    processorRef.current?.disconnect();
    sourceRef.current?.disconnect();
    streamRef.current?.getTracks().forEach((track) => track.stop());
    void audioContextRef.current?.close();
    processorRef.current = null;
    sourceRef.current = null;
    streamRef.current = null;
    audioContextRef.current = null;
  }, []);

  async function connect(): Promise<WebSocket> {
    const trimmedCandidateId = candidateId.trim();
    const trimmedGlyphTargetId = glyphTargetId.trim();
    const glyphLetter = glyphTargets.find((target) => target.id === trimmedGlyphTargetId)?.glyph_form ?? selectedLetter.trim();
    const sessionKey = `${trimmedCandidateId}:${trimmedGlyphTargetId}`;
    if (trimmedCandidateId.length === 0 || trimmedGlyphTargetId.length === 0) {
      setError("candidate and glyph target ids are required");
      throw new Error("candidate and glyph target ids are required");
    }
    if (socketRef.current?.readyState === WebSocket.OPEN && configuredSessionRef.current === sessionKey) {
      return socketRef.current;
    }
    if (pendingConnectionRef.current?.sessionKey === sessionKey) {
      return pendingConnectionRef.current.promise;
    }
    releaseAudioResources();
    const previousSocket = socketRef.current;
    socketRef.current = null;
    previousSocket?.close();
    configuredSessionRef.current = null;
    configuredLetterRef.current = null;
    setStatus("idle");
    let socket: WebSocket;
    try {
      socket = new WebSocket(WS_URL);
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "failed to create live socket";
      audioStartingRef.current = false;
      pendingConnectionRef.current = null;
      setError(message);
      throw new Error(message);
    }
    socket.binaryType = "arraybuffer";
    socketRef.current = socket;
    const connectionPromise = new Promise<WebSocket>((resolve, reject) => {
      let settled = false;
      const closeActiveConnection = (): void => {
        if (socketRef.current !== socket) {
          return;
        }
        audioStartingRef.current = false;
        socketRef.current = null;
        socket.close();
        pendingConnectionRef.current = null;
        configuredSessionRef.current = null;
        configuredLetterRef.current = null;
      };
      const fail = (message: string): void => {
        if (!settled) {
          settled = true;
          reject(new Error(message));
        }
      };
      socket.onopen = () => {
        socket.send(
          encodeConfigure({
            type: "configure",
            candidate_id: trimmedCandidateId,
            glyph_target_id: trimmedGlyphTargetId,
            scoring_metric: "procrustes"
          })
        );
      };
      socket.onmessage = (event: MessageEvent<ArrayBuffer>) => {
        if (socketRef.current !== socket) {
          return;
        }
        try {
          const response = decodeLiveResponse(event.data);
          if (response.type === "configured") {
            if (response.candidate_id !== trimmedCandidateId) {
              setError("configured candidate mismatch");
              closeActiveConnection();
              fail("configured candidate mismatch");
              return;
            }
            if (response.glyph_target_id !== trimmedGlyphTargetId) {
              setError("configured glyph target mismatch");
              closeActiveConnection();
              fail("configured glyph target mismatch");
              return;
            }
            configuredSessionRef.current = sessionKey;
            configuredLetterRef.current = glyphLetter.length > 0 ? glyphLetter : null;
            setStatus("connected");
            if (!settled) {
              settled = true;
              resolve(socket);
            }
          } else if (response.type === "score") {
            acceptScore(
              toPoints(response.contours),
              toPoints(response.target_contours),
              response.shape_distance,
              Date.now(),
              configuredLetterRef.current ?? "unassigned"
            );
          } else if (response.type === "error") {
            setError(response.message);
            if (settled) {
              releaseAudioResources();
              setStatus("idle");
              closeActiveConnection();
            } else {
              closeActiveConnection();
              fail(response.message);
            }
          }
        } catch (caught) {
          const message = caught instanceof Error ? caught.message : "failed to decode live response";
          setError(message);
          if (settled) {
            releaseAudioResources();
            setStatus("idle");
            closeActiveConnection();
          } else {
            closeActiveConnection();
          }
          fail(message);
        }
      };
      socket.onerror = () => {
        if (socketRef.current !== socket) {
          return;
        }
        releaseAudioResources();
        audioStartingRef.current = false;
        socketRef.current = null;
        socket.close();
        pendingConnectionRef.current = null;
        configuredSessionRef.current = null;
        configuredLetterRef.current = null;
        setError("live socket error");
        fail("live socket error");
      };
      socket.onclose = () => {
        if (socketRef.current !== socket) {
          return;
        }
        releaseAudioResources();
        audioStartingRef.current = false;
        socketRef.current = null;
        pendingConnectionRef.current = null;
        configuredSessionRef.current = null;
        configuredLetterRef.current = null;
        if (settled) {
          setError("live socket closed");
        } else {
          setError("live socket closed before configuration completed");
          fail("live socket closed before configuration completed");
        }
      };
    });
    const trackedPromise = connectionPromise.finally(() => {
      if (pendingConnectionRef.current?.promise === trackedPromise) {
        pendingConnectionRef.current = null;
      }
    });
    pendingConnectionRef.current = { sessionKey, promise: trackedPromise };
    return trackedPromise;
  }

  async function startAudio(): Promise<void> {
    if (audioStartingRef.current || status === "streaming") {
      return;
    }
    audioStartingRef.current = true;
    try {
      await connect();
    } catch {
      audioStartingRef.current = false;
      return;
    }
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "microphone unavailable");
      audioStartingRef.current = false;
      return;
    }
    let context: AudioContext | null = null;
    try {
      context = new AudioContext({ sampleRate: SAMPLE_RATE_HZ });
      const source = context.createMediaStreamSource(stream);
      const processor = context.createScriptProcessor(1024, 1, 1);
      processor.onaudioprocess = (event) => {
        const socket = socketRef.current;
        if (socket?.readyState !== WebSocket.OPEN) {
          return;
        }
        const samples = event.inputBuffer.getChannelData(0);
        socket.send(encodeAudio({ type: "audio", sample_rate_hz: SAMPLE_RATE_HZ, pcm16: floatToPcm16(samples) }));
      };
      source.connect(processor);
      processor.connect(context.destination);
      streamRef.current = stream;
      audioContextRef.current = context;
      processorRef.current = processor;
      sourceRef.current = source;
    } catch (caught) {
      stream.getTracks().forEach((track) => track.stop());
      void context?.close();
      audioStartingRef.current = false;
      setError(caught instanceof Error ? caught.message : "audio graph unavailable");
      return;
    }
    audioStartingRef.current = false;
    setStatus("streaming");
  }

  const stop = useCallback((): void => {
    releaseAudioResources();
    audioStartingRef.current = false;
    const socket = socketRef.current;
    socketRef.current = null;
    socket?.close();
    pendingConnectionRef.current = null;
    configuredSessionRef.current = null;
    configuredLetterRef.current = null;
    setStatus("idle");
  }, [releaseAudioResources, setStatus]);

  useEffect(() => stop, [stop]);

  return (
    <main className="app-shell">
      <section className="toolbar">
        <div className="brand-block">
          <h1>audio-glyph-inference</h1>
          <span>{statusLabel}</span>
        </div>
        <label>
          Letter
          <input value={selectedLetter} onChange={(event) => setSelectedLetter(event.target.value)} maxLength={2} />
        </label>
        <label>
          Candidate
          <input value={candidateId} onChange={(event) => setCandidateId(event.target.value)} list="candidate-options" />
          <datalist id="candidate-options">
            {candidateOptions.map((candidate) => (
              <option key={candidate.id} value={candidate.id} label={candidate.label} />
            ))}
          </datalist>
        </label>
        <label>
          Glyph target
          <input value={glyphTargetId} onChange={(event) => selectGlyphTarget(event.target.value)} list="glyph-target-options" />
          <datalist id="glyph-target-options">
            {glyphTargets.map((glyph) => (
              <option
                key={glyph.id}
                value={glyph.id}
                label={`${glyph.glyph_form} / ${glyph.font_name} / ${glyph.num_contours}`}
              />
            ))}
          </datalist>
        </label>
        <button type="button" onClick={() => void loadCatalog()} disabled={catalogLoading} aria-label="Refresh catalog">
          <RefreshCw size={18} />
        </button>
        <button type="button" onClick={() => void connect().catch(() => undefined)} disabled={!canConnect} aria-label="Connect">
          <PlugZap size={18} />
        </button>
        <button type="button" onClick={() => void startAudio()} disabled={!canConnect} aria-label="Start microphone">
          <Mic size={18} />
        </button>
        <button type="button" onClick={stop} aria-label="Stop">
          <Square size={18} />
        </button>
      </section>
      <section className="workspace">
        <LiveCanvas generated={generated} target={target} />
        <aside className="side-panel">
          <div className="metric-stack">
            <div className="metric-row">
              <Activity size={18} />
              <span>distance</span>
              <strong>{latestDistance.toFixed(5)}</strong>
            </div>
            <div className="metric-row">
              <Activity size={18} />
              <span>rate</span>
              <strong>{scoreRateHz.toFixed(1)} Hz</strong>
            </div>
          </div>
          <ScoreChart history={scoreHistory} />
          {error ? <p className="error-line">{error}</p> : null}
        </aside>
      </section>
    </main>
  );
}
