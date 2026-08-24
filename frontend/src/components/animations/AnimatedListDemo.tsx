import { useEffect, useState } from "react";

import { cn } from "@/lib/utils";

type AnimatedListDemoProps = {
  className?: string;
};

type Notification = {
  title: string;
  meta: string;
  accent: string;
};

const alerts: Notification[] = [
  {
    title: "Soil moisture dropped in Cluster 4",
    meta: "Sensor 4A • 2m ago",
    accent: "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-200",
  },
  {
    title: "Self-help group meeting synced",
    meta: "Community Hub • 8m ago",
    accent: "bg-sky-100 text-sky-700 dark:bg-sky-500/20 dark:text-sky-200",
  },
  {
    title: "Solar array output peaked 15%",
    meta: "Energy Watch • 12m ago",
    accent: "bg-amber-100 text-amber-800 dark:bg-amber-500/20 dark:text-amber-100",
  },
  {
    title: "New irrigation subsidy published",
    meta: "Gov Portal • 30m ago",
    accent: "bg-purple-100 text-purple-700 dark:bg-purple-500/20 dark:text-purple-100",
  },
  {
    title: "Delivery drone scheduled for Taluk HQ",
    meta: "Logistics • 45m ago",
    accent: "bg-rose-100 text-rose-700 dark:bg-rose-500/20 dark:text-rose-100",
  },
];

export const AnimatedListDemo = ({ className }: AnimatedListDemoProps) => {
  const [items, setItems] = useState(alerts);

  useEffect(() => {
    const interval = setInterval(() => {
      setItems((prev) => {
        const [first, ...rest] = prev;
        return [...rest, first];
      });
    }, 2800);

    return () => clearInterval(interval);
  }, []);

  const visible = items.slice(0, 4);

  return (
    <div
      className={cn(
        "flex h-full flex-col gap-3 overflow-hidden rounded-3xl border border-border/60 bg-card/80 p-4 shadow-lg shadow-black/[0.05]",
        className,
      )}
    >
      {visible.map((alert, index) => (
        <article
          key={`${alert.title}-${index}`}
          className={cn(
            "animate-in fade-in slide-in-from-top-2 flex flex-col gap-2 rounded-2xl border border-border/40 bg-background/80 px-4 py-3 shadow-sm shadow-black/[0.03]",
            "transition duration-500",
          )}
          style={{ animationDelay: `${index * 120}ms` }}
        >
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm font-medium leading-snug">{alert.title}</p>
            <span className={cn("rounded-full px-2 py-1 text-[11px] font-semibold uppercase", alert.accent)}>
              live
            </span>
          </div>
          <p className="text-xs text-muted-foreground">{alert.meta}</p>
        </article>
      ))}
    </div>
  );
};

