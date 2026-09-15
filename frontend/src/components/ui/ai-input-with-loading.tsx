"use client";

import { Sparkles, Send, Loader2, Mic, Square, VolumeX } from "lucide-react";
import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";

interface AIInputWithLoadingProps {
    value?: string;
    onChange?: (value: string) => void;
    onSubmit: (message: string) => void | Promise<void>;
    onVoiceMessage?: (userText: string, botText: string, audioBase64?: string) => void;
    loading?: boolean;
    loadingDuration?: number;
    placeholder?: string;
    className?: string;
    disabled?: boolean;
}

export function AIInputWithLoading({
    value: controlledValue,
    onChange,
    onSubmit,
    onVoiceMessage,
    loading: controlledLoading,
    loadingDuration,
    placeholder = "Ask something...",
    className,
    disabled
}: AIInputWithLoadingProps) {
    const [internalValue, setInternalValue] = useState("");
    const [internalLoading, setInternalLoading] = useState(false);
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    // Voice recording state
    const [isRecording, setIsRecording] = useState(false);
    const [isVoiceProcessing, setIsVoiceProcessing] = useState(false);
    const [isPlayingAudio, setIsPlayingAudio] = useState(false);
    const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);
    const audioChunksRef = useRef<Blob[]>([]);
    const streamRef = useRef<MediaStream | null>(null);

    const isControlled = controlledValue !== undefined;
    const inputValue = isControlled ? controlledValue : internalValue;
    const isLoading = controlledLoading !== undefined ? controlledLoading : internalLoading;

    const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        const newVal = e.target.value;
        if (!isControlled) setInternalValue(newVal);
        onChange?.(newVal);

        // Auto-resize
        if (textareaRef.current) {
            textareaRef.current.style.height = "auto";
            textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
        }
    };

    const handleSubmit = async () => {
        if (!inputValue.trim() || isLoading || disabled) return;

        const messageToSend = inputValue;

        // Clear input immediately for better UX
        if (!isControlled) setInternalValue("");
        onChange?.("");
        if (textareaRef.current) textareaRef.current.style.height = "auto";

        if (controlledLoading === undefined) {
            setInternalLoading(true);
            try {
                if (loadingDuration) {
                    await new Promise(resolve => setTimeout(resolve, loadingDuration));
                }
                await onSubmit(messageToSend);
            } finally {
                setInternalLoading(false);
            }
        } else {
            await onSubmit(messageToSend);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
        }
    };

    // Voice recording handlers
    const audioRef = useRef<HTMLAudioElement | null>(null);

    const startRecording = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            streamRef.current = stream;
            const recorder = new MediaRecorder(stream);
            audioChunksRef.current = [];

            recorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    audioChunksRef.current.push(event.data);
                }
            };

            recorder.onstop = async () => {
                setIsVoiceProcessing(true);
                const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
                audioChunksRef.current = [];

                // Send to backend for STT -> RAG -> TTS
                const formData = new FormData();
                formData.append("file", audioBlob, "recording.webm");
                formData.append("language_code", "unknown");

                try {
                    const res = await fetch("/api/v1/voice/converse", {
                        method: "POST",
                        body: formData
                    });

                    if (!res.ok) {
                        throw new Error(`Voice API error: ${res.status}`);
                    }

                    const data = await res.json();
                    console.log("Voice response:", data);

                    // Call the callback with user query, bot response, and audio
                    if (onVoiceMessage) {
                        onVoiceMessage(
                            data.query || "Voice input",
                            data.response || "No response",
                            data.audio
                        );
                    }

                    // Helper function to play audio with stop support
                    const playAudio = (audioBase64: string): Promise<void> => {
                        return new Promise((resolve, reject) => {
                            const audioFormats = ['audio/mpeg', 'audio/wav', 'audio/mp3'];

                            const tryFormat = async (index: number) => {
                                if (index >= audioFormats.length) {
                                    reject(new Error("Could not play audio with any format"));
                                    return;
                                }

                                const format = audioFormats[index];
                                try {
                                    const audio = new Audio(`data:${format};base64,${audioBase64}`);
                                    audioRef.current = audio;
                                    setIsPlayingAudio(true);

                                    audio.onended = () => {
                                        setIsPlayingAudio(false);
                                        audioRef.current = null;
                                        resolve();
                                    };

                                    audio.onerror = () => {
                                        setIsPlayingAudio(false);
                                        tryFormat(index + 1);
                                    };

                                    await audio.play();
                                } catch (e) {
                                    setIsPlayingAudio(false);
                                    tryFormat(index + 1);
                                }
                            };

                            tryFormat(0);
                        });
                    };

                    // Auto-play the audio response (English first, then native)
                    try {
                        // Stop any currently playing audio
                        if (audioRef.current) {
                            audioRef.current.pause();
                            audioRef.current = null;
                        }

                        // Play English audio first
                        if (data.audio) {
                            console.log("Playing English audio...");
                            await playAudio(data.audio);
                        }

                        // Then play native language audio
                        if (data.audio_native) {
                            console.log("Playing native language audio...");
                            await playAudio(data.audio_native);
                        }

                        if (!data.audio && !data.audio_native) {
                            console.warn("No audio received from backend");
                            if (data.error) {
                                console.warn("TTS Error:", data.error);
                            }
                        }
                    } catch (audioError) {
                        console.error("Audio playback error:", audioError);
                    }

                } catch (error) {
                    console.error("Voice processing error:", error);
                    if (onVoiceMessage) {
                        onVoiceMessage("Voice input failed", "Sorry, there was an error processing your voice message.");
                    }
                } finally {
                    setIsVoiceProcessing(false);
                    // Cleanup stream
                    if (streamRef.current) {
                        streamRef.current.getTracks().forEach(track => track.stop());
                        streamRef.current = null;
                    }
                }
            };

            recorder.start();
            setMediaRecorder(recorder);
            setIsRecording(true);

        } catch (error) {
            console.error("Microphone access denied:", error);
            alert("Please allow microphone access to use voice input.");
        }
    };

    const stopRecording = () => {
        if (mediaRecorder && mediaRecorder.state !== "inactive") {
            mediaRecorder.stop();
            setIsRecording(false);
            setMediaRecorder(null);
        }
    };

    // Stop audio playback mid-sentence
    const stopAudio = () => {
        if (audioRef.current) {
            audioRef.current.pause();
            audioRef.current.currentTime = 0;
            audioRef.current = null;
        }
        setIsPlayingAudio(false);
    };

    const handleVoiceClick = () => {
        if (isRecording) {
            stopRecording();
        } else {
            startRecording();
        }
    };

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            if (streamRef.current) {
                streamRef.current.getTracks().forEach(track => track.stop());
            }
        };
    }, []);

    const isVoiceBusy = isRecording || isVoiceProcessing;

    return (
        <div className={cn("relative w-full max-w-3xl mx-auto", className)}>

            {/* ── Stop Audio Banner ── shows whenever voice is playing */}
            <AnimatePresence>
                {isPlayingAudio && (
                    <motion.div
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: 8 }}
                        className="mb-2 flex items-center justify-between gap-3 rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-2"
                    >
                        <div className="flex items-center gap-2">
                            <motion.div
                                animate={{ scale: [1, 1.3, 1] }}
                                transition={{ duration: 0.8, repeat: Infinity }}
                                className="w-2.5 h-2.5 rounded-full bg-red-500"
                            />
                            <span className="text-sm font-medium text-red-400">Voice explanation is playing…</span>
                        </div>
                        <button
                            onClick={stopAudio}
                            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-red-500 hover:bg-red-600 active:scale-95 text-white text-xs font-semibold transition-all"
                        >
                            <VolumeX className="w-3.5 h-3.5" />
                            Stop
                        </button>
                    </motion.div>
                )}
            </AnimatePresence>

            <div className={cn(
                "relative flex items-end gap-2 p-2 rounded-3xl border shadow-sm transition-all duration-300",
                "bg-background/80 backdrop-blur top-0",
                isRecording ? "border-red-500/50 shadow-red-500/20" :
                    isVoiceProcessing ? "border-yellow-500/50 shadow-yellow-500/20" :
                        isPlayingAudio ? "border-red-500/40 shadow-red-500/10" :
                            isLoading ? "border-primary/50 shadow-primary/20" : "border-border hover:border-primary/30",
                "focus-within:border-primary focus-within:shadow-md focus-within:ring-1 focus-within:ring-primary/20",
                disabled && "opacity-50 cursor-not-allowed"
            )}>

                {/* Magic Icon */}
                <div className="flex items-center justify-center p-3 h-12 text-primary">
                    {isLoading || isVoiceProcessing ? (
                        <motion.div
                            animate={{ rotate: 360 }}
                            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                        >
                            <Sparkles className="w-5 h-5 opacity-70" />
                        </motion.div>
                    ) : isRecording ? (
                        <motion.div
                            animate={{ scale: [1, 1.2, 1] }}
                            transition={{ duration: 1, repeat: Infinity }}
                        >
                            <div className="w-3 h-3 rounded-full bg-red-500" />
                        </motion.div>
                    ) : (
                        <Sparkles className="w-5 h-5" />
                    )}
                </div>

                <textarea
                    ref={textareaRef}
                    value={inputValue}
                    onChange={handleChange}
                    onKeyDown={handleKeyDown}
                    placeholder={
                        isRecording ? "Recording... Click mic to stop" :
                            isVoiceProcessing ? "Processing voice..." :
                                isLoading ? "Generating response..." : placeholder
                    }
                    className={cn(
                        "flex-1 bg-transparent border-none outline-none resize-none py-3.5 max-h-[200px] min-h-[48px]",
                        "placeholder:text-muted-foreground/60 text-sm sm:text-base scrollbar-hide"
                    )}
                    disabled={disabled || isLoading || isVoiceBusy}
                    rows={1}
                />

                {/* Voice Button */}
                <div className="p-1.5 pb-2">
                    <motion.button
                        onClick={handleVoiceClick}
                        disabled={isLoading || isVoiceProcessing || disabled}
                        className={cn(
                            "flex items-center justify-center w-8 h-8 rounded-full transition-all duration-200",
                            isRecording
                                ? "bg-red-500 text-white hover:bg-red-600"
                                : isVoiceProcessing
                                    ? "bg-yellow-500 text-white"
                                    : "bg-muted text-muted-foreground hover:bg-muted/80 hover:text-foreground"
                        )}
                        whileTap={{ scale: 0.9 }}
                        title={isRecording ? "Stop recording" : "Start voice input"}
                    >
                        {isVoiceProcessing ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                        ) : isRecording ? (
                            <Square className="w-3 h-3 fill-current" />
                        ) : (
                            <Mic className="w-4 h-4" />
                        )}
                    </motion.button>
                </div>

                {/* Send Button */}
                <div className="p-1.5 pb-2">
                    <motion.button
                        onClick={handleSubmit}
                        disabled={!inputValue.trim() || isLoading || disabled || isVoiceBusy}
                        className={cn(
                            "flex items-center justify-center w-8 h-8 rounded-full transition-all duration-200",
                            inputValue.trim() && !isLoading && !isVoiceBusy
                                ? "bg-primary text-primary-foreground hover:scale-105 active:scale-95"
                                : "bg-muted text-muted-foreground"
                        )}
                        whileTap={{ scale: 0.9 }}
                    >
                        {isLoading ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                            <Send className="w-4 h-4 ml-0.5" />
                        )}
                    </motion.button>
                </div>

                {/* Glow effect when active */}
                <div className={cn(
                    "absolute inset-0 rounded-3xl opacity-0 transition-opacity duration-300 pointer-events-none",
                    isRecording
                        ? "bg-gradient-to-r from-red-500/10 via-red-500/10 to-red-500/10"
                        : "bg-gradient-to-r from-blue-500/10 via-purple-500/10 to-pink-500/10",
                    (isLoading || isRecording || document.activeElement === textareaRef.current) && "opacity-100"
                )} />
            </div>
        </div>
    );
}

