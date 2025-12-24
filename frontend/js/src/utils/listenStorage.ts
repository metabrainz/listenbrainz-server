import localforage from "localforage";

const listenStore = localforage.createInstance({
  name: "listenbrainz",
  storeName: "unsent_listens_queue",
});

export const saveFailedListen = async (listen: Listen): Promise<void> => {
  const id = `${listen.listened_at}-${Math.random().toString(36).slice(2)}`;
  await listenStore.setItem(id, listen);
};

export const getFailedListens = async (): Promise<
  { id: string; listen: Listen }[]
> => {
  const failedListens: { id: string; listen: Listen }[] = [];

  await listenStore.iterate<Listen, void>((value, key) => {
    failedListens.push({ id: key, listen: value });
  });

  return failedListens.sort(
    (a, b) => a.listen.listened_at - b.listen.listened_at
  );
};

export const removeFailedListen = async (id: string): Promise<void> => {
  await listenStore.removeItem(id);
};

export const clearFailedListens = async (): Promise<void> => {
  await listenStore.clear();
};
