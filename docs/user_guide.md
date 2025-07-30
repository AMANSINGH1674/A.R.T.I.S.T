# ARTIST User Guide

This guide provides instructions for end-users on how to interact with the ARTIST system.

## Getting Started

To get started, you will need an account with the appropriate permissions. Please contact your system administrator to create an account for you.

## Interacting with the System

There are two main ways to interact with the ARTIST system:

1.  **Web UI**: The web UI provides a user-friendly interface for executing workflows and viewing results. To access the web UI, open your web browser and navigate to the URL provided by your system administrator.
2.  **API**: The API provides a programmatic way to interact with the system. This is useful for integrating ARTIST with other systems or for automating tasks.

### Using the Web UI

1.  Open the web UI in your web browser.
2.  Enter your request in the text box.
3.  Click the "Execute Workflow" button.
4.  The system will start executing the workflow. You can view the status of the workflow in the "Workflow Status" section.
5.  Once the workflow is complete, the results will be displayed in the "Results" section.

### Using the API

To use the API, you will need to obtain a JWT token by authenticating with the `/auth/login` endpoint. Once you have a token, you can use it to access the other API endpoints.

For more information on how to use the API, please refer to the API documentation.

## Providing Feedback

Your feedback is important for improving the performance of the ARTIST system. You can provide feedback on workflow executions using the `/rlhf/feedback` endpoint.

When providing feedback, you can include a rating, text feedback, or a comparison between two different outputs. This feedback will be used to train the system and improve its performance over time.
