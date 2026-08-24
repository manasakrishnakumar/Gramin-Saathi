import { useState, useEffect } from "react";
import { CheckCircle2, ChevronDown, ChevronRight, Loader2, Circle, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";

interface Step {
    name: string;
    status: "completed" | "in-progress" | "failed" | "success" | "error";
    timestamp: string;
}

interface ProcessStepsProps {
    steps: Step[];
    isLoading?: boolean;
}

export function ProcessSteps({ steps, isLoading }: ProcessStepsProps) {
    const [isOpen, setIsOpen] = useState(true);
    const [visibleSteps, setVisibleSteps] = useState<Step[]>([]);

    useEffect(() => {
        if (!steps || steps.length === 0) {
            setVisibleSteps([]);
            return;
        }

        // Logic to simulate "streaming" or "processing" one by one
        // If we are loading or just received full data, we replay the sequence.

        // We will store just the *index* of the current "processing" step.
        // Steps before index are "completed".
        // Step at index is "in-progress".
        // Steps after index are not visible.

        let currentIdx = 0;

        // Initial state: nothing visible
        setVisibleSteps([]);

        const interval = setInterval(() => {
            if (currentIdx < steps.length) {
                // Show steps up to currentIdx
                const newVisible = steps.slice(0, currentIdx + 1).map((s, i) => {
                    // IF it's the last one we are revealing, make it 'in-progress' momentarily
                    // UNLESS it's the very last step and isLoading is false (meaning whole thing done)
                    // actually, we want the visual "process", so let's force the last revealed item to be 'in-progress'
                    // for a tick, then 'completed' in next tick?

                    // Simple approach: active step is 'in-progress'.
                    // BUT, this interval is adding new steps. 
                    // Let's make the "active" one the one we just added.

                    if (i === currentIdx) {
                        return { ...s, status: i === steps.length - 1 && !isLoading ? s.status : 'in-progress' } as Step;
                        // If it's the absolute last step and we are done, show real status. 
                        // Otherwise (intermediate steps), show in-progress.
                    }
                    return { ...s, status: 'completed' } as Step; // Previous are active
                });

                setVisibleSteps(newVisible);
                currentIdx++;
            } else {
                // All visible. Ensure all are marked completed (or original status)
                setVisibleSteps(steps);
                clearInterval(interval);
            }
        }, 500); // 500ms per step

        return () => clearInterval(interval);

    }, [steps, isLoading]);

    if (!steps || steps.length === 0) return null;

    return (
        <div className="mb-4 rounded-xl border bg-muted/50 p-3 text-sm">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="flex w-full items-center gap-3 bg-transparent p-2 text-sm font-medium transition-colors hover:bg-muted/80 rounded-lg text-muted-foreground"
            >
                <div className="flex bg-background border rounded-md p-1 shadow-sm">
                    {/* Show Spinner if we haven't shown all steps or parent says loading */}
                    {visibleSteps.length < steps.length || isLoading ? (
                        <Loader2 className="h-4 w-4 animate-spin text-primary" />
                    ) : (
                        <CheckCircle2 className="h-4 w-4 text-primary" />
                    )}
                </div>
                <span className="flex-1 text-left">
                    {visibleSteps.length < steps.length || isLoading ? "Thinking..." : "Finished Processing"}
                </span>
                {isOpen ? <ChevronDown className="h-4 w-4 text-muted-foreground" /> : <ChevronRight className="h-4 w-4 text-muted-foreground" />}
            </button>

            <AnimatePresence mode="wait">
                {isOpen && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="px-4 py-3 space-y-4 bg-background/50 border-t"
                    >
                        {visibleSteps.map((step, idx) => (
                            <motion.div
                                key={`${step.name}-${idx}`}
                                initial={{ opacity: 0, x: -10 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ duration: 0.3 }}
                                className="flex items-center gap-3 text-sm"
                            >
                                {step.status === 'completed' || step.status === 'success' ? (
                                    <CheckCircle2 className="h-4 w-4 text-primary shrink-0" />
                                ) : step.status === 'failed' || step.status === 'error' ? (
                                    <XCircle className="h-4 w-4 text-red-500 shrink-0" />
                                ) : (
                                    <Loader2 className="h-4 w-4 animate-spin text-primary shrink-0" />
                                )}
                                <span className={cn(
                                    step.status === 'in-progress' ? "text-foreground font-medium animate-pulse" : "text-muted-foreground",
                                    (step.status === 'failed' || step.status === 'error') && "text-red-500"
                                )}>
                                    {step.name}
                                </span>
                            </motion.div>
                        ))}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
