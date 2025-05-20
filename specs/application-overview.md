# Application Overview

This document outlines the general purpose and functionality of the Counter-Strike Update Announcer application.

## Purpose

The primary goal of this application is to monitor Counter-Strike 2 (CS2) game updates and automatically announce them on Reddit. This provides a timely notification service for the CS2 community.

## Core Functionality

1.  **Poll for Updates:** Regularly check a designated Steam event feed for new CS2 update announcements.
2.  **Parse Updates:** Extract relevant information from the new announcements.
3.  **Post to Reddit:** Format the extracted information and post it as a new submission to a specified subreddit.
4.  **Logging:** Maintain detailed logs of its operations, including successful posts, errors, and polling activity.

## Technology Stack (Key Components)

*   **Language:** Python
*   **HTTP Requests:** `httpx`
*   **CLI Output:** `rich`
*   **Data Structures:** Python `dataclasses`
*   **Logging:** `loguru` 