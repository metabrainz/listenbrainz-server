import { useEffect, useRef, useCallback, useState } from "react";
import debounce from "lodash/debounce";
import { toast } from "react-toastify";

interface UseAutoSaveOptions<T> {
  delay?: number;
  onSave: (value: T) => Promise<void>; // function that actually saves data
}

interface UseAutoSaveReturn<T> {
  triggerAutoSave: (value: T) => void;
}
// the main hook
export default function useAutoSave<T>({
  delay = 3000,
  onSave,
}: UseAutoSaveOptions<T>): UseAutoSaveReturn<T> {
  const debouncedSaveRef = useRef<ReturnType<typeof debounce>>();
  useEffect(() => {
    const debouncedSave = debounce(async (value: T) => {
      try {
        await onSave(value);
        toast.success("Changes Saved", { autoClose: 3000 });
      } catch (error) {
        // Displaying the specific error , if not then -> "Save failed"
        const errorMessage =
          error instanceof Error ? error.message : "Save failed";
        toast.error(`Error saving changes: ${errorMessage}`);
      }
    }, delay);
    debouncedSaveRef.current = debouncedSave;
    // fires when Refresh / close tab
    const handleBeforeUnload = () => {
      debouncedSave.flush(); // Pending changes are getting saved immediately
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    // Flush pending changes on component unmount or re-init like ,
    //  user navigates to another route
    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload); // <- cleanup
      debouncedSave.flush();
    };
  }, [delay, onSave]);

  // whenever user makes change , this function gets called
  const triggerAutoSave = useCallback((value: T) => {
    debouncedSaveRef.current?.(value);
  }, []);
  return { triggerAutoSave };
}
