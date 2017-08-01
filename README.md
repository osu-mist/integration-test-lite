# Integration Test Lite

Makes simple calls to APIs to confirm they return a 200 response code.
If any APIs don't return a 200, the exit code is 1 and the unsuccessful API calls are printed to STDOUT.

All API calls are made with a random query parameter and random value in order to bypass any caching.

## Instructions

1. Copy and rename [configuration_example.json](configuration_example.json) as configuration.json.

2. Build the Docker image
```
docker build -t integration-test-lite .
```

3. Run the Docker container
```
docker run --rm -v "$PWD"/configuration.json:/usr/src/app/configuration.json:ro integration-test-lite
```
