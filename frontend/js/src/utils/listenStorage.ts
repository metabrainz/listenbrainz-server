import localforage from "localforage";

// Setup Database
const listenStore = localforage.createInstance({
  name: "listenbrainz",
  storeName: "unsent_listens_queue",
});

// Save Function
export const saveFailedListen = async (listen: any) => {
  const id = Date.now().toString();
  // Store payload and timestamp
  await listenStore.setItem(id, { listen, timestamp: Date.now() });
  console.log(`[Offline] Listen saved locally: ${id}`);
};

// Get Function
export const getFailedListens = async () => {
  const failedListens: { id: string; listen: any }[] = [];
  await listenStore.iterate((value: any, key: string) => {
    failedListens.push({ id: key, listen: value.listen });
  });
  return failedListens;
};

// Delete Function
export const removeFailedListen = async (id: string) => {
  await listenStore.removeItem(id);
  console.log(`[Offline] Listen removed: ${id}`);
};
