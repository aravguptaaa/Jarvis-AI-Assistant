# actions.py

import subprocess
import json

def open_application(app_name: str) -> str:
    """
    Opens a specified application on macOS using AppleScript.

    Args:
        app_name (str): The name of the application to open (e.g., "Google Chrome", "Spotify").

    Returns:
        str: A confirmation or error message.
    """
    try:
        # Sanitize app_name to prevent command injection, although AppleScript is generally safe.
        clean_app_name = app_name.replace('"', '')
        script = f'tell application "{clean_app_name}" to activate'
        subprocess.run(["osascript", "-e", script], check=True, capture_output=True)
        return f"Opening {clean_app_name} for you, sir."
    except subprocess.CalledProcessError:
        return f"My apologies, I was unable to find or open the application named {app_name}."
    except Exception as e:
        return f"An unexpected error occurred: {e}"

def search_files_on_mac(query: str) -> str:
    """
    Searches for files on macOS using the 'mdfind' command.

    Args:
        query (str): The search term for the files.

    Returns:
        str: A summary of the top 5 search results or a not-found message.
    """
    try:
        # mdfind is the command-line interface for Spotlight search.
        result = subprocess.check_output(["mdfind", query], text=True).strip()
        if not result:
            return f"I couldn't find any files matching '{query}', sir."
        
        # Return the top 5 results for a concise response.
        first_five_results = "\n".join(result.splitlines()[:5])
        return f"I found the following files related to '{query}':\n{first_five_results}"
    except Exception as e:
        return f"An error occurred during the file search: {e}"

def get_calendar_events() -> str:
    """
    Retrieves today's events from the macOS Calendar app using AppleScript.

    Returns:
        str: A summary of today's calendar events.
    """
    # AppleScript to get today's events from the user's primary calendar.
    script = """
    set today to current date
    set tomorrow to today + (1 * days)
    tell application "Calendar"
        tell calendar 1
            set theEvents to (every event whose start date is greater than or equal to today and start date is less than tomorrow)
            set eventList to {}
            repeat with anEvent in theEvents
                set the end of eventList to summary of anEvent & " at " & short time string of (start date of anEvent)
            end repeat
            return eventList
        end tell
    end tell
    """
    try:
        result = subprocess.check_output(["osascript", "-e", script], text=True).strip()
        if not result:
            return "You have no events on your calendar for today, sir."
        else:
            events = result.replace(", ", "\n- ")
            return f"Here are your events for today:\n- {events}"
    except Exception as e:
        return f"I had trouble accessing your calendar. The error was: {e}"

def get_battery_level() -> str:
    """
    Checks the current battery level and charging status on macOS using 'pmset'.

    Returns:
        str: A human-readable string describing the battery status.
    """
    try:
        # 'pmset -g batt' is the command to get power management settings, specifically battery.
        result = subprocess.check_output(["pmset", "-g", "batt"], text=True)
        level = result.split('\t')[1].split(';')[0]
        status = result.split(';')[1].strip()
        return f"The current battery is at {level}, and is currently {status}."
    except Exception as e:
        return f"My apologies, I was unable to retrieve the battery status."
