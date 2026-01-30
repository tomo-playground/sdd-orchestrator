import axios from "axios";
import { useStudioStore } from "../useStudioStore";
import { API_BASE } from "../../constants";

export async function suggestPromptSplit() {
    const { examplePrompt, setMeta } = useStudioStore.getState();
    if (!examplePrompt.trim()) return;

    setMeta({ isSuggesting: true, copyStatus: "" });
    try {
        const res = await axios.post(`${API_BASE}/prompt/split`, {
            prompt: examplePrompt,
        });
        if (res.data.base || res.data.scene) {
            setMeta({
                suggestedBase: res.data.base || "",
                suggestedScene: res.data.scene || "",
            });
        }
    } catch (error) {
        console.error("Failed to suggest prompt split:", error);
        useStudioStore.getState().showToast("Failed to split prompt", "error");
    } finally {
        setMeta({ isSuggesting: false });
    }
}

export function copyPromptHelperText(text: string) {
    const { setMeta } = useStudioStore.getState();
    if (!text) return;

    navigator.clipboard.writeText(text).then(() => {
        setMeta({ copyStatus: "Copied to clipboard!" });
        setTimeout(() => setMeta({ copyStatus: "" }), 2000);
    });
}
