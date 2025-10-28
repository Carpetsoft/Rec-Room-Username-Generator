import cloudscraper
import json
import random
from datetime import datetime
import os
import threading

scraper = cloudscraper.create_scraper()

class Scraper:
    uniqueUsernames = set()
    lock = threading.Lock()

    BEARER = "eyJhbGciOiJSUzI1NiIsImtpZCI6Ill3ckZ1MFFYTmp5SWhxZXBIN0dlamZwOE9nTSIsInR5cCI6ImF0K2p3dCIsIng1dCI6Ill3ckZ1MFFYTmp5SWhxZXBIN0dlamZwOE9nTSJ9.eyJuYmYiOjE3NTg1NTc2MDQsImV4cCI6MTc1ODU2MTIwNCwiaXNzIjoiaHR0cHM6Ly9hdXRoLnJlYy5uZXQiLCJjbGllbnRfaWQiOiJyZWNuZXQiLCJyb2xlIjoid2ViQ2xpZW50Iiwic3ViIjoiMzgxMjMzNDk2IiwiYXV0aF90aW1lIjoxNzU4NTM3ODcyLCJpZHAiOiJsb2NhbCIsImp0aSI6IjcwOTdEMUEzRjhFMEMwQjE1OTIxNkZGRDVGRDE0QTUzIiwiaWF0IjoxNzU4NTU3NjA0LCJzY29wZSI6WyJvcGVuaWQiLCJybiIsIm9mZmxpbmVfYWNjZXNzIl0sImFtciI6WyJwd2QiXX0.ubHHobocW3xw6BmLuac76U0RArYysSopxG7Cb_S0uzEJAJpIc3swZ4g6PIYsxz6eSMgIxKBjYholzju2WNa8FWh1M70-oIB2aIX_zcYwteC9TIhe45m44oU9csEXSq9QH37GrHZnVlwgGhYqP58vG5JG3ulPf2Lf_FpkRixaGJjX6k-cslRASeP9nd0U0n_j-0kzBId_R7PCsEtMHucPThZOuqMojmbkJ8KfXlkWgsrZpZqtvhARES4Zd4F1c8L_E1LltKL98jsMCKh8TC44UTCLWiEoWwRiSeJAd1ytg0rNNgujemL2TETm2beyBHpbetf06jsCwm_aHwBFS-9oWA"

    @staticmethod
    def scraping(year, minLevel, amount):
        yearIds = {
            2016: (5, 69723),
            2017: (69724, 386114),
            2018: (386115, 1290001),
            2019: (1290002, 3314552),
            2020: (3314553, 11159630)
        }

        if year not in yearIds:
            print(f"[-] Data for year {year} is not available.")
            return

        minId, maxId = yearIds[year]

        try:
            with open("config.json", "r") as f:
                config = json.load(f)
        except Exception as e:
            print(f"[-] Failed to load config.json: {e}")
            return

        numThreads = int(config.get("amount_of_threads", 1))
        print(f"[+] Using {numThreads} threads.")

        scrapedUsernames = []
        usedIds = set()
        threads = []

        for i in range(numThreads):
            print(f"[+] Starting thread #{i+1}")
            t = threading.Thread(target=Scraper.scrapeThread, args=(scrapedUsernames, usedIds, minLevel, amount, minId, maxId))
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        print(f"[+] Scraping complete. Total usernames scraped: {len(scrapedUsernames)}")
        Scraper.saveUsrToFile(scrapedUsernames)

    @staticmethod
    def scrapeThread(scrapedUsernames, usedIds, minLevel, amount, minId, maxId):
        while True:
            with Scraper.lock:
                if len(scrapedUsernames) >= amount:
                    print("[-] Thread exiting, target reached.")
                    return

            ids = []
            with Scraper.lock:
                while len(ids) < 50:
                    randomId = random.randint(minId, maxId)
                    if randomId not in usedIds:
                        ids.append(randomId)
                        usedIds.add(randomId)
            print(f"[+] Generated {len(ids)} unique IDs.")

            playerData = Scraper.getPlrData(ids)
            if not playerData:
                print("[-] No player data returned.")
                continue

            for player in playerData:
                try:
                    playerId = int(player["PlayerId"])
                    level = int(player["Level"])
                except (KeyError, ValueError) as e:
                    print(f"[-] Bad player data format: {e}")
                    continue

                if level < minLevel:
                    continue

                playerInfo = Scraper.getUsername(playerId)
                if playerInfo and "username" in playerInfo:
                    playerInfo["Level"] = level
                    playerInfo["createdAt"] = playerInfo.get("createdAt", "N/A")
                    username = playerInfo["username"]

                    with Scraper.lock:
                        if username not in Scraper.uniqueUsernames and len(scrapedUsernames) < amount:
                            scrapedUsernames.append(playerInfo)
                            Scraper.uniqueUsernames.add(username)

                            print(f"[{datetime.now().strftime('%H:%M:%S')}] {username} | Level {level} | Created At: {playerInfo['createdAt']}")

                            if len(scrapedUsernames) >= amount:
                                return

    @staticmethod
    def getPlrData(ids):
        url = "https://api.rec.net/api/players/v2/progression/bulk"
        params = "&".join([f"id={i}" for i in ids])
        FullUrl = f"{url}?{params}"
        print(f"[DEBUG] Fetching player data from: {FullUrl}")

        try:
            response = scraper.get(FullUrl)
            print(f"[DEBUG] Status Code (PlayerData): {response.status_code}")
            if response.status_code == 200:
                return response.json()
            else:
                print(f"[ERROR] Failed to get player data. Response: {response.text}")
        except Exception as e:
            print(f"[ERROR] Exception in getPlrData: {e}")
        return None

    @staticmethod
    def getUsername(playerId):
        url = f"https://accounts.rec.net/account/{playerId}"
        headers = {
            "Authorization": f"Bearer {Scraper.BEARER}"
        }

        # print(f"[-] Getting username for PlayerID {playerId}")
        try:
            response = scraper.get(url, headers=headers)
            # print(f"[/] Status Code (Username): {response.status_code}")
            if response.status_code == 200:
                return response.json()
            else:
                print(f"[ERROR] Failed to get username for PlayerID {playerId}. Response: {response.text}")
        except Exception as e:
            print(f"[ERROR] Exception in getUsername: {e}")
        return None

    @staticmethod
    def saveUsrToFile(scrapedUsernames):
        filename = "usernames.txt"
        num = 0

        while os.path.exists(filename):
            num += 1
            filename = f"usernames_{num}.txt"

        try:
            with open(filename, "w") as f:
                for user in scrapedUsernames:
                    username = user["username"]
                    level = user["Level"]
                    createdAt = user.get("createdAt", "N/A")
                    f.write(f"Username: {username} | Level: {level} | Created At: {createdAt}\n")
            print(f"[+] Saved usernames to {filename}")
        except Exception as e:
            print(f"[-] Could not write to file: {e}")

if __name__ == "__main__":
    year = int(input("Enter the year (2016-2020): "))
    if year < 2016 or year > 2020:
        print("[-] Only years 2016-2020 are supported.")
    else:
        minLevel = int(input("Enter the minimum level: "))
        amount = int(input("Enter the amount of usernames to scrape: "))
        print("[+] Starting scraping process...")
        Scraper.scraping(year, minLevel, amount)
