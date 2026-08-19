import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-sm border px-2 py-0.5 text-xs font-medium tabular-nums transition-colors focus:outline-none focus:ring-2 focus:ring-border-focus focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-interactive text-inverse",
        secondary:
          "border-transparent bg-muted text-primary",
        outline: "text-primary border-border-default",
        critical: "border-transparent bg-[var(--color-status-critical)] text-inverse",
        warning: "border-transparent bg-[var(--color-status-warning)] text-inverse",
        healthy: "border-transparent bg-[var(--color-status-healthy)] text-inverse",
        running: "border-transparent bg-[var(--color-status-running)] text-inverse",
        stale: "border-transparent bg-[var(--color-status-stale)] text-inverse",
        unknown: "border-dashed border-[var(--color-status-unknown)] text-[var(--color-status-unknown)] bg-transparent",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

export { Badge, badgeVariants }
