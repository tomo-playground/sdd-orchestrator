"use client";

import { forwardRef, type TextareaHTMLAttributes } from "react";
import { cx, FORM_TEXTAREA_CLASSES, FOCUS_RING, DISABLED_CLASSES } from "./variants";

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
    error?: boolean;
}

const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
    ({ className, error, ...props }, ref) => {
        return (
            <textarea
                ref={ref}
                className={cx(
                    FORM_TEXTAREA_CLASSES,
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
Textarea.displayName = "Textarea";

export default Textarea;
