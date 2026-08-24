import { ArrowUpRight } from "lucide-react";
import { ComponentType, ReactNode } from "react";

import { cn } from "@/lib/utils";

type BentoGridProps = {
  className?: string;
  children: ReactNode;
};

type BentoCardProps = {
  Icon: ComponentType<{ className?: string }>;
  name: string;
  description: string;
  href?: string;
  cta?: string;
  background?: ReactNode;
  className?: string;
  accent?: "green" | "orange" | "blue";
};

export const BentoGrid = ({ className, children }: BentoGridProps) => {
  return (
    <div
      className={cn(
        "grid grid-cols-1 md:grid-cols-2 auto-rows-[minmax(320px,_1fr)] gap-6",
        className,
      )}
    >
      {children}
    </div>
  );
};

export const BentoCard = ({
  Icon,
  name,
  description,
  href,
  cta,
  background,
  className,
  accent = "green",
}: BentoCardProps) => {
  const accentTokens: Record<
    BentoCardProps["accent"],
    { icon: string; shine: string; cta: string }
  > = {
    green: {
      icon: "bg-[#2D5016]/12 text-[#2D5016] dark:bg-[#2D5016]/25 dark:text-[#C3F7C8]",
      shine: "from-[#2D5016]/20 dark:from-[#2D5016]/35",
      cta: "text-[#2D5016] dark:text-[#C3F7C8]",
    },
    orange: {
      icon: "bg-[#FF9933]/15 text-[#CC6A00] dark:bg-[#FF9933]/25 dark:text-[#FFE1C2]",
      shine: "from-[#FF9933]/20 dark:from-[#FF9933]/35",
      cta: "text-[#CC6A00] dark:text-[#FFE1C2]",
    },
    blue: {
      icon: "bg-[#4A90E2]/15 text-[#1C64B5] dark:bg-[#4A90E2]/25 dark:text-[#CFE4FF]",
      shine: "from-[#4A90E2]/25 dark:from-[#4A90E2]/35",
      cta: "text-[#1C64B5] dark:text-[#CFE4FF]",
    },
  };

  const { icon, shine, cta: ctaColor } = accentTokens[accent];

  return (
    <div className={cn("group relative flex h-full", className)}>
      <div
        className={cn(
          "pointer-events-none absolute inset-3 rounded-[36px] bg-gradient-to-br via-transparent to-transparent opacity-30 blur-3xl transition duration-500 group-hover:opacity-80",
          shine,
        )}
      />

      {background ? (
        <div className="pointer-events-none absolute inset-0 overflow-hidden">{background}</div>
      ) : null}

      <div className="relative flex h-full w-full flex-col items-center justify-between rounded-[32px] border border-white/60 bg-white/80 p-8 text-center shadow-[0_20px_60px_rgba(29,45,61,0.08)] backdrop-blur-xl transition duration-300 group-hover:-translate-y-1 group-hover:scale-[1.01] group-hover:shadow-[0_25px_80px_rgba(29,45,61,0.12)] dark:border-white/10 dark:bg-slate-900/80 dark:shadow-[0_25px_80px_rgba(2,6,23,0.8)]">
        <div className="space-y-4">
          <span
            className={cn(
              "inline-flex h-14 w-14 items-center justify-center rounded-[18px] text-lg shadow-inner shadow-black/5 transition duration-300",
              icon,
            )}
          >
            <Icon className="h-6 w-6" />
          </span>
          <div className="space-y-3">
            <h3 className="text-2xl font-semibold text-slate-900 dark:text-white">{name}</h3>
            <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-300">{description}</p>
          </div>
        </div>

        {href && cta ? (
          <a
            href={href}
            className={cn(
              "inline-flex items-center justify-center gap-2 text-sm font-semibold tracking-wide transition duration-200 hover:gap-3",
              ctaColor,
            )}
          >
            {cta}
            <ArrowUpRight className="h-4 w-4" />
          </a>
        ) : null}
      </div>
    </div>
  );
};

