"use client";

import { HelpCircle } from "lucide-react";
import Tooltip from "./Tooltip";
import { GLOSSARY, type GlossaryTerm } from "../../constants/glossary";

type Props = {
  term: GlossaryTerm;
  position?: "top" | "bottom" | "left" | "right";
};

export default function InfoTooltip({ term, position = "top" }: Props) {
  return (
    <Tooltip content={GLOSSARY[term]} position={position} className="max-w-[220px]">
      <HelpCircle className="inline h-3.5 w-3.5 text-zinc-300 hover:text-zinc-500" />
    </Tooltip>
  );
}
