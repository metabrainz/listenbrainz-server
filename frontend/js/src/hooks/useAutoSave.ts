import { useEffect, useRef, useCallback, useState } from "react";
import debounce from "lodash/debounce";
// possible states
type SaveStatus = "idle" | "saving" | "saved" | "error";

interface UseAutoSaveOptions {
  delay?: number;
  onSave: () => Promise<void>; // function that actually saves data
  enabled?: boolean;
}

interface UseAutoSaveReturn {
  triggerAutoSave: () => void;
  cancelAutoSave: () => void;
  saveStatus: SaveStatus; // current status
  errorMessage: string;
}
// the main hook
export default function useAutoSave({
  delay = 1000,
  onSave,
  enabled = true,
}: UseAutoSaveOptions): UseAutoSaveReturn {
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");
  const [errorMessage, setErrorMessage] = useState<string>("");
  // this funct waits for user to stop making change before
  // actually saving
  const debouncedSaveRef = useRef(
    debounce(async () => {
      setSaveStatus("saving");
      try {
        await onSave();
        setSaveStatus("saved");
        setErrorMessage("");
      } catch (error) {
        // console.error("Auto-save failed:", error);
        setSaveStatus("error");
        // Displaying the specific error , if not then -> "Save failed"
        setErrorMessage(error instanceof Error ? error.message : "Save failed");
      }
    }, delay)
  );

  // if the user changes the screen or navigates away before say 1 sec
  // then we cancel the save

  useEffect(() => {
    return () => {
      debouncedSaveRef.current.cancel();
    };
  }, []);
  // whenever user makes change , this function gets called
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
    triggerAutoSave, // funct to trigger save countdown
    cancelAutoSave, // function to cancel pending save
    saveStatus,
    errorMessage,
  };
}
