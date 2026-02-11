"use client";

import { useMemo } from "react";

type PromptTokenPreviewProps = {
  prompt: string;
  triggerWords?: string[];
  className?: string;
};

type TokenType = "lora" | "trigger" | "normal";

type ParsedToken = {
  text: string;
  type: TokenType;
  loraName?: string;
  loraWeight?: string;
};

/**
 * Parses a prompt string and identifies LoRA tags and trigger words.
 */
function parsePromptTokens(prompt: string, triggerWords: string[]): ParsedToken[] {
  if (!prompt.trim()) return [];

  const tokens: ParsedToken[] = [];
  const loraPattern = /<lora:([^:>]+):([^>]+)>/g;

  // Normalize trigger words for case-insensitive matching
  const normalizedTriggers = triggerWords.map((tw) => tw.toLowerCase().trim());

  // Split by commas first, preserving the structure
  const parts = prompt.split(",").map((p) => p.trim()).filter(Boolean);

  for (const part of parts) {
    // Check if this part contains a LoRA tag
    const loraMatch = part.match(loraPattern);

    if (loraMatch) {
      // Extract LoRA info
      const match = /<lora:([^:>]+):([^>]+)>/.exec(part);
      if (match) {
        // Check if there's text before the LoRA tag
        const beforeLora = part.substring(0, part.indexOf("<lora:")).trim();
        if (beforeLora) {
          tokens.push(parseNonLoraToken(beforeLora, normalizedTriggers));
        }

        tokens.push({
          text: match[0],
          type: "lora",
          loraName: match[1],
          loraWeight: match[2],
        });

        // Check if there's text after the LoRA tag
        const afterLora = part.substring(part.indexOf(">") + 1).trim();
        if (afterLora) {
          tokens.push(parseNonLoraToken(afterLora, normalizedTriggers));
        }
      }
    } else {
      tokens.push(parseNonLoraToken(part, normalizedTriggers));
    }
  }

  return tokens;
}

function parseNonLoraToken(text: string, normalizedTriggers: string[]): ParsedToken {
  const normalized = text.toLowerCase().trim();

  // Check if this is a trigger word
  if (normalizedTriggers.includes(normalized)) {
    return { text, type: "trigger" };
  }

  // Check for partial matches (trigger word might be part of compound)
  for (const trigger of normalizedTriggers) {
    if (normalized === trigger || normalized.includes(trigger)) {
      return { text, type: "trigger" };
    }
  }

  return { text, type: "normal" };
}

/**
 * Displays prompt tokens with visual highlighting for LoRA tags and trigger words.
 */
export default function PromptTokenPreview({
  prompt,
  triggerWords = [],
  className = "",
}: PromptTokenPreviewProps) {
  const tokens = useMemo(
    () => parsePromptTokens(prompt, triggerWords),
    [prompt, triggerWords]
  );

  if (tokens.length === 0) {
    return null;
  }

  return (
    <div className={`flex flex-wrap gap-1.5 ${className}`}>
      {tokens.map((token, idx) => {
        if (token.type === "lora") {
          return (
            <span
              key={idx}
              className="inline-flex items-center gap-1 rounded-full bg-violet-100 px-2.5 py-1 text-[12px] font-semibold text-violet-700 border border-violet-200"
              title={`LoRA: ${token.loraName} @ ${token.loraWeight}`}
            >
              <span className="text-violet-400">⚡</span>
              <span>{token.loraName}</span>
              <span className="text-violet-400">:</span>
              <span className="text-violet-500">{token.loraWeight}</span>
            </span>
          );
        }

        if (token.type === "trigger") {
          return (
            <span
              key={idx}
              className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2.5 py-1 text-[12px] font-semibold text-emerald-700 border border-emerald-200"
              title="Trigger Word"
            >
              <span className="text-emerald-400">★</span>
              <span>{token.text}</span>
            </span>
          );
        }

        return (
          <span
            key={idx}
            className="rounded-full bg-zinc-100 px-2 py-1 text-[12px] text-zinc-600 border border-zinc-200"
          >
            {token.text}
          </span>
        );
      })}
    </div>
  );
}
