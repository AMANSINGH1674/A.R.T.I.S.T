document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('workflow-form');
    const userRequestInput = document.getElementById('user-request');
    const statusUpdates = document.getElementById('status-updates');
    const resultsOutput = document.getElementById('results-output');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const userRequest = userRequestInput.value;
        if (!userRequest) return;
        
        // Clear previous results
        statusUpdates.innerHTML = '<p><i>Starting workflow...</i></p>';
        resultsOutput.innerHTML = '<code></code>';
        
        try {
            // **Step 1: Get access token (replace with your login logic)**
            const accessToken = "your_jwt_token_here"; // In a real app, you'd get this from a login form

            // **Step 2: Start workflow execution**
            const startResponse = await fetch('/api/v1/workflow/execute', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${accessToken}`
                },
                body: JSON.stringify({ user_request: userRequest, workflow_id: 'default' })
            });

            if (!startResponse.ok) {
                throw new Error(`Error starting workflow: ${startResponse.statusText}`);
            }

            const startData = await startResponse.json();
            const taskId = startData.task_id;
            statusUpdates.innerHTML = `<p><i>Workflow started with task ID: ${taskId}</i></p>`;

            // **Step 3: Poll for status and results**
            const pollInterval = setInterval(async () => {
                const statusResponse = await fetch(`/api/v1/workflow/status/${taskId}`);
                const statusData = await statusResponse.json();

                if (statusData) {
                    const statusMessage = statusData.info?.status || statusData.status;
                    statusUpdates.innerHTML += `<p><i>${statusMessage}</i></p>`;
                }

                if (statusData.status === 'completed' || statusData.status === 'SUCCESS') {
                    clearInterval(pollInterval);
                    
                    // Get final results
                    const resultResponse = await fetch(`/api/v1/workflow/result/${taskId}`);
                    const resultData = await resultResponse.json();
                    resultsOutput.innerHTML = `<code>${JSON.stringify(resultData, null, 2)}</code>`;
                
                } else if (statusData.status === 'failed' || statusData.status === 'FAILURE') {
                    clearInterval(pollInterval);
                    resultsOutput.innerHTML = `<code>Error: ${statusData.info}</code>`;
                }

            }, 3000);

        } catch (error) {
            statusUpdates.innerHTML = `<p><i>Error: ${error.message}</i></p>`;
            console.error("Error:", error);
        }
    });
});
