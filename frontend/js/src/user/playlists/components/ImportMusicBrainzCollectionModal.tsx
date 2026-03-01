import React from "react";
import NiceModal, { useModal, bootstrapDialog } from "@ebay/nice-modal-react";
import { Modal } from "react-bootstrap";
import { toast } from "react-toastify";
import GlobalAppContext from "../../../utils/GlobalAppContext";
import { ToastMsg } from "../../../notifications/Notifications";
import Loader from "../../../components/Loader";

type MBCollection = {
  gid: string;
  name: string;
  public: boolean;
  description: string | null;
};

export default NiceModal.create(() => {
  const modal = useModal();

  const { APIService, currentUser } = React.useContext(GlobalAppContext);
  const [collections, setCollections] = React.useState<MBCollection[]>([]);
  const [newPlaylists, setNewPlaylists] = React.useState<JSPFPlaylist[]>([]);
  const [loading, setLoading] = React.useState<boolean>(true);
  const [importingCollection, setImportingCollection] = React.useState<
    string | null
  >(null);

  React.useEffect(() => {
    async function fetchCollections() {
      try {
        const response = await APIService.importMBCollections(
          currentUser?.auth_token
        );
        if (!response) {
          return;
        }
        setCollections(response);
      } catch (error) {
        toast.error(
          <ToastMsg
            title="Error loading collections"
            message={error?.message ?? error}
          />,
          { toastId: "load-collections-error" }
        );
      } finally {
        setLoading(false);
      }
    }

    if (currentUser?.auth_token) {
      fetchCollections();
    }
  }, [APIService, currentUser]);

  const resolveAndClose = () => {
    modal.resolve(newPlaylists);
    modal.hide();
  };

  const alertMustBeLoggedIn = () => {
    toast.error(
      <ToastMsg
        title="Error"
        message="You must be logged in for this operation"
      />,
      { toastId: "auth-error" }
    );
  };

  const importCollection = async (collection: MBCollection) => {
    if (!currentUser?.auth_token) {
      alertMustBeLoggedIn();
      return;
    }
    setImportingCollection(collection.gid);
    try {
      const response = await APIService.importMBCollectionTracks(
        currentUser?.auth_token,
        collection.gid
      );
      const newPlaylist: JSPFPlaylist = response.playlist;
      toast.success(
        <ToastMsg
          title="Successfully imported collection from MusicBrainz"
          message={
            <>
              Imported{" "}
              <a href={`/playlist/${newPlaylist.identifier}`}>
                {collection.name}
              </a>
            </>
          }
        />,
        { toastId: "create-playlist-success" }
      );
      setNewPlaylists([...newPlaylists, newPlaylist]);
    } catch (error) {
      toast.error(
        <ToastMsg
          title="Something went wrong"
          message={<>We could not import the collection: {error.toString()}</>}
        />,
        { toastId: "import-collection-error" }
      );
    }
    setImportingCollection(null);
  };

  return (
    <Modal
      {...bootstrapDialog(modal)}
      title="Import collection from MusicBrainz"
      aria-labelledby="ImportMBCollectionLabel"
      id="ImportMBCollectionModal"
    >
      <Modal.Header closeButton closeLabel="Done" onHide={resolveAndClose}>
        <Modal.Title id="ImportMBCollectionLabel">
          Import collection from MusicBrainz
        </Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <p className="text-muted">
          Import one or more of your MusicBrainz recording collections as
          playlists:
        </p>
        {(() => {
          if (loading) {
            return <Loader isLoading />;
          }
          if (collections.length === 0) {
            return (
              <p>No recording collections found on your MusicBrainz account.</p>
            );
          }
          return (
            <div
              className="list-group"
              style={{ maxHeight: "50vh", overflow: "auto" }}
            >
              {collections.map((collection: MBCollection) => (
                <button
                  type="button"
                  key={collection.gid}
                  className="list-group-item list-group-item-action"
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                  disabled={!!importingCollection}
                  name={collection.name}
                  onClick={() => importCollection(collection)}
                >
                  <span>{collection.name}</span>
                </button>
              ))}
            </div>
          );
        })()}
        {!!importingCollection && (
          <div>
            <p>Importing collection... It might take some time</p>
            <Loader isLoading={!!importingCollection} />
          </div>
        )}
      </Modal.Body>
      <Modal.Footer>
        <button
          type="button"
          className="btn btn-secondary"
          onClick={resolveAndClose}
        >
          Close
        </button>
      </Modal.Footer>
    </Modal>
  );
});
