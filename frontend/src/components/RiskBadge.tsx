import { cn } from "@/lib/utils";

interface RiskBadgeProps {
  risk: "NONE" | "LOW" | "MEDIUM" | "HIGH";
  className?: string;
}

export function RiskBadge({ risk, className }: RiskBadgeProps) {
  const styles = {
    NONE: "bg-success/15 text-success border-success/20",
    LOW: "bg-primary/15 text-primary border-primary/20",
    MEDIUM: "bg-warning/15 text-warning border-warning/20",
    HIGH: "bg-destructive/15 text-destructive border-destructive/20",
  };

  const labels = {
    NONE: "Compliant",
    LOW: "Low Risk",
    MEDIUM: "Medium Risk",
    HIGH: "High Risk",
  };

  return (
    <span
      className={cn(
        "px-2.5 py-0.5 rounded-full text-xs font-medium border uppercase tracking-wider",
        styles[risk],
        className
      )}
    >
      {labels[risk]}
    </span>
  );
}
