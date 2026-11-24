"""Weather Agent - Demo Strands AI Agent with tool calling."""
import json
import boto3
from strands import Agent, tool


@tool
def get_weather(location: str) -> str:
    """Get current weather for a location.

    Args:
        location: City name or location to get weather for.
    """
    # Demo implementation - returns mock weather data
    weather_data = {
        "location": location,
        "temperature": "72\u00b0F",
        "conditions": "Partly Cloudy",
        "humidity": "45%",
        "wind": "10 mph NW",
    }
    return json.dumps(weather_data)


@tool
def get_forecast(location: str, days: int = 3) -> str:
    """Get weather forecast for a location.

    Args:
        location: City name or location.
        days: Number of forecast days (1-7).
    """
    forecasts = []
    conditions = ["Sunny", "Partly Cloudy", "Cloudy", "Rain", "Clear"]
    for i in range(min(days, 7)):
        forecasts.append({
            "day": i + 1,
            "conditions": conditions[i % len(conditions)],
            "high": f"{75 + i * 2}\u00b0F",
            "low": f"{55 + i}\u00b0F",
        })
    return json.dumps({"location": location, "forecasts": forecasts})


# Create the agent with Bedrock model
agent = Agent(
    model="${{ values.bedrockModelId }}",
    tools=[get_weather, get_forecast],
    system_prompt=(
        "You are a helpful weather assistant. Use the available tools "
        "to provide accurate weather information when asked."
    ),
)

if __name__ == "__main__":
    agent("What's the weather like in Seattle and what's the 3-day forecast?")
