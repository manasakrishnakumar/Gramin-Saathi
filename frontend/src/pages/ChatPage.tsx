import { useState, useEffect, useRef, useMemo } from "react";
import ReactMarkdown from 'react-markdown';
import { Send, Plus, MessageSquare, Loader2, Bot, User, ChevronRight, CheckCircle2, ChevronDown, Trash2, Sparkles, AlertTriangle, Database } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useUser } from "@clerk/clerk-react";
import { useLanguage } from "@/contexts/LanguageContext";
import { cn } from "@/lib/utils";
import { AIInputWithLoading } from "@/components/ui/ai-input-with-loading";
import { AnimatePresence, motion } from "framer-motion";
import { Sidebar, SidebarBody, SidebarLink } from "@/components/ui/sidebar";

// Logo Component
const Logo = () => {
    return (
        <a href="#" className="font-normal flex space-x-2 items-center text-sm text-black py-1 relative z-20">
            <Sparkles className="h-6 w-6 text-primary shrink-0" />
            <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="font-medium text-black dark:text-white whitespace-pre"
            >
                Gramin Saathi
            </motion.span>
        </a>
    );
};

const LogoIcon = () => {
    return (
        <a href="#" className="font-normal flex space-x-2 items-center text-sm text-black py-1 relative z-20">
            <Sparkles className="h-6 w-6 text-primary shrink-0" />
        </a>
    );
};

// --- Types ---

interface Step {
    name: string;
    status: "completed" | "in-progress" | "failed" | "success" | "error";
    timestamp: string;
}

interface IntentData {
    intent: string;
    confidence: number;
    method: string;              // "trained_classifier" | "rule_based"
    suggested_action?: string;
    model_version?: string | null;
}

interface GroundednessData {
    grounded_probability: number | null;
    is_likely_grounded?: boolean;
}

interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    steps?: Step[];
    source?: string;
    score?: number;
    intent?: IntentData;
    groundedness?: GroundednessData;
}

interface ChatSession {
    id: string;
    title: string;
    messages: Message[];
    updatedAt: number;
}



const LANGUAGE_MAP: Record<string, string> = {
    en: "English", hi: "Hindi", ta: "Tamil", te: "Telugu", kn: "Kannada",
    ml: "Malayalam", gu: "Gujarati", mr: "Marathi", bn: "Bengali", pa: "Punjabi"
};

// --- Components ---

// Maps specific step names to badge metadata for hybrid RAG pipeline steps
const HYBRID_STEP_META: Record<string, { label: string; color: string }> = {
    "Hybrid Retrieval (Dense + BM25 + Re-rank)": { label: "Hybrid RAG", color: "text-violet-400 bg-violet-500/10 border-violet-500/20" },
    "Analyzing Documents (RAG)":                 { label: "Retrieval",  color: "text-blue-400 bg-blue-500/10 border-blue-500/20" },
    "Querying Hybrid RAG System":                { label: "RAG",        color: "text-violet-400 bg-violet-500/10 border-violet-500/20" },
};

