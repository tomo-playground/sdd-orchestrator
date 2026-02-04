export default function Footer() {
    return (
        <footer className="mt-auto max-w-5xl border-t border-zinc-100 px-6 py-8 text-center w-full">
            <p className="text-xs text-zinc-400">
                &copy; {new Date().getFullYear()} Shorts Producer. All rights reserved.
                <span className="mx-2 text-zinc-300">|</span>
                v1.0.0
            </p>
        </footer>
    );
}
