BEGIN;

ALTER TABLE listen_json ADD CONSTRAINT listen_json_id_foreign_key FOREIGN KEY (id) REFERENCES "listen" (id); 

COMMIT;
