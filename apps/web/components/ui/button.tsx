import { Slot } from "@radix-ui/react-slot";
import { type VariantProps, cva } from "class-variance-authority";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex h-10 items-center justify-center gap-2 whitespace-nowrap rounded-md px-3 text-sm font-semibold transition focus:outline-none focus:ring-2 focus:ring-atlas-teal/40 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        primary: "bg-atlas-teal text-slate-950 hover:bg-[#65e1c7]",
        secondary: "border border-atlas-line bg-atlas-panelSoft text-atlas-text hover:bg-[#1b2835]",
        ghost: "text-atlas-muted hover:bg-white/5 hover:text-atlas-text"
      },
      size: {
        default: "h-10 px-3",
        icon: "h-10 w-10 px-0",
        sm: "h-8 px-2.5 text-xs"
      }
    },
    defaultVariants: {
      variant: "secondary",
      size: "default"
    }
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export function Button({ className, variant, size, asChild = false, ...props }: ButtonProps) {
  const Comp = asChild ? Slot : "button";

  return <Comp className={cn(buttonVariants({ variant, size, className }))} {...props} />;
}
