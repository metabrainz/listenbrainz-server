BEGIN;

CREATE TABLE artist_credit_redirect_array (
  artist_credit_cluster_id UUID NOT NULL, -- FK to artist_credit_cluster.cluster_id
  artist_mbids_array       UUID[] NOT NULL
);
ALTER TABLE artist_credit_redirect_array ADD CONSTRAINT artist_credit_redirect_array_artist_mbids_array_uniq UNIQUE (artist_mbids_array);

COMMIT;
