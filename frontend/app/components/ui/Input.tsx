"use client";

import { forwardRef, type InputHTMLAttributes } from "react";
import {
    cx,
    FORM_INPUT_CLASSES,
    FOCUS_RING,
    DISABLED_CLASSES,
    ERROR_INPUT_BORDER,
    ERROR_BG,
    ERROR_INPUT_FOCUS
} from "./variants";

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
                    error && `${ERROR_INPUT_BORDER} ${ERROR_INPUT_FOCUS} ${ERROR_BG}/50`,
                    className
                )}
                {...props}
            />
        );
    }
);
Input.displayName = "Input";

export default Input;
