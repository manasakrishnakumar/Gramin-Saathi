import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { ArrowRight, Sparkles } from "lucide-react";
import { ParticlesBackground } from "@/components/ParticlesBackground";

interface HeroProps {
  onChatOpen: () => void;
}

const languagePhrases = [
  "Gramin Saathi",
  "ಗ್ರಾಮಿಣ ಸಾಥಿ",
  "గ్రామిన్ సాథి",
  "கிராமின் சாத்தி",
  "ग्रामीण साथी",
  "ग्रामीण साथी", // Marathi uses same script/text
];

export const Hero = ({ onChatOpen }: HeroProps) => {
  const phrases = useMemo(() => languagePhrases, []);
  const [displayedText, setDisplayedText] = useState("");
  const [languageIndex, setLanguageIndex] = useState(0);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isFading, setIsFading] = useState(true);

  useEffect(() => {
    setIsFading(true);
    const fadeTimer = setTimeout(() => setIsFading(false), 250);
    return () => clearTimeout(fadeTimer);
  }, [languageIndex]);

  useEffect(() => {
    const currentPhrase = phrases[languageIndex];
    const hasCompleted = displayedText === currentPhrase;
    const hasErased = displayedText === "";

    if (!isDeleting && hasCompleted) {
      const pauseTimer = setTimeout(() => setIsDeleting(true), 1200);
      return () => clearTimeout(pauseTimer);
    }

    if (isDeleting && hasErased) {
      setIsDeleting(false);
      setLanguageIndex((prev) => (prev + 1) % phrases.length);
      return;
    }

    const baseSpeed = isDeleting ? 60 : 85;
    const variance = Math.random() * 20;
    const typingDelay = baseSpeed + variance;

    const typingTimer = setTimeout(() => {
      const nextLength = displayedText.length + (isDeleting ? -1 : 1);
      setDisplayedText(currentPhrase.slice(0, nextLength));
    }, typingDelay);

    return () => clearTimeout(typingTimer);
  }, [displayedText, isDeleting, languageIndex, phrases]);

  return (
    <section className="relative isolate overflow-hidden bg-transparent">
      <div className="absolute inset-0">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(45,80,22,0.12),_transparent_55%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom,_rgba(74,144,226,0.08),_transparent_60%)]" />
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-white/40 dark:to-black/30" />
        <div className="absolute inset-0 bg-[linear-gradient(120deg,rgba(255,255,255,0.08),transparent_30%,transparent_70%,rgba(255,255,255,0.08))] opacity-40 dark:opacity-20" />
      </div>

      <div className="relative z-10 mx-auto flex min-h-screen max-w-5xl flex-col items-center justify-center gap-10 px-6 py-24 text-center">
        <div className="inline-flex items-center gap-2 rounded-full border border-white/50 bg-white/40 px-4 py-2 text-xs font-semibold uppercase tracking-[0.3em] text-[#2D5016] shadow-[0_15px_45px_rgba(45,80,22,0.15)] dark:border-white/10 dark:bg-white/10 dark:text-white">
          <Sparkles className="h-4 w-4 text-[#FF9933]" />
          AI-powered rural platform
        </div>

        <div className="space-y-6">
          <p
            className={`hero-typing text-4xl font-bold leading-tight transition-all duration-500 sm:text-5xl lg:text-6xl ${
              isFading ? "opacity-0 translate-y-2" : "opacity-100 translate-y-0"
            }`}
          >
            <span className="hero-typing__text gradient-text text-transparent">{displayedText}</span>
          </p>

          <p className="text-base leading-relaxed text-slate-600 md:text-lg dark:text-slate-300">
            Empowering Rural Communities Through Intelligent Conversation. Connect with instant support for government
            schemes, agriculture guidance, local services, and community resources. Get answers in your language,
            anytime.
          </p>
        </div>

        <div className="flex flex-col gap-4 sm:flex-row">
          <Button
            size="lg"
            onClick={onChatOpen}
            className="group flex items-center justify-center gap-3 rounded-2xl border border-transparent bg-[#25D366] px-10 py-5 text-base font-semibold text-white shadow-[0_25px_80px_rgba(37,211,102,0.35)] transition hover:-translate-y-0.5 hover:bg-[#20b758] hover:shadow-[0_35px_90px_rgba(37,211,102,0.45)]"
          >
            Start Chat
            <span className="flex h-8 w-8 items-center justify-center rounded-full border border-white/40 bg-white/20 text-white transition group-hover:translate-x-1">
              <ArrowRight className="h-4 w-4" />
            </span>
          </Button>
          <Button
            size="lg"
            variant="ghost"
            className="rounded-2xl border border-[#2D5016]/20 bg-white/80 px-10 py-5 text-base font-semibold text-[#2D5016] shadow-[0_20px_70px_rgba(32,80,30,0.2)] backdrop-blur-2xl transition hover:-translate-y-0.5 hover:bg-white dark:border-white/15 dark:bg-white/10 dark:text-white"
            asChild
          >
            <a href="#features">Explore Features</a>
          </Button>
        </div>
      </div>
    </section>
  );
};
