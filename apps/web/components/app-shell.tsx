"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, Command, DatabaseZap } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { navItems } from "@/lib/data";
import { cn } from "@/lib/utils";

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-atlas-bg">
      <aside className="fixed left-0 top-0 hidden h-screen w-72 border-r border-atlas-line bg-[#0e141b] p-4 lg:block">
        <div className="mb-8 flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-lg border border-atlas-teal/30 bg-atlas-teal/10">
            <Command className="h-5 w-5 text-atlas-teal" />
          </div>
          <div>
            <p className="text-lg font-semibold text-atlas-text">Atlas</p>
            <p className="text-xs text-atlas-muted">Private AI OS</p>
          </div>
        </div>

        <nav className="space-y-1">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;

            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex h-11 items-center gap-3 rounded-md px-3 text-sm font-medium transition",
                  isActive
                    ? "bg-atlas-panelSoft text-atlas-text"
                    : "text-atlas-muted hover:bg-white/5 hover:text-atlas-text"
                )}
              >
                <Icon className="h-4 w-4" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="absolute bottom-4 left-4 right-4 rounded-lg border border-atlas-line bg-atlas-panel p-3">
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold text-atlas-text">
              <DatabaseZap className="h-4 w-4 text-atlas-blue" />
              Context Index
            </div>
            <Badge tone="teal">Live</Badge>
          </div>
          <div className="grid grid-cols-3 gap-2 text-center">
            <div>
              <p className="text-base font-semibold">Local</p>
              <p className="text-[11px] text-atlas-muted">Memory</p>
            </div>
            <div>
              <p className="text-base font-semibold">Cited</p>
              <p className="text-[11px] text-atlas-muted">Symbols</p>
            </div>
            <div>
              <p className="text-base font-semibold">Gated</p>
              <p className="text-[11px] text-atlas-muted">Runs</p>
            </div>
          </div>
        </div>
      </aside>

      <div className="lg:pl-72">
        <header className="sticky top-0 z-20 border-b border-atlas-line bg-atlas-bg/95 px-4 py-3 backdrop-blur md:px-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3 lg:hidden">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-atlas-teal/30 bg-atlas-teal/10">
                <Command className="h-5 w-5 text-atlas-teal" />
              </div>
              <div>
                <p className="font-semibold text-atlas-text">Atlas</p>
                <p className="text-xs text-atlas-muted">Private AI OS</p>
              </div>
            </div>

            <div className="hidden items-center gap-2 lg:flex">
              <Badge tone="teal">Traceable</Badge>
              <Badge tone="blue">Source-backed</Badge>
              <Badge tone="amber">Approval gated</Badge>
            </div>

            <div className="flex items-center gap-2">
              <Button size="sm" variant="ghost" aria-label="Open activity">
                <Activity className="h-4 w-4" />
                <span className="hidden sm:inline">Activity</span>
              </Button>
              <Button size="sm" variant="primary" aria-label="Open command palette">
                <Command className="h-4 w-4" />
                Command
              </Button>
            </div>
          </div>

          <nav className="mt-3 flex gap-2 overflow-x-auto pb-1 lg:hidden">
            {navItems.map((item) => {
              const isActive = pathname === item.href;
              const Icon = item.icon;

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "inline-flex h-9 shrink-0 items-center gap-2 rounded-md border px-3 text-sm",
                    isActive
                      ? "border-atlas-teal/30 bg-atlas-teal/10 text-atlas-teal"
                      : "border-atlas-line bg-atlas-panel text-atlas-muted"
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </header>

        <main className="mx-auto w-full max-w-7xl px-4 py-6 md:px-6">{children}</main>
      </div>
    </div>
  );
}
