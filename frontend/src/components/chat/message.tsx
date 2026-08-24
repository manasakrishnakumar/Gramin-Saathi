import { cn } from "@/lib/utils";
import { Bot, User, Sparkles } from "lucide-react";
import { motion } from "framer-motion";
import { memo } from "react";
import { ProcessSteps } from "./process-steps";

interface Step {
    name: string;
    status: "completed" | "in-progress" | "failed" | "success" | "error";
    timestamp: string;
}

export interface MessageProps {
    role: 'user' | 'assistant';
    content: string;
    steps?: Step[];
    source?: string;
    score?: number;
    isLoading?: boolean;
}

const PureMessage = ({ role, content, steps, source, score, isLoading }: MessageProps) => {
    const isUser = role === 'user';

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className={cn(
                "group w-full text-slate-900 border-b border-zinc-100 last:border-0 dark:text-zinc-100 dark:border-zinc-800",
                isUser ? "bg-background" : "bg-muted/30"
            )}
        >
            <div className="flex flex-col gap-4 p-4 md:p-6 max-w-3xl mx-auto w-full">
                <div className="flex gap-4 items-start">
                    <div className={cn(
                        "flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-md border shadow-sm",
                        isUser ? "bg-background" : "bg-primary text-primary-foreground"
                    )}>
                        {isUser ? <User className="h-4 w-4" /> : <Sparkles className="h-4 w-4" />}
                    </div>

                    <div className="flex-1 space-y-2 overflow-hidden">
                        <div className="prose prose-sm md:prose-base dark:prose-invert break-words max-w-none">
                            {/* Render Steps for Assistant */}
                            {!isUser && steps && steps.length > 0 && (
                                <ProcessSteps steps={steps} isLoading={isLoading} />
                            )}

                            {/* Message Content */}
                            {!content && isLoading ? (
                                <span className="text-muted-foreground animate-pulse">Thinking...</span>
                            ) : (
                                <div dangerouslySetInnerHTML={{ __html: content.replace(/\n/g, '<br/>') }} />
                                // Ideally use a Markdown renderer component here
                            )}
                        </div>

                        {/* Source Metadata */}
                        {!isUser && source && !isLoading && (
                            <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
                                <span className="font-medium">Source:</span> {source}
                                {score && <span>({(score * 100).toFixed(0)}% match)</span>}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </motion.div>
    );
};

export const Message = memo(PureMessage);
