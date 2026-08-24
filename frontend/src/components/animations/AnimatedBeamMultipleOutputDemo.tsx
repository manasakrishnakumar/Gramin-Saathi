import { Database, Network, Radio, Send, Share2, Smartphone } from "lucide-react";

import { cn } from "@/lib/utils";

type AnimatedBeamMultipleOutputDemoProps = {
  className?: string;
};

const beams = [
  "M200 140 C 140 110 110 70 60 80",
  "M200 140 C 260 110 300 70 340 80",
  "M200 140 C 150 160 110 210 80 220",
  "M200 140 C 240 170 300 210 340 220",
];

const outputs = [
  {
    label: "Village Apps",
    icon: Smartphone,
    style: "top-[5%] left-[8%]",
  },
  {
    label: "District Cloud",
    icon: Database,
    style: "top-[8%] right-[8%]",
  },
  {
    label: "Community Radio",
    icon: Radio,
    style: "bottom-[8%] left-[12%]",
  },
  {
    label: "Partner APIs",
    icon: Network,
    style: "bottom-[10%] right-[10%]",
  },
];

export const AnimatedBeamMultipleOutputDemo = ({
  className,
}: AnimatedBeamMultipleOutputDemoProps) => {
  return (
    <div
      className={cn(
        "relative flex h-full w-full items-center justify-center overflow-hidden rounded-3xl border border-border/60 bg-gradient-to-br from-primary/5 via-background to-background shadow-inner shadow-black/10",
        className,
      )}
    >
      <svg
        viewBox="0 0 400 260"
        className="pointer-events-none absolute inset-0 h-full w-full opacity-80"
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          <linearGradient id="beamGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="hsl(158 64% 52%)" stopOpacity="0" />
            <stop offset="40%" stopColor="hsl(158 64% 52%)" stopOpacity="0.8" />
            <stop offset="100%" stopColor="hsl(25 95% 53%)" stopOpacity="0" />
          </linearGradient>
          <filter id="glow">
            <feGaussianBlur stdDeviation="4" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {beams.map((path, index) => (
          <path
            key={path}
            d={path}
            stroke="url(#beamGradient)"
            strokeWidth="3"
            fill="none"
            strokeLinecap="round"
            strokeDasharray="12 10"
            className="beam-path"
            style={{ animationDelay: `${index * 0.4}s` }}
            filter="url(#glow)"
          />
        ))}
      </svg>

      <div className="relative z-10 flex flex-col items-center gap-2">
        <span className="inline-flex h-16 w-16 items-center justify-center rounded-full border border-primary/40 bg-primary/10 text-primary shadow-[0_0_40px_rgba(16,185,129,0.4)]">
          <Share2 className="h-6 w-6" />
        </span>
        <p className="text-sm font-semibold text-muted-foreground">AI Coordination Hub</p>
      </div>

      {outputs.map(({ label, icon: Icon, style }) => (
        <div
          key={label}
          className={cn(
            "absolute flex flex-col items-center gap-2 rounded-2xl bg-background/90 px-4 py-2 text-xs font-medium text-muted-foreground shadow-lg shadow-black/10",
            style,
          )}
        >
          <span className="relative flex h-10 w-10 items-center justify-center rounded-full border border-border/50 bg-card/80 text-primary">
            <Icon className="h-4 w-4" />
            <span className="absolute inset-[-6px] rounded-full border border-primary/30 opacity-0 blur-lg transition duration-700 group-hover:opacity-100" />
          </span>
          {label}
        </div>
      ))}

      <div className="absolute bottom-[32%] left-1/2 flex -translate-x-1/2 translate-y-1/2 gap-4 text-xs font-semibold text-muted-foreground">
        <div className="flex items-center gap-2 rounded-full bg-primary/10 px-4 py-1">
          <Send className="h-4 w-4 text-primary" />
          Instant Sync
        </div>
        <div className="flex items-center gap-2 rounded-full bg-amber-100/60 px-4 py-1 text-amber-800 dark:bg-amber-500/10 dark:text-amber-100">
          <Share2 className="h-4 w-4" />
          Multi-output
        </div>
      </div>
    </div>
  );
};

