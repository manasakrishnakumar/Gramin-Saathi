import { defineConfig } from "@trigger.dev/sdk/v3";

export default defineConfig({
    project: "proj_emmrkmcclbrrzqhdfqdq", // Your Project ID
    runtime: "node",
    logLevel: "log",
    // Set the maxDuration to 300 seconds (5 minutes) to give scraper time
    maxDuration: 300,
    retries: {
        enabledInDev: true,
        default: {
            maxAttempts: 3,
            minTimeoutInMs: 1000,
            maxTimeoutInMs: 10000,
            factor: 2,
            randomize: true,
        },
    },
});
