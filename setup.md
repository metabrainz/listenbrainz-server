# Local Setup Guide for ListenBrainz Server

This guide provides step-by-step instructions on how to set up and start the local development server for ListenBrainz using Docker, so you can test your changes locally. 

**Note**: You must be in the `listenbrainz-server` directory to run these commands (`cd /Users/swaimsahay/listenbrainz-server`).

### 1. Build the Docker Containers
*Run this only the first time you set up the project, or after adding new dependencies.*
```bash
./develop.sh build
```

### 2. Initialize the Databases
*Run this only the first time you set up the project.*
```bash
./develop.sh manage init_db --create-db
./develop.sh manage init_ts_db --create-db
```

### 3. Start the Server
*Run this every time you want to start the local server to test your code.*
```bash
./develop.sh up
```
Once it finishes starting, open your browser and go to: **[http://localhost:8100](http://localhost:8100)**

*(To stop the server, press `Ctrl + C` in your terminal)*

### 4. Run the Tests
*Run this before committing new code to ensure your changes didn't break anything.*
```bash
./test.sh
```

---

### Other Useful Commands:
- Start the server in the background: `./develop.sh up -d`
- Stop the background server: `./develop.sh down`
- Apply static/JS/CSS changes (rebuild builder): `./develop.sh build static_builder`
- Apply Python dependency changes (rebuild web): `./develop.sh build web`
