# Polling Mechanism Specification

This document describes how the application will poll the data source for new Counter-Strike updates.

## Polling Interval

The application will poll the JSON feed specified in `data-source.md` at a regular interval.

*   **Frequency:** Every one (1) minute.

## Logic

1.  **Scheduled Task:** A recurring task will be scheduled to trigger the polling process every minute.
2.  **Fetch Data:** On each trigger, the application will make an HTTP GET request to the specified URL.
3.  **Identify New Updates:**
    *   The application must keep track of the most recently seen update(s) to avoid re-posting old news.
    *   This could be achieved by storing the ID or timestamp of the last processed event.
    *   When new data is fetched, it will be compared against the stored identifier(s) to determine if there are any new, unannounced updates.
4.  **Process New Updates:** If new updates are found, they will be passed to the Reddit posting module.
5.  **Error Handling:** The polling mechanism should include robust error handling for:
    *   Network issues (e.g., unable to connect to the Steam server).
    *   HTTP errors (e.g., 4xx or 5xx responses).
    *   Unexpected data format from the server.
    *   Errors during the processing or storage of the last seen update identifier.
    Logging will be crucial for diagnosing issues with the polling process.

## Considerations

*   **Drift:** Long-term execution might lead to slight drifts in the polling interval. While minor drifts are acceptable, the scheduling mechanism should be reasonably accurate.
*   **Resource Usage:** Polling every minute is frequent. The HTTP request and subsequent processing should be efficient to minimize resource consumption.
*   **Missed Updates:** If the application is down for an extended period, it might miss updates when it restarts if the `count=100` parameter doesn't cover all missed events. The current specification assumes `count=100` and a 1-minute interval is sufficient to capture all updates even after short downtimes. For longer downtimes, a more sophisticated catch-up mechanism might be needed, but is out of scope for the initial design based on the provided requirements. 