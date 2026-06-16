import { cn } from "@/lib/utils";

type BadgeTone = "teal" | "amber" | "blue" | "rose" | "neutral";

const tones: Record<BadgeTone, string> = {
  teal: "border-atlas-teal/30 bg-atlas-teal/10 text-atlas-teal",
  amber: "border-atlas-amber/30 bg-atlas-amber/10 text-atlas-amber",
  blue: "border-atlas-blue/30 bg-atlas-blue/10 text-atlas-blue",
  rose: "border-atlas-rose/30 bg-atlas-rose/10 text-atlas-rose",
  neutral: "border-white/10 bg-white/5 text-atlas-muted"
};

export function Badge({
  children,
  tone = "neutral",
  className
}: {
  children: React.ReactNode;
  tone?: BadgeTone;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex h-7 items-center whitespace-nowrap rounded-md border px-2.5 text-xs font-medium",
        tones[tone],
        className
      )}
    >
      {children}
    </span>
  );
}
