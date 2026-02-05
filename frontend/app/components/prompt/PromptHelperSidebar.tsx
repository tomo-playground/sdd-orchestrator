"use client";

type PromptHelperSidebarProps = {
  isOpen: boolean;
  onClose: () => void;
  examplePrompt: string;
  setExamplePrompt: (value: string) => void;
  onSuggestSplit: () => void;
  isSuggesting: boolean;
  suggestedBase: string;
  suggestedScene: string;
  copyStatus: string | null;
  onCopyText: (text: string) => void;
};

export default function PromptHelperSidebar({
  isOpen,
  onClose,
  examplePrompt,
  setExamplePrompt,
  onSuggestSplit,
  isSuggesting,
  suggestedBase,
  suggestedScene,
  copyStatus,
  onCopyText,
}: PromptHelperSidebarProps) {
  return (
    <>
      <div
        className={`fixed inset-0 z-[var(--z-sidebar)] bg-black/30 transition-opacity ${isOpen ? "opacity-100" : "pointer-events-none opacity-0"}`}
        onClick={onClose}
      />
      <aside
        className={`fixed top-0 right-0 z-[var(--z-sidebar)] h-full w-full max-w-md transform bg-white shadow-2xl transition-transform ${isOpen ? "translate-x-0" : "translate-x-full"}`}
      >
        <div className="flex h-full flex-col gap-4 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs tracking-[0.3em] text-zinc-500 uppercase">Prompt Helper</p>
              <h3 className="text-lg font-semibold text-zinc-900">Split Example Prompt</h3>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="rounded-full border border-zinc-200 px-3 py-1 text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase"
            >
              Close
            </button>
          </div>
          {copyStatus && (
            <div className="rounded-2xl border border-zinc-200 bg-zinc-50 px-4 py-2 text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
              {copyStatus}
            </div>
          )}
          <div className="grid gap-2">
            <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
              Example Prompt
            </label>
            <textarea
              value={examplePrompt}
              onChange={(e) => setExamplePrompt(e.target.value)}
              rows={4}
              className="rounded-2xl border border-zinc-200 bg-white p-3 text-sm outline-none focus:border-zinc-400"
              placeholder="Paste a full prompt line from Civitai"
            />
            <button
              type="button"
              onClick={onSuggestSplit}
              disabled={isSuggesting || !examplePrompt.trim()}
              className="rounded-full bg-zinc-900 px-4 py-2 text-[10px] font-semibold tracking-[0.2em] text-white uppercase shadow-md shadow-zinc-900/20 transition disabled:cursor-not-allowed disabled:bg-zinc-400"
            >
              {isSuggesting ? "Suggesting..." : "Suggest Base/Scene"}
            </button>
          </div>
          {(suggestedBase || suggestedScene) && (
            <div className="grid gap-4">
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                    Suggested Base
                  </label>
                  <button
                    type="button"
                    onClick={() => onCopyText(suggestedBase)}
                    className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase"
                  >
                    Copy
                  </button>
                </div>
                <textarea
                  value={suggestedBase}
                  readOnly
                  rows={3}
                  className="rounded-2xl border border-zinc-200 bg-zinc-50 p-3 text-xs text-zinc-600"
                />
              </div>
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                    Suggested Scene
                  </label>
                  <button
                    type="button"
                    onClick={() => onCopyText(suggestedScene)}
                    className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase"
                  >
                    Copy
                  </button>
                </div>
                <textarea
                  value={suggestedScene}
                  readOnly
                  rows={3}
                  className="rounded-2xl border border-zinc-200 bg-zinc-50 p-3 text-xs text-zinc-600"
                />
              </div>
            </div>
          )}
          <div className="mt-auto text-[10px] text-zinc-400">
            Suggestions do not auto-apply. Copy and paste into Base Prompt or Scene Prompt.
          </div>
        </div>
      </aside>
    </>
  );
}
