import { useEffect, useRef, useCallback, useState } from "react";
import debounce from "lodash/debounce";
import { toast } from "react-toastify";

interface UseAutoSaveOptions {
  delay?: number;
  onSave: () => Promise<void>; // function that actually saves data
  enabled?: boolean;
}

interface UseAutoSaveReturn {
  triggerAutoSave: () => void;
}
// the main hook
export default function useAutoSave({
  delay = 3000,
  onSave,
  enabled = true,
}: UseAutoSaveOptions): UseAutoSaveReturn {
  const debouncedSaveRef = useRef(
    debounce(async () => {
      try {
        await onSave();
        toast.success("Changes Saved", { autoClose: 3000 });
      } catch (error) {
        // Displaying the specific error , if not then -> "Save failed"
        const errorMessage =
          error instanceof Error ? error.message : "Save failed";
        toast.error(`Error saving changes: ${errorMessage}`);
      }
    }, delay)
  );

  // whenever user makes change , this function gets called
  const triggerAutoSave = useCallback(() => {
    if (enabled) {
      debouncedSaveRef.current();
    }
  }, [enabled]);

  // Adding this useEffect : if user refreshes browser before 3 sec or navigates away then changes should
  // be saved:
  useEffect(() => {
    const handleBeforeUnload = () => {
      debouncedSaveRef.current.flush(); // Pending changes are getting saved immediately
    };
    // listening for whenever user closes/refreshes browser
    window.addEventListener("beforeunload", handleBeforeUnload);

    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload); // <- cleanup
      debouncedSaveRef.current.flush();
    };
  }, []);

  return {
    triggerAutoSave, // funct to trigger save countdown
  };
}
