import { useEffect, useRef, useCallback, useState } from "react";
import debounce from "lodash/debounce";

type SaveStatus = "idle" | "saving" | "saved" | "error";

interface UseAutoSaveOptions {
  delay?: number;
  onSave: () => Promise<void>;
  enabled?: boolean;
}

interface UseAutoSaveReturn {
  triggerAutoSave: () => void;
  cancelAutoSave: () => void;
  saveStatus: SaveStatus;
  errorMessage: string;
}

export default function useAutoSave({
  delay = 2000,
  onSave,
  enabled = true,
}: UseAutoSaveOptions): UseAutoSaveReturn {
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");
  const [errorMessage, setErrorMessage] = useState<string>("");

  const debouncedSaveRef = useRef(
    debounce(async () => {
      setSaveStatus("saving");
      try {
        await onSave();
        setSaveStatus("saved");
        setErrorMessage("");
        // Reset to idle after 2 seconds
        setTimeout(() => setSaveStatus("idle"), 2000);
      } catch (error) {
        console.error("Auto-save failed:", error);
        setSaveStatus("error");
        setErrorMessage(error instanceof Error ? error.message : "Save failed");
      }
    }, delay)
  );

  useEffect(() => {
    return () => {
      debouncedSaveRef.current.cancel();
    };
  }, []);

  const triggerAutoSave = useCallback(() => {
    if (enabled) {
      debouncedSaveRef.current();
    }
  }, [enabled]);

  const cancelAutoSave = useCallback(() => {
    debouncedSaveRef.current.cancel();
    setSaveStatus("idle");
  }, []);

  return {
    triggerAutoSave,
    cancelAutoSave,
    saveStatus,
    errorMessage,
  };
}
