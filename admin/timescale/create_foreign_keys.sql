BEGIN;

ALTER TABLE messybrainz.submissions_redirect
    ADD CONSTRAINT messybrainz_submissions_msid_foreign_key
    FOREIGN KEY (original_msid)
    REFERENCES messybrainz.submissions (gid)
    ON DELETE NO ACTION;



COMMIT;
