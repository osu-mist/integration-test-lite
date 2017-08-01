# Integration Test Lite

Makes simple calls to APIs to confirm they return a 200 response code.
If any APIs don't return a 200, the programs exit code is 1 and the unsuccessful API calls are printed to STDOUT.

All API calls are made with a random query parameter and random value in order to bypass any caching.

## Instructions
