import React from "react";
import NiceModal, { bootstrapDialog, useModal } from "@ebay/nice-modal-react";
import { Modal } from "react-bootstrap";
import { toast } from "react-toastify";

import GlobalAppContext from "../../../utils/GlobalAppContext";
import { ToastMsg } from "../../../notifications/Notifications";
import Loader from "../../../components/Loader";
import type { MusicBrainzCollectionSummary } from "../../../utils/APIService";

export default NiceModal.create(() => {
  const modal = useModal();
  const { APIService, currentUser } = React.useContext(GlobalAppContext);

  const [collections, setCollections] = React.useState<
    MusicBrainzCollectionSummary[]
  >([]);
  const [isLoading, setIsLoading] = React.useState(false);

  React.useEffect(() => {
    async function loadCollections() {
      if (!currentUser?.auth_token) {
        toast.error(
          <ToastMsg
            title="Error"
            message="You must be logged in for this operation"
          />,
          { toastId: "auth-error" }
        );
        return;
      }

      setIsLoading(true);
      try {
        const result = await APIService.getMusicBrainzCollections(
          currentUser.auth_token
        );
        setCollections(result);
      } catch (error) {
        toast.error(
          <ToastMsg
            title="Error loading collections"
            message={error?.message ?? error}
          />,
          { toastId: "load-collections-error" }
        );
      } finally {
        setIsLoading(false);
      }
    }

    loadCollections();
  }, [APIService, currentUser]);

  const close = () => {
    modal.hide();
  };

  return (
    <Modal
      {...bootstrapDialog(modal)}
      title="Import collections from MusicBrainz"
      aria-labelledby="ImportMBCollectionsModalLabel"
      id="ImportMBCollectionsModal"
    >
      <Modal.Header closeButton>
        <Modal.Title id="ImportMBCollectionsModalLabel">
          Import collections from MusicBrainz
        </Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <div
          className="list-group"
          style={{ maxHeight: "50vh", overflow: "auto" }}
        >
          {!isLoading && collections.length === 0 ? (
            <p className="text-center text-muted mb-0">
              No recording collections found
            </p>
          ) : (
            collections.map((collection) => (
              <div key={collection.mbid} className="list-group-item">
                <div style={{ fontWeight: 600 }}>{collection.name}</div>
                <div className="text-muted">
                  {collection.item_count} recordings
                </div>
              </div>
            ))
          )}
        </div>
        <Loader isLoading={isLoading} />
      </Modal.Body>
      <Modal.Footer>
        <button type="button" className="btn btn-secondary" onClick={close}>
          Close
        </button>
      </Modal.Footer>
    </Modal>
  );
});
