"""
Generate a small synthetic sample that mirrors the PatentsView granted
"disambiguated" bulk tables, so the pipeline can be built and tested before
the real ~1 GB TSVs are in place.

Real tables mimicked (subset of columns we actually use):
  g_patent.tsv                  patent_id, patent_type, patent_date, patent_title, wipo_kind, num_claims, withdrawn
  g_cpc_current.tsv             patent_id, cpc_sequence, cpc_section, cpc_class, cpc_subclass, cpc_group, cpc_type
  g_assignee_disambiguated.tsv  patent_id, assignee_sequence, assignee_id,
                                disambig_assignee_individual_name_first, disambig_assignee_individual_name_last,
                                disambig_assignee_organization, assignee_type, assignee_country

The sample deliberately includes:
  - messy real-world org-name variants for the same player (ASML, Canon, ...)  -> exercises normalization
  - patents OUTSIDE G03F (noise)                                               -> exercises the CPC filter
  - a few patents outside the 2005-2025 window                                 -> exercises the date filter
"""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)
OUT = Path(__file__).resolve().parents[1] / "data" / "sample"
OUT.mkdir(parents=True, exist_ok=True)

# player -> (messy org-name variants as they appear in real assignee data, country)
PLAYERS = {
    "ASML":        (["ASML Netherlands B.V.", "ASML HOLDING N.V.", "ASML Netherlands, B.V.", "Asml Netherlands BV"], "NL"),
    "Canon":       (["Canon Kabushiki Kaisha", "CANON KABUSHIKI KAISHA", "Canon Inc."], "JP"),
    "Nikon":       (["Nikon Corporation", "NIKON CORPORATION", "Nikon Corp"], "JP"),
    "Carl Zeiss":  (["Carl Zeiss SMT GmbH", "Carl Zeiss SMT AG", "CARL ZEISS SMT GMBH"], "DE"),
    "TSMC":        (["Taiwan Semiconductor Manufacturing Company, Ltd.", "Taiwan Semiconductor Manufacturing Co., Ltd.", "TAIWAN SEMICONDUCTOR MANUFACTURING COMPANY LIMITED"], "TW"),
    "Samsung":     (["Samsung Electronics Co., Ltd.", "SAMSUNG ELECTRONICS CO., LTD.", "Samsung Electronics Company Limited"], "KR"),
    "Intel":       (["Intel Corporation", "INTEL CORPORATION"], "US"),
    "Tokyo Electron": (["Tokyo Electron Limited", "TOKYO ELECTRON LIMITED"], "JP"),
    "Applied Materials": (["Applied Materials, Inc.", "APPLIED MATERIALS, INC."], "US"),
    "Gigaphoton":  (["Gigaphoton Inc.", "GIGAPHOTON INC."], "JP"),
    "Cymer":       (["Cymer, Inc.", "Cymer LLC", "CYMER, INC."], "US"),
    "IBM":         (["International Business Machines Corporation", "INTERNATIONAL BUSINESS MACHINES CORPORATION"], "US"),
}

# G03F sub-technologies (cpc_group -> readable area). Used later for the assignee x sub-tech network.
G03F_GROUPS = {
    "G03F7/70":  "Exposure apparatus",     # the lithography "machines" (ASML/Canon/Nikon core)
    "G03F7/20":  "Exposure; illumination",
    "G03F1/00":  "Masks / reticles",
    "G03F1/24":  "EUV masks",
    "G03F7/00":  "Photoresist / process",
    "G03F7/16":  "Resist coating",
    "G03F9/00":  "Alignment / registration",
}
# rough affinity: which players lean into which areas (weights)
AFFINITY = {
    "ASML":        {"G03F7/70": 6, "G03F7/20": 4, "G03F9/00": 3, "G03F1/24": 2},
    "Canon":       {"G03F7/70": 5, "G03F7/20": 3, "G03F7/16": 2},
    "Nikon":       {"G03F7/70": 5, "G03F7/20": 3, "G03F9/00": 2},
    "Carl Zeiss":  {"G03F7/70": 4, "G03F7/20": 3},
    "TSMC":        {"G03F1/00": 4, "G03F1/24": 4, "G03F7/00": 3, "G03F9/00": 2},
    "Samsung":     {"G03F1/00": 3, "G03F1/24": 3, "G03F7/00": 3},
    "Intel":       {"G03F1/24": 3, "G03F7/00": 2, "G03F9/00": 2},
    "Tokyo Electron": {"G03F7/16": 4, "G03F7/00": 3},
    "Applied Materials": {"G03F7/16": 3, "G03F7/00": 2},
    "Gigaphoton":  {"G03F7/20": 5},
    "Cymer":       {"G03F7/20": 5},
    "IBM":         {"G03F7/00": 3, "G03F1/00": 2},
}

