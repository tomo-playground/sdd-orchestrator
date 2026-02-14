"use client";

import { forwardRef, type InputHTMLAttributes } from "react";
import { cx, FORM_INPUT_CLASSES, FOCUS_RING, DISABLED_CLASSES } from "./variants";

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
    error?: boolean;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
    ({ className, error, ...props }, ref) => {
        return (
            <input
                ref={ref}
                className={cx(
                    FORM_INPUT_CLASSES,
                    FOCUS_RING,
                    DISABLED_CLASSES,
                    error && "border-rose-500 focus:border-rose-500 bg-rose-50/50",
                    className
                )}
                {...props}
            />
        );
    }
);
Input.displayName = "Input";

export default Input;
