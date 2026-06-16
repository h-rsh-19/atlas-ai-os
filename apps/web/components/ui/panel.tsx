import { cn } from "@/lib/utils";

export function Panel({
  children,
  className
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section
      className={cn(
        "rounded-lg border border-atlas-line bg-atlas-panel p-4 shadow-panel",
        className
      )}
    >
      {children}
    </section>
  );
}

export function SectionTitle({
  eyebrow,
  title,
  action
}: {
  eyebrow?: string;
  title: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="mb-4 flex min-h-10 items-start justify-between gap-3">
      <div className="min-w-0">
        {eyebrow ? (
          <p className="mb-1 text-xs font-semibold uppercase tracking-[0.18em] text-atlas-muted">
            {eyebrow}
          </p>
        ) : null}
        <h2 className="truncate text-base font-semibold text-atlas-text">{title}</h2>
      </div>
      {action}
    </div>
  );
}
