"use client";

type Props = {
  reasoning: { narrative_function: string; why: string; alternatives: string[] };
  onClose: () => void;
};

export default function SceneReasoningPanel({ reasoning, onClose }: Props) {
  return (
    <div className="mt-2 rounded-xl border border-zinc-200 bg-zinc-50 p-4">
      <div className="mb-2 flex items-center justify-between">
        <h4 className="text-xs font-semibold text-zinc-700">씬 근거</h4>
        <button onClick={onClose} className="text-xs text-zinc-400 hover:text-zinc-600">
          닫기
        </button>
      </div>
      <div className="space-y-2 text-xs text-zinc-600">
        <div>
          <span className="font-medium text-zinc-500">역할:</span> {reasoning.narrative_function}
        </div>
        <div>
          <span className="font-medium text-zinc-500">이유:</span> {reasoning.why}
        </div>
        {reasoning.alternatives.length > 0 && (
          <div>
            <span className="font-medium text-zinc-500">대안:</span>
            <ul className="mt-1 list-disc pl-4">
              {reasoning.alternatives.map((alt, i) => (
                <li key={i}>{alt}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
