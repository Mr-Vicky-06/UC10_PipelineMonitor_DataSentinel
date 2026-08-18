import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-sm border px-2 py-0.5 text-xs font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-border-focus focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-interactive text-inverse",
        secondary:
          "border-transparent bg-muted text-primary",
        outline: "text-primary",
        critical: "border-transparent bg-status-critical text-inverse",
        error: "border-transparent bg-status-error text-inverse",
        warning: "border-transparent bg-status-warning text-inverse",
        success: "border-transparent bg-status-success text-inverse",
        info: "border-transparent bg-status-info text-inverse",
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
