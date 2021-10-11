from flaskinventory.add.external import find_feeds, find_sitemaps

sites = ["https://www.tagesschau.de/", "https://www.krone.at/", "https://www.nzz.ch/"]

for site in sites:
    print(f"Finding feeds for {site}")
    print(find_feeds(site))
    print(f"Finding sitemaps for {site}")
    print(find_sitemaps(site))
    print("-"*64)