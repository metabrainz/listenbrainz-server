import React from "react";
import NiceModal, { bootstrapDialog, useModal } from "@ebay/nice-modal-react";
import { Modal } from "react-bootstrap";
import { toast } from "react-toastify";
import { useNavigate } from "react-router";

import GlobalAppContext from "../../../utils/GlobalAppContext";
import { ToastMsg } from "../../../notifications/Notifications";
import Loader from "../../../components/Loader";
import type { MusicBrainzCollectionSummary } from "../../../utils/APIService";

export default NiceModal.create(() => {
  const modal = useModal();
  const navigate = useNavigate();
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

  const openCollection = (collectionMbid: string) => {
    close();
    navigate(`/collection/${collectionMbid}`);
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
          {collections.map((collection) => (
            <button
              type="button"
              key={collection.mbid}
              className="list-group-item list-group-item-action"
              disabled={isLoading}
              onClick={() => openCollection(collection.mbid)}
            >
              <div style={{ fontWeight: 600 }}>{collection.name}</div>
              <div className="text-muted">
                {collection.item_count} recordings
              </div>
            </button>
          ))}
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
