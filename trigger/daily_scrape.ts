import { logger, schedules } from "@trigger.dev/sdk/v3";

// Define the daily scraping task
export const dailyScrapingTask = schedules.task({
    id: "daily-scraping-job",
    // Run daily at 2:00 AM UTC (adjust cron as needed)
    cron: "0 2 * * *",
    run: async (payload) => {
        logger.info("Starting Daily Scraping Job via Trigger.dev", { payload });

        // The URL of your deployed FastAPI backend
        // When running locally, you might use http://localhost:8000
        // When deployed, set this env var to your public URL
        const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
        const scrapeEndpoint = `${backendUrl}/api/v1/scraper/trigger`;

        logger.info(`Triggering scraper at: ${scrapeEndpoint}`);

        try {
            const response = await fetch(scrapeEndpoint, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    // Add authentication header here if you implemented protection
                    // "Authorization": "Bearer " + process.env.API_SECRET 
                },
            });

            if (!response.ok) {
                const errorText = await response.text();
                logger.error("Failed to trigger scraper", { status: response.status, error: errorText });
                throw new Error(`Scraper API returned ${response.status}: ${errorText}`);
            }

            const data = await response.json();
            logger.info("Scraper triggered successfully", { data });

            return {
                status: "success",
                message: "Scraping job initiated",
                jobId: data.job_id // Assuming backend returns a job/task ID
            };

        } catch (error) {
            logger.error("Network error triggering scraper", { error });
            throw error;
        }
    },
});
