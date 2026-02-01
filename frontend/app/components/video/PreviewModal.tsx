"use client";

type PreviewModalProps = {
  type: "image" | "video";
  src: string;
  onClose: () => void;
};

export default function PreviewModal({ type, src, onClose }: PreviewModalProps) {
  return (
    <>
      <div
        className="fixed inset-0 z-[var(--z-modal)] bg-black/60"
        onClick={onClose}
      />
      <div className="fixed inset-0 z-[var(--z-modal)] flex items-center justify-center p-6">
        <div className="max-h-[90vh] w-full max-w-3xl rounded-3xl border border-white/40 bg-white/90 p-4 shadow-2xl backdrop-blur">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
              {type === "image" ? "Image Preview" : "Video Preview"}
            </span>
            <button
              type="button"
              onClick={onClose}
              className="rounded-full p-2 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600 transition-colors"
            >
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-5 h-5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div className={`mt-3 flex max-h-[80vh] w-full items-center justify-center overflow-hidden rounded-2xl ${type === "image" ? "bg-zinc-100 p-3" : "bg-black"}`}>
            {type === "image" ? (
              <img
                src={src}
                alt="Generated scene"
                className="max-h-[76vh] w-auto max-w-full object-contain"
              />
            ) : (
              <video
                src={src}
                controls
                autoPlay
                className="max-h-[78vh] w-auto max-w-full object-contain"
              />
            )}
          </div>
        </div>
      </div>
    </>
  );
}
