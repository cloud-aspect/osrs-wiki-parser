# File: /ca-python/ca-python/src/fetch.py
import csv
import subprocess
from bs4 import BeautifulSoup
from selenium import webdriver

# from selenium.webdriver.chrome.service import Service
# from selenium.common.exceptions import TimeoutException, WebDriverException
import time

URL = "https://oldschool.runescape.wiki/w/Combat_Achievements/All_tasks"
COOKIE = {"name": "RSN", "value": "Echo_Jaggi", "domain": "oldschool.runescape.wiki"}

options = webdriver.ChromeOptions()
options.timeouts = {"implicit": 10}
service = webdriver.ChromeService(
    service_args=["--log-level=INFO"], log_output=subprocess.STDOUT
)

driver = webdriver.Chrome(options=options, service=service)


try:
    driver.get(URL)  # Load domain first to set cookie
    driver.add_cookie(COOKIE)

    # Wait until .wikisync-success element appears
    loaded = False
    start_time = time.time()
    while not loaded:
        if driver.find_elements("css selector", ".wikisync-success"):
            loaded = True
        else:
            time.sleep(1)
            if time.time() - start_time > 30:
                print("Timeout waiting for WikiSync to complete.")
                with open(
                    "debug/debug_timeout_page_source.html", "w", encoding="utf-8"
                ) as file:
                    file.write(driver.page_source)
                print("debug/timeout_page_source.html saved for inspection.")
                exit(1)

    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")

    with open("debug/timeout_page_source.html", "w", encoding="utf-8") as file:
        file.write(html)
    print("HTML content saved to combat_achievements_raw.html")

    # look for a <table> whose class list contains both "qc-active" and "ca-tasks"
    table = soup.find(
        "table",
        attrs={
            "class": lambda classes: (
                classes and "qc-active" in classes and "ca-tasks" in classes
            )
        },
    )

    # if nothing was found, bail out
    if table is None:
        # Page doesn't have Combat Achievement tasks on it
        print("No Combat Achievement tasks found on the page.")
        exit(1)
    # If we found the table, we can proceed to parse it

    # Log table html for debugging
    print(table.prettify())  # Uncomment for debugging if needed
    # Write table html to a file for inspection
    # with open("debug/combat_achievements_table.html", "w", encoding="utf-8") as f:
    #     f.write(str(table))

    # Prepare CSV writer
    writer = csv.writer(open("combat_achievements.csv", "w", newline=""))
    writer.writerow(["Done", "Boss", "Name", "Description", "Type", "Points"])

    for row in table.select("tr"):
        cols = row.find_all("td")
        if len(cols) != 5:
            continue  # skip header or malformed rows

        # detect highlight by specific class
        style = row.get("style", "")
        done = "True" if ("highlight-on" in row.get("class", [])) else "False"

        boss = cols[0].get_text(strip=True)
        name = cols[1].get_text(strip=True)
        desc = cols[2].get_text(strip=True)
        typ = cols[3].get_text(strip=True)
        # tier text like "Easy (1 pt)" → extract number before "pt"
        points_text = cols[4].get_text()
        points = points_text.split("pt")[0].split()[-1]

        writer.writerow([done, boss, name, desc, typ, points])

    print("CSV written to combat_achievements_achievements.csv")

finally:
    print("\nBrowser log...")
    print(driver.get_log("browser"), "\n\n")
    driver.quit()
    print("Browser closed.")
