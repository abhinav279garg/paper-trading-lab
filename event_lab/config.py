"""Fixed parameters of the event experiment (docs/event-intelligence-spec.md). Paper research only."""

HISTORY_START = "2017-01-01"      # filings searched from here; links need a year of lead-in
DEV_START, HOLDOUT_START = "2018-01-01", "2023-01-01"
TRIGGER = 0.03                     # customer's sector-adjusted move at T1
HOLD_DAYS = 5
MAX_NAMES = 5
CUTOFF_MINUTES = 15 * 60 + 45      # filings accepted after 15:45 New York time count for the next trading day
MIN_EDGE = 0.0025                  # 0.25% per event after costs
BOOTSTRAP, SEED = 10000, 20261113

# costs per side by liquidity bucket (median daily traded value over the previous 60 trading days, USD)
BUCKETS = [(50e6, "large"), (5e6, "mid"), (0.0, "small")]
COST_SIDE = {"large": 0.0010, "mid": 0.0025, "small": 0.0050}
BORROW_YEAR = {"large": 0.01, "mid": 0.03, "small": 0.10}   # stock-loan fee charged on short positions
MIN_DOLLAR_VOLUME = 1e5            # below this a name is treated as untradable
SHORT_MIN_PRICE, SHORT_MIN_DOLLAR_VOLUME = 5.0, 1e6          # below either, a short is not allowed

GATE0 = {"pairs": 150, "customers": 40, "top5_share": 0.40, "sectors": 4, "events": 100, "priced": 0.80}

# Customer vocabulary: (ticker, names as they are written in suppliers' annual reports).
CUSTOMERS = [
    ("WMT", ["Walmart", "Wal-Mart"]), ("AMZN", ["Amazon"]), ("AAPL", ["Apple"]), ("TGT", ["Target"]),
    ("COST", ["Costco"]), ("HD", ["Home Depot"]), ("LOW", ["Lowe's"]), ("KR", ["Kroger"]),
    ("CVS", ["CVS"]), ("WBA", ["Walgreens"]), ("MCK", ["McKesson"]), ("CAH", ["Cardinal Health"]),
    ("COR", ["AmerisourceBergen", "Cencora"]), ("BBY", ["Best Buy"]), ("DG", ["Dollar General"]),
    ("DLTR", ["Dollar Tree"]), ("SYY", ["Sysco"]), ("USFD", ["US Foods"]), ("PFGC", ["Performance Food Group"]),
    ("BA", ["Boeing"]), ("LMT", ["Lockheed Martin"]), ("RTX", ["Raytheon"]), ("NOC", ["Northrop Grumman"]),
    ("GD", ["General Dynamics"]), ("GE", ["General Electric"]), ("HON", ["Honeywell"]),
    ("CAT", ["Caterpillar"]), ("DE", ["John Deere", "Deere & Company"]), ("PCAR", ["PACCAR"]), ("CMI", ["Cummins"]),
    ("GM", ["General Motors"]), ("F", ["Ford Motor", "Ford"]), ("TSLA", ["Tesla"]), ("TM", ["Toyota"]),
    ("HMC", ["Honda"]), ("STLA", ["Stellantis", "Fiat Chrysler"]),
    ("MSFT", ["Microsoft"]), ("GOOGL", ["Google", "Alphabet"]), ("META", ["Facebook", "Meta Platforms"]),
    ("NFLX", ["Netflix"]), ("ORCL", ["Oracle"]), ("IBM", ["IBM"]), ("CSCO", ["Cisco"]), ("DELL", ["Dell"]),
    ("HPQ", ["HP Inc"]), ("HPE", ["Hewlett Packard Enterprise"]), ("INTC", ["Intel"]), ("NVDA", ["Nvidia", "NVIDIA"]),
    ("QCOM", ["Qualcomm"]), ("AVGO", ["Broadcom"]), ("AMD", ["Advanced Micro Devices"]), ("MU", ["Micron"]),
    ("AMAT", ["Applied Materials"]), ("LRCX", ["Lam Research"]), ("TXN", ["Texas Instruments"]),
    ("TSM", ["TSMC", "Taiwan Semiconductor"]), ("ASML", ["ASML"]), ("KLAC", ["KLA"]),
    ("JBL", ["Jabil"]), ("ARW", ["Arrow Electronics"]), ("AVT", ["Avnet"]), ("SNX", ["Synnex", "TD SYNNEX"]),
    ("NOK", ["Nokia"]), ("ERIC", ["Ericsson"]), ("SONY", ["Sony"]),
    ("VZ", ["Verizon"]), ("T", ["AT&T"]), ("TMUS", ["T-Mobile"]), ("CMCSA", ["Comcast"]), ("DIS", ["Disney"]),
    ("JNJ", ["Johnson & Johnson"]), ("PFE", ["Pfizer"]), ("MRK", ["Merck"]), ("ABBV", ["AbbVie"]),
    ("ABT", ["Abbott"]), ("AMGN", ["Amgen"]), ("GILD", ["Gilead"]), ("LLY", ["Eli Lilly"]),
    ("BMY", ["Bristol-Myers Squibb", "Bristol Myers Squibb"]), ("NVS", ["Novartis"]), ("SNY", ["Sanofi"]),
    ("AZN", ["AstraZeneca"]), ("GSK", ["GlaxoSmithKline", "GSK"]), ("NVO", ["Novo Nordisk"]), ("TAK", ["Takeda"]),
    ("MDT", ["Medtronic"]), ("BSX", ["Boston Scientific"]), ("SYK", ["Stryker"]), ("BDX", ["Becton Dickinson"]),
    ("TMO", ["Thermo Fisher"]), ("DHR", ["Danaher"]), ("UNH", ["UnitedHealth", "UnitedHealthcare"]),
    ("HUM", ["Humana"]), ("CI", ["Cigna", "Express Scripts"]), ("ELV", ["Anthem", "Elevance"]),
    ("HCA", ["HCA Healthcare"]), ("DVA", ["DaVita"]), ("DGX", ["Quest Diagnostics"]), ("LH", ["Labcorp", "LabCorp"]),
    ("XOM", ["ExxonMobil", "Exxon Mobil"]), ("CVX", ["Chevron"]), ("COP", ["ConocoPhillips"]),
    ("MPC", ["Marathon Petroleum"]), ("VLO", ["Valero"]), ("PSX", ["Phillips 66"]), ("SHEL", ["Shell"]),
    ("BP", ["BP"]), ("HAL", ["Halliburton"]), ("SLB", ["Schlumberger"]),
    ("PEP", ["PepsiCo"]), ("KO", ["Coca-Cola"]), ("PG", ["Procter & Gamble"]), ("NKE", ["Nike"]),
    ("SBUX", ["Starbucks"]), ("MCD", ["McDonald's"]), ("FDX", ["FedEx"]), ("UPS", ["UPS", "United Parcel Service"]),
    ("UNP", ["Union Pacific"]), ("DAL", ["Delta Air Lines"]), ("UAL", ["United Airlines"]),
    ("AAL", ["American Airlines"]), ("LUV", ["Southwest Airlines"]),
    ("AZO", ["AutoZone"]), ("ORLY", ["O'Reilly"]), ("AAP", ["Advance Auto Parts"]), ("TSCO", ["Tractor Supply"]),
    ("DKS", ["Dick's Sporting Goods"]), ("M", ["Macy's"]), ("KSS", ["Kohl's"]), ("TJX", ["TJX"]),
    ("ROST", ["Ross Stores"]), ("ULTA", ["Ulta"]), ("GME", ["GameStop"]), ("EBAY", ["eBay"]), ("W", ["Wayfair"]),
    ("CHWY", ["Chewy"]), ("ACI", ["Albertsons"]), ("BJ", ["BJ's Wholesale"]), ("GWW", ["Grainger"]),
    ("FAST", ["Fastenal"]), ("WCC", ["WESCO"]), ("WHR", ["Whirlpool"]),
]
PHRASES = ["{a} accounted for", "{a} inc accounted for", "{a} represented", "{a} comprised",
           "sales to {a}", "revenue from {a}", "revenues from {a}", "largest customer {a}"]


