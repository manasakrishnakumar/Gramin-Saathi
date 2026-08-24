import { Button } from "@/components/ui/button";
import { MessageCircle } from "lucide-react";

interface ChatbotTriggerProps {
  onClick: () => void;
}

export const ChatbotTrigger = ({ onClick }: ChatbotTriggerProps) => {
  return (
    <Button
      onClick={onClick}
      size="lg"
      className="fixed bottom-6 right-6 z-40 w-16 h-16 rounded-full bg-primary hover:bg-primary/90 text-primary-foreground shadow-2xl hover:shadow-xl transition-all animate-scale-in group"
      style={{ boxShadow: "0 0 40px rgba(16, 185, 129, 0.3)" }}
    >
      <MessageCircle className="w-7 h-7 group-hover:scale-110 transition-transform" />
      <span className="absolute -top-1 -right-1 w-4 h-4 bg-accent rounded-full animate-pulse" />
    </Button>
  );
};
