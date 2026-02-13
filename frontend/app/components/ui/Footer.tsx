export default function Footer() {
  return (
    <footer className="mx-auto mt-auto w-full max-w-7xl border-t border-zinc-100 px-6 py-8 text-center">
      <p className="text-xs text-zinc-400">
        &copy; {new Date().getFullYear()} Shorts Producer. All rights reserved.
        <span className="mx-2 text-zinc-200">&middot;</span>
        v1.0.0
      </p>
    </footer>
  );
}
