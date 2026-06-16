"use client";

import { useMemo, useRef, useState } from "react";
import { Mic, MicOff, Volume2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { sendChat } from "@/lib/api";

type SpeechRecognitionLike = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onend: (() => void) | null;
  onerror: (() => void) | null;
  start: () => void;
  stop: () => void;
};

type SpeechRecognitionEventLike = {
  results: ArrayLike<ArrayLike<{ transcript: string }>>;
};

type SpeechWindow = Window & {
  SpeechRecognition?: new () => SpeechRecognitionLike;
  webkitSpeechRecognition?: new () => SpeechRecognitionLike;
};

export function VoiceCommand() {
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const [listening, setListening] = useState(false);
  const [mode, setMode] = useState("command");
  const [transcript, setTranscript] = useState("");
  const [response, setResponse] = useState("");
  const [status, setStatus] = useState("Voice ready");

  const supported = useMemo(() => {
    if (typeof window === "undefined") {
      return false;
    }
    const speechWindow = window as SpeechWindow;
    return Boolean(speechWindow.SpeechRecognition || speechWindow.webkitSpeechRecognition);
  }, []);

  function startListening() {
    if (!supported || typeof window === "undefined") {
      setStatus("Speech recognition is not available in this browser.");
      return;
    }
    const speechWindow = window as SpeechWindow;
    const Recognition = speechWindow.SpeechRecognition || speechWindow.webkitSpeechRecognition;
    if (!Recognition) {
      return;
    }
    const recognition = new Recognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-US";
    recognition.onresult = (event) => {
      const text = event.results[0]?.[0]?.transcript || "";
      setTranscript(text);
      void submitVoice(text);
    };
    recognition.onend = () => setListening(false);
    recognition.onerror = () => {
      setListening(false);
      setStatus("Voice capture stopped.");
    };
    recognitionRef.current = recognition;
    setListening(true);
    setStatus("Listening...");
    recognition.start();
  }

  function stopListening() {
    recognitionRef.current?.stop();
    setListening(false);
  }

  async function submitVoice(text: string) {
    if (!text.trim()) {
      return;
    }
    try {
      setStatus("Atlas is responding...");
      const result = await sendChat(text, `voice_mode:${mode}`);
      setResponse(result.answer);
      setStatus(`Answered with ${result.citations.length} citations`);
      speak(result.answer);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Voice command failed");
    }
  }

  function speak(text: string) {
    if (typeof window === "undefined" || !window.speechSynthesis) {
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text.slice(0, 420));
    utterance.rate = 0.98;
    utterance.pitch = 0.95;
    window.speechSynthesis.speak(utterance);
  }

  return (
    <div className="rounded-lg border border-atlas-line bg-atlas-panelSoft p-3">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Volume2 className="h-4 w-4 text-atlas-blue" />
          <p className="text-sm font-semibold text-atlas-text">Voice command</p>
        </div>
        <Badge tone={supported ? "teal" : "amber"}>{supported ? status : "browser limited"}</Badge>
      </div>
      <div className="flex flex-wrap gap-2">
        <select
          className="h-10 rounded-md border border-atlas-line bg-atlas-bg px-3 text-sm text-atlas-text outline-none"
          value={mode}
          onChange={(event) => setMode(event.target.value)}
          aria-label="Voice mode"
        >
          <option value="command">Command</option>
          <option value="career">Career</option>
          <option value="learning">Learning</option>
          <option value="code">Code</option>
        </select>
        <Button onClick={listening ? stopListening : startListening} variant="primary">
          {listening ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
          {listening ? "Stop" : "Push to talk"}
        </Button>
      </div>
      {transcript ? (
        <p className="mt-3 rounded-md border border-atlas-line bg-atlas-bg p-3 text-sm text-atlas-muted">
          {transcript}
        </p>
      ) : null}
      {response ? (
        <p className="mt-3 max-h-40 overflow-auto rounded-md border border-atlas-line bg-atlas-bg p-3 text-sm leading-6 text-atlas-muted atlas-scrollbar">
          {response}
        </p>
      ) : null}
    </div>
  );
}
