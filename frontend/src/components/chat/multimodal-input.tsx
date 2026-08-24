import { useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea"; // Assuming you have this, otherwise standard textarea
import { ArrowUp, Loader2, Paperclip, Mic } from "lucide-react";
import { cn } from "@/lib/utils";

interface MultimodalInputProps {
    value: string;
    onChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
    onSubmit: () => void;
    isLoading: boolean;
    placeholder?: string;
}

export function MultimodalInput({ value, onChange, onSubmit, isLoading, placeholder }: MultimodalInputProps) {
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    // Auto-resize
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto'; // Reset
            textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
        }
    }, [value]);

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            onSubmit();
        }
    };

    return (
        <div className="relative w-full max-w-3xl mx-auto p-4 bg-transparent">
            <div className="relative flex items-end w-full p-3 bg-muted/40 border rounded-xl shadow-sm focus-within:ring-1 focus-within:ring-primary/20 focus-within:border-primary/50 transition-all">

                {/* File Attachment Button (Placeholder) */}
                <Button variant="ghost" size="icon" className="h-8 w-8 rounded-lg text-muted-foreground mr-2 shrink-0" disabled>
                    <Paperclip className="h-5 w-5" />
                </Button>

                <textarea
                    ref={textareaRef}
                    value={value}
                    onChange={onChange}
                    onKeyDown={handleKeyDown}
                    placeholder={placeholder || "Information about scholarships..."}
                    className="flex-1 w-full bg-transparent border-0 resize-none focus:ring-0 p-1 min-h-[44px] max-h-[200px] text-base scrollbar-hide focus-visible:outline-none"
                    rows={1}
                    disabled={isLoading}
                />

                {/* Voice Input Button (Placeholder) */}
                {/* <Button variant="ghost" size="icon" className="h-8 w-8 rounded-lg text-muted-foreground ml-2 shrink-0">
                    <Mic className="h-5 w-5" />
                </Button> */}

                <Button
                    onClick={onSubmit}
                    disabled={!value.trim() || isLoading}
                    size="icon"
                    className={cn(
                        "h-8 w-8 rounded-lg ml-2 shrink-0 transition-all text-primary-foreground shadow-sm hover:shadow-md",
                        value.trim() ? "opacity-100 bg-primary hover:bg-primary/90" : "opacity-50 bg-muted"
                    )}
                >
                    {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowUp className="h-4 w-4" />}
                </Button>
            </div>

            <div className="text-center mt-2 text-xs text-muted-foreground">
                AI can make mistakes. Check for accuracy.
            </div>
        </div>
    );
}
