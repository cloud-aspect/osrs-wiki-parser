import csv
import json
import requests
from bs4 import BeautifulSoup
import argparse


def download_all_tasks_csv(outpath="combat_achievements.csv"):
    URL = "https://oldschool.runescape.wiki/w/Combat_Achievements/All_tasks"

    response = requests.get(URL)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Log the page source for debugging
    with open("debug/combat_achievements_raw.html", "w", encoding="utf-8") as file:
        file.write(soup.prettify())

    # Find the table with class ca-tasks
    table = soup.find(
        "table", {"class": "wikitable lighttable sortable qc-active ca-tasks"}
    )

    if table is None:
        print("No Combat Achievement tasks found on the page.")
        exit(1)

    with open(outpath, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Boss", "Name", "Description", "Type", "Points", "ID"])

        # Get each table row with class data-class-id and write to CSV
        for row in table.select("tr[data-ca-task-id]"):
            cols = row.find_all("td")
            if len(cols) != 6:
                continue  # skip malformed rows

            task_id = row["data-ca-task-id"]
            boss = cols[0].get_text(strip=True)
            name = cols[1].get_text(strip=True)
            desc = cols[2].get_text(strip=True)
            typ = cols[3].get_text(strip=True)
            points_text = cols[4].get_text()
            points = "".join(filter(str.isdigit, points_text))

            writer.writerow([boss, name, desc, typ, points, task_id])

    print(f"CSV written to {outpath}")


def fetch_wikisync_json(rsn):
    """
    Fetches and saves sync JSON data for an OSRS player.

    Args:
        rsn (str): The OSRS name.
        output_path (str, optional): The output file path. Defaults to None.

    Returns:
        None
    """
    url = f"https://sync.runescape.wiki/runelite/player/{rsn}/STANDARD"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://sync.runescape.wiki/",
    }

    response = requests.get(url, headers=headers)

    if not response.ok:
        print(
            f"HTTP error! status: {response.status_code}, statusText: {response.reason}"
        )
        return

    data = response.json()

    outPath = f"debug/wikisync_{rsn}.json"

    with open(outPath, "w") as file:
        json.dump(data, file, indent=2)

    print(f"JSON data written to {outPath}")

    return data.get("combat_achievements", [])


def add_completed_column(csv_file, wikisync_data):
    with open(csv_file, "r") as file:
        reader = csv.DictReader(file)
        rows = [row for row in reader]

    with open(csv_file, "w", newline="") as file:
        original_fieldnames = list(rows[0].keys())
        fieldnames = ["Completed"] + original_fieldnames
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        writer.writeheader()
        for row in rows:
            new_row = {"Completed": int(row["ID"]) in wikisync_data}
            new_row.update({key: value for key, value in row.items() if key != "ID"})
            new_row["ID"] = row["ID"]
            writer.writerow(new_row)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--tasks-only",
        action="store_true",
        help="Only download the Combat Achievements JSON data to a CSV file",
    )
    parser.add_argument(
        "--wikisync-only",
        action="store_true",
        help="Only download the WikiSync JSON data for the OSRS player",
    )
    parser.add_argument(
        "osrs_name", nargs="?", help="OSRS name to fetch wikisync JSON data for"
    )

    args = parser.parse_args()

    if args.tasks_only:
        download_all_tasks_csv("debug/combat_achievements_tasks.csv")
    elif args.wikisync_only:
        if not args.osrs_name:
            print("Please provide an OSRS name")
            exit(1)
        wikisync_data = fetch_wikisync_json(args.osrs_name)
    else:
        if not args.osrs_name:
            print("Please provide an OSRS name")
            exit(1)
        download_all_tasks_csv("combat_achievements.csv")
        wikisync_data = fetch_wikisync_json(args.osrs_name)
        add_completed_column("combat_achievements.csv", wikisync_data)
