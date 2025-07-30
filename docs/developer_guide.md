# ARTIST Developer Guide

This guide provides instructions for developers on how to extend the ARTIST system with new agents and tools.

## Getting Started

To get started, you will need to clone the ARTIST repository and set up a development environment. Please refer to the `README.md` file for instructions on how to do this.

## Extending the System

The ARTIST system is designed to be extensible, allowing you to add new agents and tools to meet your specific needs.

### Creating a New Agent

To create a new agent, you will need to create a new Python class that inherits from the `BaseAgent` class. Your new agent must implement the `execute` method, which is responsible for executing the agent's logic.

Once you have created your new agent, you will need to register it with the system by adding it to the `agent_registry` table in the database. This will make the agent available to the orchestration engine.

### Creating a New Tool

To create a new tool, you will need to create a new Python class that inherits from the `BaseTool` class. Your new tool must implement the `execute` method, which is responsible for executing the tool's logic.

Once you have created your new tool, you will need to register it with the system by adding it to the `tool_registry` table in the database. This will make the tool available to the agents.

## Contributing

We welcome contributions to the ARTIST project. If you would like to contribute, please fork the repository and submit a pull request.

When submitting a pull request, please make sure to include the following:

-   A clear and concise description of the changes you have made.
-   Unit tests for any new code you have added.
-   Documentation for any new features you have added.

We look forward to your contributions!
