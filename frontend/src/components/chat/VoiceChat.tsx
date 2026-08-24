"use client";

import { Mic, MicOff, Volume2, VolumeX, Sparkles, Loader2, X } from "lucide-react";
import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";

interface VoiceChatProps {
    onStart?: () => void;
    onStop?: (duration: number) => void;
    onVolumeChange?: (volume: number) => void;
    onClose?: () => void;
    onConversationComplete?: (userText: string, botText: string) => void;
    className?: string;
    demoMode?: boolean;
}

interface Particle {
    id: number;
    x: number;
    y: number;
    size: number;
    opacity: number;
    velocity: { x: number; y: number };
}

export function VoiceChat({
    onStart,
    onStop,
    onVolumeChange,
    onClose,
    onConversationComplete,
    className,
    demoMode = true
}: VoiceChatProps) {
    const [isListening, setIsListening] = useState(false);
    const [isProcessing, setIsProcessing] = useState(false);
    const [isSpeaking, setIsSpeaking] = useState(false);
    const [volume, setVolume] = useState(0);
    const [duration, setDuration] = useState(0);
    const [particles, setParticles] = useState<Particle[]>([]);
    const [waveformData, setWaveformData] = useState<number[]>(Array(32).fill(0));
    const intervalRef = useRef<NodeJS.Timeout>();
    const animationRef = useRef<number>();

    // Generate particles for ambient effect
    useEffect(() => {
        const generateParticles = () => {
            const newParticles: Particle[] = [];
            for (let i = 0; i < 20; i++) {
                newParticles.push({
                    id: i,
                    x: Math.random() * 400,
                    y: Math.random() * 400,
                    size: Math.random() * 3 + 1,
                    opacity: Math.random() * 0.3 + 0.1,
                    velocity: {
                        x: (Math.random() - 0.5) * 0.5,
                        y: (Math.random() - 0.5) * 0.5
                    }
                });
            }
            setParticles(newParticles);
        };

        generateParticles();
    }, []);

    // Animate particles
    useEffect(() => {
        const animateParticles = () => {
            setParticles(prev => prev.map(particle => ({
                ...particle,
                x: (particle.x + particle.velocity.x + 400) % 400,
                y: (particle.y + particle.velocity.y + 400) % 400,
                opacity: particle.opacity + (Math.random() - 0.5) * 0.02
            })));
            animationRef.current = requestAnimationFrame(animateParticles);
        };

        animationRef.current = requestAnimationFrame(animateParticles);
        return () => {
            if (animationRef.current) {
                cancelAnimationFrame(animationRef.current);
            }
        };
    }, []);

    // Timer and waveform simulation
    useEffect(() => {
        if (isListening) {
            intervalRef.current = setInterval(() => {
                setDuration(prev => prev + 1);

                // Simulate audio waveform
                const newWaveform = Array(32).fill(0).map(() =>
                    Math.random() * (isListening ? 100 : 20)
                );
                setWaveformData(newWaveform);

                // Simulate volume changes
                const newVolume = Math.random() * 100;
                setVolume(newVolume);
                onVolumeChange?.(newVolume);
            }, 100);
        } else {
            if (intervalRef.current) {
                clearInterval(intervalRef.current);
            }
            setWaveformData(Array(32).fill(0));
            setVolume(0);
        }

        return () => {
            if (intervalRef.current) {
                clearInterval(intervalRef.current);
            }
        };
    }, [isListening, onVolumeChange]);

    // Demo mode simulation
    useEffect(() => {
        if (!demoMode) return;

        // Only run demo sequence if not manually stopped
        let timeout: NodeJS.Timeout;
        const demoSequence = async () => {
            // Only loop if component is mounted
        };

        // NOTE: Disabled auto demo loop for integration to avoid annoyance
        // const timeout = setTimeout(demoSequence, 1000);
        // return () => clearTimeout(timeout);
    }, [demoMode]);

    const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);
    const audioChunks = useRef<Blob[]>([]);

    const handleToggleListening = async () => {
        if (isListening) {
            // STOP LISTENING
            setIsListening(false);
            mediaRecorder?.stop();
        } else {
            // START LISTENING
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                const recorder = new MediaRecorder(stream);

                recorder.ondataavailable = (event) => {
                    if (event.data.size > 0) {
                        audioChunks.current.push(event.data);
                    }
                };

                recorder.onstop = async () => {
                    setIsProcessing(true);
                    const audioBlob = new Blob(audioChunks.current, { type: 'audio/wav' });
                    audioChunks.current = []; // Reset chunks

                    // Send to Backend for Full Processing (STT -> RAG -> TTS)
                    const formData = new FormData();
                    formData.append("file", audioBlob, "recording.wav");
                    formData.append("language_code", "unknown");

                    try {
                        const res = await fetch("/api/v1/voice/converse", {
                            method: "POST",
                            body: formData
                        });

                        if (!res.ok) throw new Error("Voice conversation failed");

                        const data = await res.json();
                        console.log("User:", data.query);
                        console.log("Bot:", data.response);

                        if (data.audio) {
                            setIsProcessing(false);
                            setIsSpeaking(true);
                            const audio = new Audio(`data:audio/wav;base64,${data.audio}`);
                            audio.onended = () => setIsSpeaking(false);
                            audio.play();
                        } else {
                            setIsProcessing(false);
                        }

                        // Notify parent component of completed conversation
                        if (data.query && data.response) {
                            onConversationComplete?.(data.query, data.response);
                        }
                    } catch (error) {
                        console.error("Voice Error:", error);
                        setIsProcessing(false);
                    } finally {
                        // Cleanup stream
                        stream.getTracks().forEach(track => track.stop());
                    }
                };

                recorder.start();
                setMediaRecorder(recorder);
                setIsListening(true);
                onStart?.();

            } catch (error) {
                console.error("Microphone access denied:", error);
            }
        }
    };

    const formatTime = (seconds: number) => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
    };

    const getStatusText = () => {
        if (isListening) return "Listening...";
        if (isProcessing) return "Processing...";
        if (isSpeaking) return "Speaking...";
        return "Tap to speak";
    };

    const getStatusColor = () => {
        if (isListening) return "text-blue-400";
        if (isProcessing) return "text-yellow-400";
        if (isSpeaking) return "text-green-400";
        return "text-muted-foreground";
    };

    return (
        <div className={cn("fixed inset-0 z-50 flex flex-col items-center justify-center bg-background/95 backdrop-blur-sm", className)}>

            {/* Close Button */}
            <button
                onClick={onClose}
                className="absolute top-6 right-6 p-2 rounded-full hover:bg-muted transition-colors z-50"
            >
                <X className="w-6 h-6 text-muted-foreground" />
            </button>

            {/* Ambient particles */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                {particles.map(particle => (
                    <motion.div
                        key={particle.id}
                        className="absolute w-1 h-1 bg-primary/20 rounded-full"
                        style={{
                            left: particle.x,
                            top: particle.y,
                            opacity: particle.opacity
                        }}
                        animate={{
                            scale: [1, 1.5, 1],
                        }}
                        transition={{
                            duration: 2,
                            repeat: Infinity,
                            ease: "easeInOut"
                        }}
                    />
                ))}
            </div>

            {/* Background glow effects */}
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                <motion.div
                    className="w-96 h-96 rounded-full bg-gradient-to-r from-blue-500/10 via-purple-500/10 to-pink-500/10 blur-3xl"
                    animate={{
                        scale: isListening ? [1, 1.2, 1] : [1, 1.1, 1],
                        opacity: isListening ? [0.3, 0.6, 0.3] : [0.1, 0.2, 0.1]
                    }}
                    transition={{
                        duration: 2,
                        repeat: Infinity,
                        ease: "easeInOut"
                    }}
                />
            </div>

            <div className="relative z-10 flex flex-col items-center space-y-12">
                {/* Main voice button */}
                <motion.div
                    className="relative"
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                >
                    <motion.button
                        onClick={handleToggleListening}
                        className={cn(
                            "relative w-32 h-32 rounded-full flex items-center justify-center transition-all duration-300",
                            "bg-gradient-to-br from-primary/20 to-primary/10 border-2",
                            isListening ? "border-blue-500 shadow-lg shadow-blue-500/25" :
                                isProcessing ? "border-yellow-500 shadow-lg shadow-yellow-500/25" :
                                    isSpeaking ? "border-green-500 shadow-lg shadow-green-500/25" :
                                        "border-border hover:border-primary/50"
                        )}
                        animate={{
                            boxShadow: isListening
                                ? ["0 0 0 0 rgba(59, 130, 246, 0.4)", "0 0 0 20px rgba(59, 130, 246, 0)"]
                                : undefined
                        }}
                        transition={{
                            duration: 1.5,
                            repeat: isListening ? Infinity : 0
                        }}
                    >
                        <AnimatePresence mode="wait">
                            {isProcessing ? (
                                <motion.div
                                    key="processing"
                                    initial={{ opacity: 0, scale: 0.8 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    exit={{ opacity: 0, scale: 0.8 }}
                                >
                                    <Loader2 className="w-12 h-12 text-yellow-500 animate-spin" />
                                </motion.div>
                            ) : isSpeaking ? (
                                <motion.div
                                    key="speaking"
                                    initial={{ opacity: 0, scale: 0.8 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    exit={{ opacity: 0, scale: 0.8 }}
                                >
                                    <Volume2 className="w-12 h-12 text-green-500" />
                                </motion.div>
                            ) : isListening ? (
                                <motion.div
                                    key="listening"
                                    initial={{ opacity: 0, scale: 0.8 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    exit={{ opacity: 0, scale: 0.8 }}
                                >
                                    <Mic className="w-12 h-12 text-blue-500" />
                                </motion.div>
                            ) : (
                                <motion.div
                                    key="idle"
                                    initial={{ opacity: 0, scale: 0.8 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    exit={{ opacity: 0, scale: 0.8 }}
                                >
                                    <Mic className="w-12 h-12 text-muted-foreground" />
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </motion.button>

                    {/* Pulse rings */}
                    <AnimatePresence>
                        {isListening && (
                            <>
                                <motion.div
                                    className="absolute inset-0 rounded-full border-2 border-blue-500/30"
                                    initial={{ scale: 1, opacity: 0.6 }}
                                    animate={{ scale: 1.5, opacity: 0 }}
                                    transition={{
                                        duration: 1.5,
                                        repeat: Infinity,
                                        ease: "easeOut"
                                    }}
                                />
                                <motion.div
                                    className="absolute inset-0 rounded-full border-2 border-blue-500/20"
                                    initial={{ scale: 1, opacity: 0.4 }}
                                    animate={{ scale: 2, opacity: 0 }}
                                    transition={{
                                        duration: 1.5,
                                        repeat: Infinity,
                                        ease: "easeOut",
                                        delay: 0.5
                                    }}
                                />
                            </>
                        )}
                    </AnimatePresence>
                </motion.div>

                {/* Waveform visualizer */}
                <div className="flex items-center justify-center space-x-1 h-16">
                    {waveformData.map((height, index) => (
                        <motion.div
                            key={index}
                            className={cn(
                                "w-1 rounded-full transition-colors duration-300",
                                isListening ? "bg-blue-500" :
                                    isProcessing ? "bg-yellow-500" :
                                        isSpeaking ? "bg-green-500" :
                                            "bg-muted"
                            )}
                            animate={{
                                height: `${Math.max(4, height * 0.6)}px`,
                                opacity: isListening || isSpeaking ? 1 : 0.3
                            }}
                            transition={{
                                duration: 0.1,
                                ease: "easeOut"
                            }}
                        />
                    ))}
                </div>

                {/* Status and timer */}
                <div className="text-center space-y-2">
                    <motion.p
                        className={cn("text-lg font-medium transition-colors", getStatusColor())}
                        animate={{ opacity: [1, 0.7, 1] }}
                        transition={{
                            duration: 2,
                            repeat: isListening || isProcessing || isSpeaking ? Infinity : 0
                        }}
                    >
                        {getStatusText()}
                    </motion.p>

                    <p className="text-sm text-muted-foreground font-mono">
                        {formatTime(duration)}
                    </p>

                    {volume > 0 && (
                        <motion.div
                            className="flex items-center justify-center space-x-2"
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                        >
                            <VolumeX className="w-4 h-4 text-muted-foreground" />
                            <div className="w-24 h-2 bg-muted rounded-full overflow-hidden">
                                <motion.div
                                    className="h-full bg-blue-500 rounded-full"
                                    animate={{ width: `${volume}%` }}
                                    transition={{ duration: 0.1 }}
                                />
                            </div>
                            <Volume2 className="w-4 h-4 text-muted-foreground" />
                        </motion.div>
                    )}
                </div>

                {/* AI indicator */}
                <motion.div
                    className="flex items-center space-x-2 text-sm text-muted-foreground"
                    animate={{ opacity: [0.5, 1, 0.5] }}
                    transition={{
                        duration: 3,
                        repeat: Infinity,
                        ease: "easeInOut"
                    }}
                >
                    <Sparkles className="w-4 h-4" />
                    <span>Gramin Saathi Voice</span>
                </motion.div>
            </div>
        </div>
    );
}
