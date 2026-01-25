import React from "react";

type LoadingSpinnerProps = {
  size?: "sm" | "md" | "lg";
  color?: string;
  className?: string;
};

export default function LoadingSpinner({
  size = "md",
  color = "text-zinc-500",
  className = "",
}: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: "h-4 w-4 border-2",
    md: "h-6 w-6 border-2",
    lg: "h-10 w-10 border-3",
  };

  return (
    <div
      className={`animate-spin rounded-full border-t-transparent ${sizeClasses[size]} ${color} ${className}`}
      role="status"
      aria-label="Loading"
    />
  );
}
