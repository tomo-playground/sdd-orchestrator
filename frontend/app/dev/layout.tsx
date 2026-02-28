import DevShell from "../components/shell/DevShell";

export default function DevLayout({ children }: { children: React.ReactNode }) {
  return <DevShell>{children}</DevShell>;
}