def sector_etf(sic) -> str:
    """Fixed industry-code to sector-ETF table."""
    try:
        s = int(sic)
    except (TypeError, ValueError):
        return "SPY"
    table = [
        (100, 999, "XLP"), (1000, 1299, "XLB"), (1300, 1399, "XLE"), (1400, 1499, "XLB"), (1500, 1799, "XLI"),
        (2000, 2199, "XLP"), (2200, 2399, "XLY"), (2400, 2499, "XLB"), (2500, 2599, "XLY"), (2600, 2699, "XLB"),
        (2700, 2799, "XLY"), (2800, 2829, "XLB"), (2830, 2836, "XLV"), (2840, 2844, "XLP"), (2850, 2899, "XLB"),
        (2900, 2999, "XLE"), (3000, 3099, "XLB"), (3100, 3199, "XLY"), (3200, 3399, "XLB"), (3400, 3569, "XLI"),
        (3570, 3579, "XLK"), (3580, 3599, "XLI"), (3600, 3629, "XLK"), (3630, 3639, "XLY"), (3640, 3699, "XLK"),
        (3700, 3716, "XLY"), (3720, 3799, "XLI"), (3800, 3839, "XLK"), (3840, 3851, "XLV"), (3860, 3899, "XLK"),
        (3900, 3999, "XLY"), (4000, 4799, "XLI"), (4800, 4899, "XLC"), (4900, 4999, "XLU"),
        (5000, 5119, "XLI"), (5120, 5122, "XLV"), (5130, 5139, "XLY"), (5140, 5149, "XLP"), (5150, 5199, "XLI"),
        (5200, 5399, "XLY"), (5400, 5499, "XLP"), (5500, 5911, "XLY"), (5912, 5912, "XLP"), (5913, 5999, "XLY"),
        (6000, 6499, "XLF"), (6500, 6599, "XLRE"), (6600, 6797, "XLF"), (6798, 6798, "XLRE"), (6799, 6799, "XLF"),
        (7000, 7299, "XLY"), (7300, 7369, "XLI"), (7370, 7379, "XLK"), (7380, 7399, "XLI"), (7800, 7999, "XLC"),
        (8000, 8099, "XLV"), (8700, 8730, "XLI"), (8731, 8734, "XLV"), (8735, 8799, "XLI"),
    ]
    for lo, hi, etf in table:
        if lo <= s <= hi:
            return etf
    return "SPY"


ETFS = ["SPY", "XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY"]
