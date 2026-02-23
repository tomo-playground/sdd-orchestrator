/**
 * LinearView — All tokens in order for ComposedPromptPreview.
 */

type LinearViewProps = {
  tokens: string[];
  getTokenStyle: (token: string) => { bg: string; text: string; border: string };
  getCategory: (token: string) => string;
};

export default function LinearView({ tokens, getTokenStyle, getCategory }: LinearViewProps) {
  return (
    <div className="flex flex-wrap gap-1">
      {tokens.map((token, idx) => {
        const style = getTokenStyle(token);
        return (
          <span
            key={idx}
            className={`rounded-full border px-2 py-0.5 text-[12px] ${style.bg} ${style.text} ${style.border}`}
            title={getCategory(token)}
          >
            {token === "BREAK" ? (
              <span className="font-bold">BREAK</span>
            ) : token.startsWith("<lora:") ? (
              <>
                <span className="opacity-60">&#9889;</span>
                {token.replace(/<lora:|>/g, "")}
              </>
            ) : (
              token
            )}
          </span>
        );
      })}
    </div>
  );
}
