# ARTIST API Documentation

This documentation provides a detailed overview of the ARTIST API, including all available endpoints, request/response models, and authentication requirements.

## Base URL

The base URL for all API endpoints is:

```
/api/v1
```

## Authentication

All API endpoints (except for `/auth/login` and `/monitoring/health`) require a valid JWT token to be included in the `Authorization` header as a bearer token:

```
Authorization: Bearer <your_jwt_token>
```

## Endpoints

### Authentication

- **POST /auth/login**: Authenticate a user and receive a JWT token.
- **GET /auth/profile**: Get the profile of the currently authenticated user.

### Workflow Management

- **POST /workflow/execute**: Start a new workflow execution asynchronously.
- **GET /workflow/status/{task_id}**: Get the status of a workflow execution.
- **GET /workflow/result/{task_id}**: Get the result of a completed workflow execution.

### Agent Management

- **GET /agents/list**: List all available agents.
- **GET /agents/{agent_name}**: Get information about a specific agent.

### Tool Management

- **GET /tools/list**: List all available tools.
- **GET /tools/{tool_name}**: Get information about a specific tool.

### Monitoring

- **GET /monitoring/health**: Get the health status of all system components.
- **GET /monitoring/metrics**: Get Prometheus metrics.
- **GET /monitoring/status**: Get the overall status of the ARTIST system.

### RLHF

- **POST /rlhf/feedback**: Submit feedback for a workflow execution.
- **POST /rlhf/train**: Trigger RLHF training.
- **GET /rlhf/training/status**: Get the status of the RLHF training system.

For more details on the request and response models, please refer to the OpenAPI documentation at `/docs`.
