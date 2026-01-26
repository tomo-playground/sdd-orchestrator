"use client";

type LayoutSelectorProps = {
  value: "full" | "post";
  onChange: (value: "full" | "post") => void;
  showLabel?: boolean;
  variant?: "compact" | "detailed";
};

export default function LayoutSelector({
  value,
  onChange,
  showLabel = false,
  variant = "compact",
}: LayoutSelectorProps) {
  const isCompact = variant === "compact";

  return (
    <div className={showLabel ? "grid gap-3" : ""}>
      {showLabel && (
        <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
          Layout
        </label>
      )}
      <div className={`flex ${isCompact ? "justify-center" : ""} gap-4`}>
        {/* Full Button */}
        <button
          type="button"
          onClick={() => onChange("full")}
          className={`flex flex-col items-center gap-2 rounded-2xl border-2 p-4 transition ${
            value === "full"
              ? "border-zinc-900 bg-zinc-900/5 shadow-md"
              : "border-zinc-200 bg-white hover:border-zinc-400"
          }`}
        >
          <div
            className={`flex ${isCompact ? "h-16 w-9" : "h-20 w-11"} flex-col items-center justify-center rounded-lg border-2 ${
              value === "full" ? "border-zinc-700 bg-zinc-200" : "border-zinc-300 bg-zinc-100"
            }`}
          >
            <div className={`${isCompact ? "h-4 w-4" : "h-6 w-6"} rounded ${value === "full" ? "bg-zinc-500" : "bg-zinc-300"}`} />
            {!isCompact && (
              <>
                <div className={`mt-1 h-1 w-5 rounded ${value === "full" ? "bg-zinc-400" : "bg-zinc-200"}`} />
                <div className={`mt-0.5 h-1 w-4 rounded ${value === "full" ? "bg-zinc-400" : "bg-zinc-200"}`} />
              </>
            )}
          </div>
          <div className="text-center">
            <p className={`text-xs font-semibold ${value === "full" ? "text-zinc-900" : "text-zinc-600"}`}>Full</p>
            <p className={`text-[10px] ${value === "full" ? "text-zinc-600" : "text-zinc-400"}`}>
              {isCompact ? "9:16" : "9:16 세로"}
            </p>
          </div>
          {!isCompact && value === "full" && (
            <span className="rounded-full bg-zinc-900 px-2 py-0.5 text-[9px] font-semibold text-white">선택됨</span>
          )}
        </button>

        {/* Post Button */}
        <button
          type="button"
          onClick={() => onChange("post")}
          className={`flex flex-col items-center gap-2 rounded-2xl border-2 p-4 transition ${
            value === "post"
              ? "border-zinc-900 bg-zinc-900/5 shadow-md"
              : "border-zinc-200 bg-white hover:border-zinc-400"
          }`}
        >
          <div
            className={`flex ${isCompact ? "h-11 w-11" : "h-14 w-14"} flex-col items-center justify-center rounded-lg border-2 ${
              value === "post" ? "border-zinc-700 bg-zinc-200" : "border-zinc-300 bg-zinc-100"
            }`}
          >
            <div className={`${isCompact ? "h-4 w-4" : "h-6 w-6"} rounded ${value === "post" ? "bg-zinc-500" : "bg-zinc-300"}`} />
            {!isCompact && (
              <div className={`mt-1 h-1 w-5 rounded ${value === "post" ? "bg-zinc-400" : "bg-zinc-200"}`} />
            )}
          </div>
          <div className="text-center">
            <p className={`text-xs font-semibold ${value === "post" ? "text-zinc-900" : "text-zinc-600"}`}>Post</p>
            <p className={`text-[10px] ${value === "post" ? "text-zinc-600" : "text-zinc-400"}`}>
              {isCompact ? "1:1" : "1:1 정사각형"}
            </p>
          </div>
          {!isCompact && value === "post" && (
            <span className="rounded-full bg-zinc-900 px-2 py-0.5 text-[9px] font-semibold text-white">선택됨</span>
          )}
        </button>
      </div>
    </div>
  );
}