const ProcessSteps = ({ steps }: { steps: Step[] }) => {
    const [isOpen, setIsOpen] = useState(true);

    if (!steps || steps.length === 0) return null;

    const isHybridPipeline = steps.some(s =>
        s.name.includes("Hybrid") || s.name.includes("BM25") || s.name.includes("Cross-Encoder")
    );

    return (
        <div className={cn("mb-4 rounded-lg border p-3 text-sm", isHybridPipeline ? "bg-violet-500/5 border-violet-500/20" : "bg-muted/30")}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="flex w-full items-center justify-between text-muted-foreground hover:text-foreground mb-2"
            >
                <span className="font-medium text-xs uppercase tracking-wide flex items-center gap-2">
                    <Loader2 className="h-3 w-3 animate-spin duration-[3s]" />
                    {isHybridPipeline ? "Hybrid RAG Pipeline" : "Thinking Process"}
                    {isHybridPipeline && (
                        <span className="text-[10px] bg-violet-500/15 text-violet-400 border border-violet-500/20 px-1.5 py-0.5 rounded-full font-semibold normal-case tracking-normal">
                            Dense + BM25 + Re-rank
                        </span>
                    )}
                </span>
                {isOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            </button>

            {isOpen && (
                <div className="space-y-3 pl-1 pt-1 animate-in fade-in slide-in-from-top-2">
                    {steps.map((step, idx) => {
                        const hybridMeta = HYBRID_STEP_META[step.name];
                        return (
                            <div key={idx} className="flex items-start gap-3">
                                {step.status === 'completed' || step.status === 'success' ? (
                                    <CheckCircle2 className="h-4 w-4 text-green-500 mt-0.5 shrink-0" />
                                ) : step.status === 'failed' || step.status === 'error' ? (
                                    <div className="h-4 w-4 rounded-full border-2 border-red-500 bg-red-500/20 mt-0.5 shrink-0" />
                                ) : (
                                    <div className="h-4 w-4 rounded-full border-2 border-primary border-t-transparent animate-spin mt-0.5 shrink-0" />
                                )}
                                <div className="flex flex-col gap-0.5">
                                    <span className={cn("text-sm", step.status === 'error' ? "text-red-500" : "text-foreground/80")}>
                                        {step.name}
                                    </span>
                                    {hybridMeta && (
                                        <span className={cn("text-[10px] px-1.5 py-0.5 rounded-full border w-fit font-semibold", hybridMeta.color)}>
                                            {hybridMeta.label}
                                        </span>
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
};

// Shows what the trained intent classifier (ml/train_intent_classifier.py)
// read this message as — proves the trained model, not just the rule-based
// fallback, is actually driving this. See backend/ml/README.md.
const IntentBadge = ({ intent }: { intent: IntentData }) => {
    const isTrained = intent.method === "trained_classifier";
    const label = intent.intent.replace(/_/g, " ");
    return (
        <div
            className={cn(
                "flex items-center gap-1.5 text-[10px] px-2 py-1 rounded-full border w-fit font-medium",
                isTrained
                    ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
                    : "text-muted-foreground bg-muted/30 border-border"
            )}
            title={isTrained ? `Trained ML classifier (model ${intent.model_version ?? "?"})` : "Rule-based fallback"}
        >
            <Sparkles className="h-2.5 w-2.5" />
            {isTrained ? "ML" : "rule"} · {label} ({Math.round(intent.confidence * 100)}%)
        </div>
    );
};

// Trained groundedness classifier's read on this answer (ml/train_groundedness_classifier.py).
// Deliberately soft: only shows below a conservative confidence threshold,
// and phrased as a suggestion, not a claim the answer is wrong — the
// classifier has a known false-positive tendency on heavily-reworded but
// correct paraphrases (see ml_groundedness_service.py docstring), so a
// louder/more confident UI treatment than this would be misleading.
const GROUNDEDNESS_NUDGE_THRESHOLD = 0.15;

const GroundednessNote = ({ groundedness }: { groundedness: GroundednessData }) => {
    if (groundedness.grounded_probability === null || groundedness.grounded_probability === undefined) return null;
    if (groundedness.grounded_probability >= GROUNDEDNESS_NUDGE_THRESHOLD) return null;
    return (
        <div
            className="flex items-center gap-1.5 text-[10px] px-2 py-1 rounded-full border w-fit font-medium text-amber-400 bg-amber-500/10 border-amber-500/20"
            title="Trained ML classifier — experimental signal, may have false positives on heavily reworded answers"
        >
            <AlertTriangle className="h-2.5 w-2.5" /> ML: consider verifying with the official source
        </div>
    );
};

export default function ChatPage() {
    const { user, isLoaded } = useUser();
    const { language } = useLanguage();
    const [sessions, setSessions] = useState<ChatSession[]>([]);
    const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
    const [open, setOpen] = useState(false);
    const [messages, setMessages] = useState<any[]>([]);
    const [input, setInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [currentSteps, setCurrentSteps] = useState<any[]>([]);
    const [detectedLanguage, setDetectedLanguage] = useState<string | null>(null);
    const scrollRef = useRef<HTMLDivElement>(null);
    // Track currently playing streaming audio so it can be stopped
    const streamAudioRef = useRef<HTMLAudioElement | null>(null);
    const [isStreamingAudio, setIsStreamingAudio] = useState(false);

    // --- Persistence ---

    // Key depends on user ID. If not logged in, use 'guest'.
    // We prefix with 'chat_sessions_' 
    const storageKey = useMemo(() => {
        if (!isLoaded) return null; // Wait for load
        return user ? `chat_sessions_${user.id}` : `chat_sessions_guest`;
    }, [user, isLoaded]);

    useEffect(() => {
        if (!storageKey) return;

        // Load sessions from local storage for the specific user
        const saved = localStorage.getItem(storageKey);
        if (saved) {
            try {
                const parsed = JSON.parse(saved);
                setSessions(parsed);
                // Reset current session on user switch if valid
                // But don't auto-select to keep "Welcome" screen? 
                // Issue: If we switch user, we might want to clear currentSessionId if it's not in the new list.
                // We'll handle that in the dependency change.
            } catch (e) {
                console.error("Failed to parse sessions", e);
                setSessions([]);
            }
        } else {
            setSessions([]);
        }

        // When user changes, we should ensure we don't hold onto old session ID
        setCurrentSessionId(null);

    }, [storageKey]); // Re-run when user changes

    useEffect(() => {
        if (!storageKey) return;
        // Save sessions
        localStorage.setItem(storageKey, JSON.stringify(sessions));
    }, [sessions, storageKey]);

    useEffect(() => {
        // `messages` must be a dependency too, not just `sessions` — sessions
        // only gets updated once at the end of a streamed response, so
        // without this the view wouldn't auto-scroll while tokens are
        // streaming in, only once the full answer finishes.
        scrollRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [currentSessionId, sessions, messages]);

    // --- Actions ---

    const createNewChat = () => {
        const newSession: ChatSession = {
            id: crypto.randomUUID(),
            title: "New Chat",
            messages: [],
            updatedAt: Date.now()
        };
        setSessions(prev => [newSession, ...prev]);
        setCurrentSessionId(newSession.id);
        return newSession.id;
    };

    const deleteChat = (e: React.MouseEvent, id: string) => {
        e.stopPropagation();
        setSessions(prev => prev.filter(s => s.id !== id));
        if (currentSessionId === id) setCurrentSessionId(null);
    };

    const activeSession = sessions.find(s => s.id === currentSessionId);

    useEffect(() => {
        if (activeSession) {
            setMessages(activeSession.messages || []);
        } else {
            setMessages([]);
        }
    }, [activeSession]);

    // Detect location and language on mount
    useEffect(() => {
        const fetchLocation = async () => {
            // Only auto-detect if not already set manually? 
            // Requirement says "based on location... final prompt response should have both"
            // This implies auto-detection should drive the secondary language.
            import("@/services/geolocation").then(async (module) => {
                const lang = await module.detectLocationAndLanguage();
                if (lang) {
                    console.log("Detected Language:", lang);
                    setDetectedLanguage(lang);
                }
            });
        };
        fetchLocation();
    }, []);

    const handleSendLegacy = async () => {
        if (!input?.trim() || isLoading) return;

        let activeId = currentSessionId;
        if (!activeId) {
            activeId = createNewChat();
        }

        const userMessage = { id: Date.now().toString(), role: 'user', content: input };
        const newMessages = [...messages, userMessage];

        setMessages(newMessages);
        setInput("");
        setIsLoading(true);
        setCurrentSteps([]);

        try {
            // Determine target language: use detected if available, else context language (which defaults to English/Hindi?)
            // Actually, if detectedLanguage is present, backend will do English + Detected.
            // If not, we might fall back to English-only or whatever context says.

            const targetLang = detectedLanguage || LANGUAGE_MAP[language] || "English";

            const response = await fetch('/api/v1/rag/stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query: userMessage.content,
                    target_language: targetLang,
                    history: messages.map(m => ({ role: m.role, content: m.content }))
                })
            });

            if (!response.ok) throw new Error(response.statusText);
            if (!response.body) throw new Error("No response body");

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            // Create placeholder for assistant message
            const assistantId = (Date.now() + 1).toString();
            let assistantContent = "";
            let assistantSteps: any[] = [];
            let assistantIntent: IntentData | undefined = undefined;
            let assistantGroundedness: GroundednessData | undefined = undefined;

            setMessages(prev => [...prev, { id: assistantId, role: 'assistant', content: "", steps: [] }]);

            // Audio playback helper — tracks audio so it can be stopped
            const playAudio = (audioBase64: string): Promise<void> => {
                return new Promise((resolve) => {
                    const audioFormats = ['audio/mpeg', 'audio/wav', 'audio/mp3'];

                    const tryFormat = (index: number) => {
                        if (index >= audioFormats.length) {
                            setIsStreamingAudio(false);
                            resolve();
                            return;
                        }

                        const format = audioFormats[index];
                        const audio = new Audio(`data:${format};base64,${audioBase64}`);
                        streamAudioRef.current = audio;
                        setIsStreamingAudio(true);

                        audio.onended = () => {
                            streamAudioRef.current = null;
                            setIsStreamingAudio(false);
                            resolve();
                        };

                        audio.onerror = () => tryFormat(index + 1);

                        audio.play().catch(() => tryFormat(index + 1));
                    };

                    tryFormat(0);
                });
            };

            // Handles one decoded NDJSON line: updates local accumulators + UI state.
            const processLine = async (line: string) => {
                if (!line.trim()) return;
                try {
                    const data = JSON.parse(line);

                    if (data.type === 'token') {
                        assistantContent += data.content;
                    } else if (data.type === 'step') {
                        assistantSteps = data.data;
                        setCurrentSteps(assistantSteps);
                    } else if (data.type === 'intent') {
                        // Emitted by rag_service.py — the trained intent classifier's
                        // read on this turn (ml/train_intent_classifier.py, 95.3% held-out
                        // accuracy), falls back to rule-based only if that model didn't load.
                        assistantIntent = data.data;
                    } else if (data.type === 'groundedness') {
                        // Trained classifier's read on whether this answer is
                        // supported by its retrieved context. Soft signal —
                        // see ml_groundedness_service.py's documented
                        // false-positive limitation on heavy paraphrasing —
                        // so the UI only nudges on a low-confidence score,
                        // never a hard "this is wrong" claim.
                        assistantGroundedness = data.data;
                    } else if (data.type === 'error') {
                        console.error("Stream error:", data.content);
                    } else if (data.type === 'audio') {
                        // Play audio response (English first, then native)
                        console.log("Received audio data from stream");
                        if (data.audio) {
                            console.log("Playing English audio...");
                            await playAudio(data.audio);
                        }
                        if (data.audio_native) {
                            console.log("Playing native language audio...");
                            await playAudio(data.audio_native);
                        }
                    }

                    // Update UI
                    setMessages(prev => prev.map(m =>
                        m.id === assistantId
                            ? { ...m, content: assistantContent, steps: assistantSteps, intent: assistantIntent, groundedness: assistantGroundedness }
                            : m
                    ));

                } catch (e) {
                    console.warn("Failed to parse JSON line:", line);
                }
            };

            // NOTE: a single NDJSON line can be split across two reader.read()
            // chunks (chunk boundaries don't align with newlines). `buffer`
            // carries any trailing incomplete line over to the next read so we
            // never JSON.parse a half-received line and silently drop it.
            let buffer = "";
            while (true) {
                const { done, value } = await reader.read();
                if (done) {
                    if (buffer.trim()) await processLine(buffer);
                    break;
                }

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() ?? ""; // last segment may be incomplete — hold it back

                for (const line of lines) {
                    await processLine(line);
                }
            }

            // Sync with session storage
            if (activeId) {
                setSessions(prev => prev.map(s => {
                    if (s.id === activeId) {
                        // Rename if it's the first message (or title is default)
                        let newTitle = s.title;
                        if (s.messages.length === 0 || s.title === "New Chat") {
                            newTitle = userMessage.content.slice(0, 30) + (userMessage.content.length > 30 ? "..." : "");
                        }

                        return {
                            ...s,
                            title: newTitle,
                            messages: [...newMessages, { id: assistantId, role: 'assistant', content: assistantContent, steps: assistantSteps, intent: assistantIntent, groundedness: assistantGroundedness }],
                            updatedAt: Date.now()
                        };
                    }
                    return s;
                }));
            }

        } catch (error) {
            console.error("Failed to send message:", error);
            // Optionally add error message to chat
        } finally {
            setIsLoading(false);
        }
    };

    // Removed useEffect for syncing hook messages since we manage state manually now


    // Callback for Voice Chat
    const handleVoiceConversation = (userText: string, botText: string) => {
        let activeId = currentSessionId;
        if (!activeId) {
            activeId = createNewChat();
        }

        // Add User Message
        const userMsg: Message = { id: Date.now().toString(), role: 'user' as const, content: userText };

        // Add Bot Message
        const botMsg: Message = { id: (Date.now() + 1).toString(), role: 'assistant' as const, content: botText, steps: [] };

        const newMessages = [...messages, userMsg, botMsg];
        setMessages(newMessages);

        // Sync to Sessions
        if (activeId) {
            setSessions(prev => prev.map(s => {
                if (s.id === activeId) {
                    // Update Title if needed
                    let newTitle = s.title;
                    if (s.messages.length === 0 || s.title === "New Chat") {
                        newTitle = userText.slice(0, 30) + (userText.length > 30 ? "..." : "");
                    }
                    return {
                        ...s,
                        title: newTitle,
                        messages: [...s.messages, userMsg, botMsg],
                        updatedAt: Date.now()
                    };
                }
                return s;
            }));
        }
    };

    // Use session messages for rendering to support 'steps', but prefer hook messages for current stream?
    // Casting to any allows us to read mismatched props without error
    const displayMessages = messages as any[];

    return (
        <div key={currentSessionId} className="flex h-[calc(100vh-4rem)] w-full overflow-hidden bg-background">
            {/* New Aceternity Style Sidebar */}
            <Sidebar open={open} setOpen={setOpen}>
                <SidebarBody className="justify-between gap-10">
                    <div className="flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
                        {open ? <Logo /> : <LogoIcon />}
                        <div className="mt-8 flex flex-col gap-2">
                            <Button
                                onClick={createNewChat}
                                variant="outline"
                                className={cn("w-full justify-start gap-2 mb-4", !open && "px-2 justify-center")}
                            >
                                <Plus className="h-4 w-4" />
                                {open && "New Chat"}
                            </Button>

                            {sessions.map((session) => (
                                <SidebarLink
                                    key={session.id}
                                    link={{
                                        label: session.title,
                                        href: "#",
                                        icon: <MessageSquare className="h-4 w-4 shrink-0 text-neutral-700 dark:text-neutral-200" />
                                    }}
                                    action={
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="h-5 w-5 opacity-0 group-hover/sidebar:opacity-100"
                                            onClick={(e) => deleteChat(e, session.id)}
                                        >
                                            <Trash2 className="h-3 w-3 text-muted-foreground" />
                                        </Button>
                                    }
                                    onClick={() => {
                                        setCurrentSessionId(session.id);
                                        // On mobile, close sidebar on selection? Optional.
                                        // setOpen(false); 
                                    }}
                                    className={cn(currentSessionId === session.id && "bg-neutral-100 dark:bg-neutral-800 rounded-md")}
                                />
                            ))}
                        </div>
                    </div>
                </SidebarBody>
            </Sidebar>

            {/* Main Chat Area */}
            <div className="flex-1 flex flex-col relative bg-background/50">

                {/* Chat Header */}
                <div className="flex items-center justify-between p-4 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-10">
                    <div className="flex items-center gap-2">
                        <Sparkles className="h-5 w-5 text-primary animate-pulse" />
                        <h2 className="font-semibold text-lg bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
                            Gramin Saathi
                        </h2>
                    </div>
                </div>

                {!activeSession ? (
                    <div className="flex-1 flex items-center justify-center flex-col gap-4 text-center p-8">
                        <div className="rounded-full bg-primary/10 p-6">
                            <Bot className="h-12 w-12 text-primary" />
                        </div>
                        <h2 className="text-2xl font-bold">Welcome to Gramin Saathi</h2>
                        <p className="text-muted-foreground max-w-md">
                            Select a chat from the sidebar or start a new conversation to ask about government schemes.
                        </p>
                        <Button onClick={createNewChat}>Start New Conversation</Button>
                    </div>
                ) : (
                    <>
                        <div className="flex-1 p-4 md:p-8 overflow-y-auto mb-20 scroll-smooth">
                            <div className="max-w-3xl mx-auto space-y-6">
                                {displayMessages.map((msg, idx) => (
                                    <div key={msg.id} className={cn("flex gap-4", msg.role === 'user' ? "justify-end" : "justify-start")}>
                                        {msg.role === 'assistant' && (
                                            <div className="mt-1 h-8 w-8 shrink-0 rounded-full bg-primary/10 flex items-center justify-center">
                                                <Bot className="h-5 w-5 text-primary" />
                                            </div>
                                        )}

                                        <div className={cn("flex flex-col gap-2 max-w-[85%]", msg.role === 'user' && "items-end")}>
                                            {msg.role === 'user' && (
                                                <div className="rounded-2xl px-4 py-3 bg-primary text-primary-foreground shadow-sm">
                                                    {msg.content}
                                                </div>
                                            )}

                                            {msg.role === 'assistant' && (
                                                <>
                                                    {(idx === displayMessages.length - 1 && isLoading && currentSteps.length > 0) ? (
                                                        <ProcessSteps steps={currentSteps} />
                                                    ) : msg.steps && msg.steps.length > 0 && (
                                                        <ProcessSteps steps={msg.steps} />
                                                    )}

                                                    <div className="rounded-2xl rounded-tl-none px-4 py-3 bg-card border shadow-sm prose dark:prose-invert prose-sm max-w-none">
                                                        <ReactMarkdown>{msg.content}</ReactMarkdown>
                                                    </div>

                                                    <div className="flex items-center gap-2 flex-wrap mt-1">
                                                        {/* RAG Source Badge */}
                                                        <div
                                                            className="flex items-center gap-1.5 text-[10px] px-2 py-1 rounded-full border w-fit font-medium text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
                                                            title="Response generated from RAG (Retrieval-Augmented Generation) using the scheme knowledge base"
                                                        >
                                                            <Database className="h-2.5 w-2.5" />
                                                            RAG · Scheme Knowledge Base
                                                        </div>
                                                        {msg.intent && <IntentBadge intent={msg.intent} />}
                                                        {msg.groundedness && false /* yellow badge removed */}
                                                    </div>
                                                </>
                                            )}
                                        </div>

                                        {msg.role === 'user' && (
                                            <div className="mt-1 h-8 w-8 shrink-0 rounded-full bg-accent flex items-center justify-center text-accent-foreground">
                                                <User className="h-5 w-5" />
                                            </div>
                                        )}
                                    </div>
                                ))}
                                <div ref={scrollRef} />
                            </div>
                        </div>

                        {/* Input Area */}
                        <div className="p-4 border-t bg-background mt-auto absolute bottom-0 left-0 right-0 z-10">
                            <div className="max-w-3xl mx-auto flex flex-col gap-2">
                                <AIInputWithLoading
                                    value={input}
                                    onChange={setInput}
                                    onSubmit={handleSendLegacy}
                                    onVoiceMessage={handleVoiceConversation}
                                    loading={isLoading}
                                    placeholder="Ask about a government scheme..."
                                    disabled={isLoading}
                                    externalIsPlayingAudio={isStreamingAudio}
                                    onExternalStop={() => {
                                        if (streamAudioRef.current) {
                                            streamAudioRef.current.pause();
                                            streamAudioRef.current.currentTime = 0;
                                            streamAudioRef.current = null;
                                        }
                                        setIsStreamingAudio(false);
                                    }}
                                />

                                <div className="text-center">
                                    <span className="text-xs text-muted-foreground">
                                        Language: {LANGUAGE_MAP[language] || language}
                                    </span>
                                </div>
                            </div>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}
