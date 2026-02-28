import ServiceShell from "../components/shell/ServiceShell";

export default function ServiceLayout({ children }: { children: React.ReactNode }) {
  return <ServiceShell>{children}</ServiceShell>;
}