def rand_date(y0, y1):
    start = date(y0, 1, 1); end = date(y1, 12, 31)
    return start + timedelta(days=random.randint(0, (end - start).days))

def weighted_group(player):
    aff = AFFINITY[player]
    groups = list(aff.keys()); weights = list(aff.values())
    return random.choices(groups, weights=weights, k=1)[0]

patents, cpc_rows, assignee_rows = [], [], []
pid = 5_000_000
assignee_ids = {p: f"a-{i:04d}" for i, p in enumerate(PLAYERS)}

# --- in-scope G03F patents, 2005-2025, ramping up over time (EUV era) ---
for year in range(2005, 2026):
    ramp = 1.0 + (year - 2005) * 0.12  # more filings later
    for player in PLAYERS:
        n = max(0, int(random.gauss(6 * ramp * (0.5 + AFFINITY[player].get("G03F7/70", 1) / 6), 3)))
        for _ in range(n):
            pid += 1
            g = weighted_group(player)
            patents.append([pid, "utility", rand_date(year, year).isoformat(),
                            f"{G03F_GROUPS[g]} method and apparatus", "B2",
                            random.randint(8, 30), 0])
            cpc_rows.append([pid, 0, "G", "03", "G03F", g, "inventional"])
            # sometimes a secondary CPC (e.g. H01L) to look realistic
            if random.random() < 0.4:
                cpc_rows.append([pid, 1, "H", "01", "H01L", "H01L21/027", "additional"])
            org = random.choice(PLAYERS[player][0])
            assignee_rows.append([pid, 0, assignee_ids[player], "", "", org, "3", PLAYERS[player][1]])

# --- noise: non-G03F patents (should be filtered OUT) ---
for _ in range(400):
    pid += 1
    patents.append([pid, "utility", rand_date(2005, 2025).isoformat(),
                    "Unrelated semiconductor widget", "B2", random.randint(5, 20), 0])
    cpc_rows.append([pid, 0, "H", "01", "H01L", "H01L29/00", "inventional"])
    assignee_rows.append([pid, 0, "a-9999", "", "", "Some Other Company, Inc.", "3", "US"])

# --- noise: G03F but OUTSIDE the date window (should be filtered OUT) ---
for _ in range(60):
    pid += 1
    patents.append([pid, "utility", rand_date(1998, 2004).isoformat(),
                    "Old lithography apparatus", "B2", 12, 0])
    cpc_rows.append([pid, 0, "G", "03", "G03F", "G03F7/70", "inventional"])
    org = random.choice(PLAYERS["Nikon"][0])
    assignee_rows.append([pid, 0, assignee_ids["Nikon"], "", "", org, "3", "JP"])

def write_tsv(name, header, rows):
    with open(OUT / name, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(header)
        w.writerows(rows)

write_tsv("g_patent.tsv",
          ["patent_id", "patent_type", "patent_date", "patent_title", "wipo_kind", "num_claims", "withdrawn"],
          patents)
write_tsv("g_cpc_current.tsv",
          ["patent_id", "cpc_sequence", "cpc_section", "cpc_class", "cpc_subclass", "cpc_group", "cpc_type"],
          cpc_rows)
write_tsv("g_assignee_disambiguated.tsv",
          ["patent_id", "assignee_sequence", "assignee_id",
           "disambig_assignee_individual_name_first", "disambig_assignee_individual_name_last",
           "disambig_assignee_organization", "assignee_type", "location_id"],
          assignee_rows)

print(f"patents:   {len(patents):>6}  ({sum(1 for p in patents if p[1]=='utility')} utility)")
print(f"cpc rows:  {len(cpc_rows):>6}")
print(f"assignees: {len(assignee_rows):>6}")
print(f"written to {OUT}")
