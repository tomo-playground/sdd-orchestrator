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
        className="fixed inset-0 z-40 bg-black/60"
        onClick={onClose}
      />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-6">
        <div className="max-h-[90vh] w-full max-w-3xl rounded-3xl border border-white/40 bg-white/90 p-4 shadow-2xl backdrop-blur">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
              {type === "image" ? "Image Preview" : "Video Preview"}
            </span>
            <button
              type="button"
              onClick={onClose}
              className="rounded-full border border-zinc-200 px-3 py-1 text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase"
            >
              Close
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
