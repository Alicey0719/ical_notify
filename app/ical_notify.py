import requests
import os
from icalendar import Calendar
from deepdiff import DeepDiff
from dotenv import load_dotenv
from utils.sendwebhook import SendWebhook

# load env
load_dotenv()
ICAL_URL = os.environ.get("ICAL_URL")
PREVIOUS_ICAL_FILE = os.environ.get("PREVIOUS_ICAL_FILE", "previous_ical.ics")

def fetch_ical(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.content

def parse_ical(content):
    """iCalをパースして、イベントの一覧を辞書で取得する"""
    calendar = Calendar.from_ical(content)
    events = {}
    for component in calendar.walk():
        if component.name == "VEVENT":
            event_id = component.get("uid")
            events[event_id] = {
                "summary": component.get("summary"),
                "start": component.get("dtstart").dt,
                "end": component.get("dtend").dt,
                "description": component.get("description"),
                "location": component.get("location")
            }
    return events

def load_previous_ical():
    if not os.path.exists(PREVIOUS_ICAL_FILE):
        return None
    with open(PREVIOUS_ICAL_FILE, "rb") as f:
        content = f.read()
    return content

def save_ical(content):
    with open(PREVIOUS_ICAL_FILE, "wb") as f:
        f.write(content)

def format_diff(diff, previous_events, current_events):
    """DeepDiffの結果をStrで整形する"""
    messages = []

    # added event
    added_keys = diff.get("dictionary_item_added", [])
    for key_path in added_keys:
        event_id = key_path.split("'")[1]
        event = current_events.get(event_id, {})
        messages.append(f"New: {event.get('summary')} | Date: {event.get('start')}-{event.get('end')}")

    # deleted event
    removed_keys = diff.get("dictionary_item_removed", [])
    for key_path in removed_keys:
        event_id = key_path.split("'")[1]
        event = previous_events.get(event_id, {})
        messages.append(f"Delete: {event.get('summary')} | Date: {event.get('start')}-{event.get('end')}")

    # changed event
    changed_events = diff.get("values_changed", {})
    for path, change in changed_events.items():
        path_parts = path.split("'")
        event_id = path_parts[1]
        event = previous_events.get(event_id, {})
        attribute = path_parts[3]  # 変更された属性名
        old_value = change["old_value"]
        new_value = change["new_value"]
        messages.append(f"Change: {event.get('summary')} | {attribute} | old: {old_value} | new: {new_value}")

    return "\n".join(messages)

def main():
    if ICAL_URL is None:
        print("ICAL_URL is not found.")
        return

    webhook_url = os.environ.get("WEBHOOK_URL", None)
    try:
        if webhook_url is None:
            raise Exception(f"WEBHOOK_URL is not found: {webhook_url}")
    except:
        traceback.print_exc()

    sw = SendWebhook(webhook_url)
    sw.username = os.environ.get("MESSAGE_USERNAME", "iCal Notify")
    sw.avatar_url = os.environ.get("MESSAGE_AVATAR_URL", "")
    sw.author_name = os.environ.get("MESSAGE_AUTHORNAME", "iCal Notify")
    sw.author_icon_url = os.environ.get("MESSAGE_AUTHORICON_URL", "")
    sw.author_url = os.environ.get("MESSAGE_AUTHOR_URL", "")

    # get current iCal file
    current_content = fetch_ical(ICAL_URL)

    # get previous iCal file
    previous_content = load_previous_ical()

    if previous_content is None:
        print("No previous data. Save current data.")
        save_ical(current_content)
        return

    # parse iCal file
    previous_events = parse_ical(previous_content)
    current_events = parse_ical(current_content)

    # compare iCal files
    diff = DeepDiff(previous_events, current_events, ignore_order=True)

    # send&print message
    if diff:
        formatted_diff = format_diff(diff, previous_events, current_events)
        sw.send_embed_message(formatted_diff, level_color=sw.Level.info)
        print("Calender diff:\n" + formatted_diff)
    else:
        print("Nothing has changed.")

    # save current iCal file
    save_ical(current_content)

if __name__ == "__main__":
    main()
