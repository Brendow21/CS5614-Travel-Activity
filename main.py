

"""Main entry point for the Real-Time Travel Activity System"""

import os
import sys
import json
from dotenv import load_dotenv
from src.travel_system import RealTimeTravelActivitySystem
from src.utils import format_distance, logger

# Load environment variables from .env
load_dotenv()


def print_activity(activity, index: int = None):
    """
    Pretty-print a single activity in a clean readable format.

    Args:
        activity: Activity object
        index: Optional index number to display
    """
    prefix = f"{index}. " if index else ""

    print(f"{prefix}{activity.name}")
    print(f"   Rating: {activity.rating or 'N/A'} ({activity.user_ratings_total or 0} reviews)")
    print(f"   Address: {activity.address}")

    if activity.distance:
        print(f"   Distance: {format_distance(activity.distance)}")

    print(f"   Price: {activity.get_price_symbol()}")
    print(f"   Types: {', '.join(activity.types[:3])}")

    if activity.is_open_now():
        print(f"   Status: Open now")

    print()


def scenario_basic_search(system):
    """
    Scenario 1: Basic search for activities in Tokyo.
    """
    print("=" * 60)
    print("Scenario 1: Basic Search — Tokyo Activities")
    print("=" * 60)

    recommendation = system.recommend_activities(
        location_query="Tokyo, Japan",
        activity_types=["tourist_attraction", "restaurant", "museum"],
        radius=5000,
        max_per_type=3,
        sort_by="rating"
    )

    print(f"\nSearch Location: {recommendation.search_location}")
    print(f"Timestamp: {recommendation.timestamp}")
    print(f"Total Activities Found: {recommendation.total_count}\n")

    for i, activity in enumerate(recommendation.activities[:5], 1):
        print_activity(activity, i)

    return recommendation


def scenario_detailed_info(system, recommendation):
    """
    Scenario 2: Fetch detailed information for the top result.
    """
    if not recommendation.activities:
        return

    print("=" * 60)
    print("Scenario 2: Detailed Activity Information")
    print("=" * 60)

    first_activity = recommendation.activities[0]
    detailed = system.get_place_details(first_activity.place_id)

    if detailed:
        print(f"\n{detailed.name}")
        print(f"Rating: {detailed.rating} ({detailed.user_ratings_total} reviews)")
        print(f"Photos: {len(detailed.photos)}")

        if detailed.reviews:
            print("\nTop Reviews:")
            for review in detailed.reviews[:3]:
                print(f" - {review['author']} ({review['rating']}★)")
                print(f"   {review['text'][:100]}...")
            print()


def scenario_route_planning(system, recommendation):
    """
    Scenario 3: Route planning using a greedy algorithm.
    Produces a textual route summary and order of visits.
    """
    if not recommendation.activities:
        return

    print("=" * 60)
    print("Scenario 3: Route Planning")
    print("=" * 60)

    # Compute optimal route
    route = system.plan_route(
        activities=recommendation.activities[:5],
        start=recommendation.search_location
    )

    print(f"\nOptimized Route ({len(route)} stops):\n")

    for i, activity in enumerate(route, 1):
        print(f"{i}. {activity.name}")
        if activity.distance:
            print(f"   Dist. from start: {format_distance(activity.distance)}")
        print()

    print("Route Overview:\n")

    for i, activity in enumerate(route):
        if i == 0:
            print(f"START → {activity.name}")
        else:
            print(f"  ↓")
            print(f"{activity.name}")

    print("\nRoute planning complete.\n")


def scenario_personalized(system, recommendation):
    """
    Scenario 4: Personalized ranking based on user preferences.
    """
    if not recommendation.activities:
        return

    print("=" * 60)
    print("Scenario 4: Personalized Recommendations")
    print("=" * 60)

    user_preferences = {
        "museum": 0.9,
        "tourist_attraction": 0.7,
        "restaurant": 0.5,
        "park": 0.3
    }

    personalized = system.personalized_recommend(
        user_preferences=user_preferences,
        activities=recommendation.activities
    )

    print("Top Personalized Results:\n")

    for i, activity in enumerate(personalized[:5], 1):
        print_activity(activity, i)


def scenario_map_generation(system, recommendation):
    """
    Scenario 5: Generate a dynamic HTML map using Google Maps JavaScript API.
    The HTML file is saved locally (server-side).
    """
    if not recommendation.activities:
        return

    print("=" * 60)
    print("Scenario 5: Generating Dynamic Map")
    print("=" * 60)

    html = system.generate_map_url(
        activities=recommendation.activities[:10],
        center=recommendation.search_location
    )

    filepath = "dynamic_map.html"
    abs_path = os.path.abspath(filepath)

    with open(abs_path, "w", encoding="utf-8") as f:
        f.write(html.lstrip())

    print(f"\nDynamic map saved to: {abs_path}")
    print("Open this file on your local machine to view the interactive map.\n")


def save_results(recommendation, filename: str = "results.json"):
    """
    Save recommendation results to a JSON file.
    """
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(recommendation.to_dict(), f, ensure_ascii=False, indent=2)
    print(f"Results saved to {filename}")


def main():
    """
    Program entry point.
    Loads API key, initializes the system, and runs all scenarios.
    """
    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        print("ERROR: GOOGLE_API_KEY not set.")
        sys.exit(1)

    config_path = "config/config.yaml" if os.path.exists("config/config.yaml") else None
    system = RealTimeTravelActivitySystem(api_key=api_key, config_path=config_path)

    print("\nReal-Time Travel Activity System\n")

    try:
        recommendation = scenario_basic_search(system)

        scenario_detailed_info(system, recommendation)

        scenario_route_planning(system, recommendation)

        scenario_personalized(system, recommendation)

        scenario_map_generation(system, recommendation)

        save_results(recommendation)

        print("\nAll scenarios completed successfully.\n")

    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
