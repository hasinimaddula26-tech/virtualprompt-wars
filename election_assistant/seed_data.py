"""Structured demonstration data for the Election Process Assistant.

The records are deliberately local and marked as mock data. Production use must
replace these dictionaries with official state and local election authority
feeds before citizens rely on deadlines, candidates, or polling details.
"""

META = {
    "last_updated": "2026-05-01T00:00:00+00:00",
    "data_boundary": (
        "Mock demonstration data for product workflow validation. Replace with "
        "official election authority feeds before production use."
    ),
    "cache_limit_mb": 50,
}

LANGUAGES = [
    {"code": "en", "label": "English", "dir": "ltr"},
    {"code": "es", "label": "Español", "dir": "ltr"},
    {"code": "zh", "label": "中文", "dir": "ltr"},
    {"code": "vi", "label": "Tiếng Việt", "dir": "ltr"},
    {"code": "ko", "label": "한국어", "dir": "ltr"},
    {"code": "tl", "label": "Tagalog", "dir": "ltr"},
    {"code": "ar", "label": "العربية", "dir": "rtl"},
    {"code": "fr", "label": "Français", "dir": "ltr"},
    {"code": "ru", "label": "Русский", "dir": "ltr"},
    {"code": "pt", "label": "Português", "dir": "ltr"},
]

COMMON_PROCESS_STEPS = [
    {
        "id": "confirm-eligibility",
        "title": "Confirm eligibility",
        "estimated_time": "3 minutes",
        "documents": ["Birth year", "Citizenship confirmation", "Residence county"],
        "instructions": "Review age, citizenship, residency, and rights restoration rules.",
        "help": [
            "People who move should update their address.",
            "First-time voters may need extra ID depending on registration method.",
        ],
    },
    {
        "id": "check-registration",
        "title": "Check registration status",
        "estimated_time": "5 minutes",
        "documents": ["Name", "Date of birth", "County or ZIP code"],
        "instructions": "Use the official status portal or election office contact route.",
        "help": [
            "Name mismatches and recent moves are common lookup issues.",
            "Use manual verification when official API data is unavailable.",
        ],
    },
    {
        "id": "choose-method",
        "title": "Choose a voting method",
        "estimated_time": "6 minutes",
        "documents": ["Schedule availability", "Mailing address", "Accessibility needs"],
        "instructions": "Compare mail, early, election day, and absentee options.",
        "help": [
            "Consider transit, work schedule, language assistance, and ballot return rules."
        ],
    },
    {
        "id": "research-ballot",
        "title": "Research the ballot",
        "estimated_time": "20 minutes",
        "documents": ["Residential address", "Sample ballot", "Candidate and measure sources"],
        "instructions": "Review candidate statements, measure summaries, fiscal notes, and sources.",
        "help": ["Save neutral notes locally and export them in the voter guide."],
    },
    {
        "id": "vote-and-confirm",
        "title": "Vote and confirm",
        "estimated_time": "10 minutes",
        "documents": ["Ballot envelope if voting by mail", "Accepted ID if required", "Voter guide"],
        "instructions": "Cast the ballot, track mail ballot status where available, and report issues quickly.",
        "help": ["Use election day support for long waits, equipment issues, or intimidation reports."],
    },
]

JURISDICTIONS = {
    "california": {
        "name": "California",
        "timezone": "America/Los_Angeles",
        "timezone_label": "Pacific Time",
        "official": {
            "elections_url": "https://www.sos.ca.gov/elections",
            "registration_url": "https://registertovote.ca.gov",
            "status_url": "https://voterstatus.sos.ca.gov",
            "mail_tracking_url": "https://california.ballottrax.net/voter",
        },
        "registration": {
            "status": "Action needed",
            "methods": [
                "Online registration",
                "Paper form by mail",
                "In-person county office update",
                "Conditional registration at voting sites",
            ],
            "required_documents": [
                "Legal name",
                "Residential address",
                "Date of birth",
                "California ID or last four digits of SSN if requested by official form",
            ],
            "processing_time": "3 to 15 business days depending on county workload",
            "fallback": "Contact the county elections office if online status lookup is unavailable.",
        },
        "eligibility": {
            "min_age": 18,
            "preregister_age": 16,
            "citizenship_required": True,
            "residency_rule": (
                "Must be a California resident and not currently serving a state or "
                "federal prison term for a felony conviction."
            ),
        },
        "deadlines": [
            {
                "id": "ca-registration-primary",
                "title": "Primary registration update",
                "date": "2026-05-18T23:59:00-07:00",
                "category": "Registration",
                "critical": True,
                "description": "Update registration details before the statewide primary cycle.",
                "source": "California Secretary of State sample feed",
            },
            {
                "id": "ca-primary-election",
                "title": "Statewide primary election day",
                "date": "2026-06-02T20:00:00-07:00",
                "category": "Election Day",
                "critical": True,
                "description": "Polls close at 8:00 PM local time.",
                "source": "California Secretary of State sample feed",
            },
            {
                "id": "ca-general-registration",
                "title": "General election registration deadline",
                "date": "2026-10-19T23:59:00-07:00",
                "category": "Registration",
                "critical": True,
                "description": "Standard registration deadline before conditional registration applies.",
                "source": "California Secretary of State sample feed",
            },
            {
                "id": "ca-mail-request",
                "title": "Mail ballot replacement request target",
                "date": "2026-10-27T17:00:00-07:00",
                "category": "Vote by mail",
                "critical": False,
                "description": "Recommended latest date to request support if a mailed ballot has not arrived.",
                "source": "County elections sample feed",
            },
            {
                "id": "ca-general-election",
                "title": "General election day",
                "date": "2026-11-03T20:00:00-08:00",
                "category": "Election Day",
                "critical": True,
                "description": "Ballots must be postmarked or delivered according to official rules.",
                "source": "California Secretary of State sample feed",
            },
        ],
        "process_steps": COMMON_PROCESS_STEPS,
        "voting_methods": [
            {
                "id": "mail",
                "name": "Vote by mail",
                "available": True,
                "deadline": "Postmark or return by election day rules",
                "requirements": "Use the official ballot envelope and signature process.",
                "procedure": "Complete the ballot, sign the envelope, return by mail, drop box, or county office.",
                "accessibility": "Remote accessible vote-by-mail options may be available through county offices.",
                "tracking": "Mail ballot tracking link available.",
            },
            {
                "id": "early",
                "name": "Early voting",
                "available": True,
                "deadline": "Dates and hours vary by county.",
                "requirements": "Confirm location and hours before visiting.",
                "procedure": "Visit an early vote center, check in, and cast a ballot.",
                "accessibility": "Accessible voting machines and curbside help listed by site.",
            },
            {
                "id": "election-day",
                "name": "Election day in person",
                "available": True,
                "deadline": "Polls close at 8:00 PM local time.",
                "requirements": "Arrive before polls close; stay in line if already waiting.",
                "procedure": "Use assigned polling place or vote center if available.",
                "accessibility": "Language assistance and accessible equipment listed by site.",
            },
            {
                "id": "absentee",
                "name": "Absentee support",
                "available": True,
                "deadline": "Use county guidance for special circumstances.",
                "requirements": "Eligibility depends on location, status, and voting method.",
                "procedure": "Contact the county office for replacement, accessible, military, or overseas ballot support.",
                "accessibility": "Remote accessible materials and hotline support may apply.",
            },
        ],
        "ballot": {
            "district": "Sample District 12",
            "sample_ballot_url": "https://www.sos.ca.gov/elections",
            "candidates": [
                {
                    "id": "avery-park",
                    "race": "City Council District 12",
                    "name": "Avery Park",
                    "party": "Nonpartisan",
                    "website": "https://example.org/avery-park",
                    "statement": "Focuses on transit reliability, housing permits, and transparent budgeting.",
                    "issues": {
                        "Transit": "Increase bus frequency on high-use routes.",
                        "Housing": "Prioritize faster permit review.",
                        "Budget": "Publish quarterly spending dashboards.",
                    },
                    "source": "Sample candidate filing",
                },
                {
                    "id": "jordan-rivera",
                    "race": "City Council District 12",
                    "name": "Jordan Rivera",
                    "party": "Nonpartisan",
                    "website": "https://example.org/jordan-rivera",
                    "statement": "Focuses on neighborhood services, small business support, and park maintenance.",
                    "issues": {
                        "Transit": "Expand late-night service pilots.",
                        "Housing": "Use city land for affordable housing.",
                        "Budget": "Fund participatory budgeting pilots.",
                    },
                    "source": "Sample candidate filing",
                },
            ],
            "measures": [
                {
                    "id": "measure-a",
                    "title": "Measure A: Library and digital access bond",
                    "summary": "Authorizes local bonds for library repair, broadband rooms, and accessibility upgrades.",
                    "fiscal_impact": "Estimated annual repayment listed in the county sample pamphlet.",
                    "arguments_for": "Supporters say the measure modernizes public learning spaces.",
                    "arguments_against": "Opponents say the debt should wait for a broader capital plan.",
                    "source": "Sample county voter pamphlet",
                }
            ],
        },
        "polling": {
            "assigned": {
                "name": "Harbor Community Center",
                "address": "100 Civic Harbor Way, Sample City, CA",
                "hours": "7:00 AM to 8:00 PM",
                "wait_minutes": 18,
                "parking": "Street parking and accessible spaces on the east entrance.",
                "transit": "Bus routes 8 and 14 stop within two blocks.",
                "directions_url": "https://maps.google.com",
                "accessibility": [
                    "Wheelchair-accessible entrance",
                    "Accessible ballot marking device",
                    "Curbside voting",
                    "Seating area",
                ],
                "languages": ["English", "Spanish", "Chinese", "Tagalog"],
            },
            "alternatives": [
                {"name": "Northside Vote Center", "distance_miles": 3.2, "hours": "8:00 AM to 5:00 PM", "wait_minutes": 10},
                {"name": "County Elections Office", "distance_miles": 6.9, "hours": "8:00 AM to 8:00 PM", "wait_minutes": 22},
            ],
        },
        "contacts": {
            "official": "County Elections Office: 555-0100",
            "hotline": "Voter assistance hotline: 866-OUR-VOTE",
            "rights_restoration": (
                "Review California rights restoration guidance through the Secretary of "
                "State and county officials."
            ),
        },
    },
    "texas": {
        "name": "Texas",
        "timezone": "America/Chicago",
        "timezone_label": "Central Time",
        "official": {
            "elections_url": "https://www.votetexas.gov",
            "registration_url": "https://www.votetexas.gov/register-to-vote",
            "status_url": "https://teamrv-mvp.sos.texas.gov/MVP/mvp.do",
            "mail_tracking_url": "https://teamrv-mvp.sos.texas.gov/MVP/mvp.do",
        },
        "registration": {
            "status": "Verify with county",
            "methods": ["Paper registration application", "County voter registrar office", "Limited online update for existing state records"],
            "required_documents": ["Name", "Residential address", "Date of birth", "County", "Official form signature"],
            "processing_time": "Up to 30 days before an election deadline",
            "fallback": "Call the county voter registrar when online lookup does not match.",
        },
        "eligibility": {
            "min_age": 18,
            "preregister_age": 17,
            "citizenship_required": True,
            "residency_rule": "Must be a resident of the county and meet state eligibility rules.",
        },
        "deadlines": [
            {"id": "tx-registration", "title": "Registration deadline", "date": "2026-10-05T17:00:00-05:00", "category": "Registration", "critical": True, "description": "Registration applications should be submitted by the official deadline.", "source": "VoteTexas sample feed"},
            {"id": "tx-early-start", "title": "Early voting begins", "date": "2026-10-19T08:00:00-05:00", "category": "Early voting", "critical": False, "description": "Early voting schedule varies by county.", "source": "County sample feed"},
            {"id": "tx-mail-request", "title": "Mail ballot application received by", "date": "2026-10-23T17:00:00-05:00", "category": "Absentee", "critical": True, "description": "Mail ballot application must be received by the early voting clerk.", "source": "VoteTexas sample feed"},
            {"id": "tx-election-day", "title": "General election day", "date": "2026-11-03T19:00:00-06:00", "category": "Election Day", "critical": True, "description": "Polls close at 7:00 PM local time.", "source": "VoteTexas sample feed"},
        ],
        "process_steps": COMMON_PROCESS_STEPS,
        "voting_methods": [
            {"id": "early", "name": "Early voting", "available": True, "deadline": "County schedule before election day", "requirements": "Accepted ID or official alternative process.", "procedure": "Visit any eligible early voting location in the county.", "accessibility": "Accessible voting equipment is required at polling places."},
            {"id": "election-day", "name": "Election day in person", "available": True, "deadline": "Polls close at 7:00 PM local time.", "requirements": "Vote at assigned precinct unless countywide vote centers apply.", "procedure": "Check in, present ID or alternative documentation, and cast a ballot.", "accessibility": "Accessible machines, curbside voting rules, and assistance options are listed by county."},
            {"id": "absentee", "name": "Ballot by mail", "available": True, "deadline": "Application received by official deadline.", "requirements": "Must meet state eligibility criteria.", "procedure": "Apply with the early voting clerk, receive ballot, and return by official deadline.", "accessibility": "Contact county officials for disability-related ballot assistance."},
        ],
        "ballot": {
            "district": "Sample County Precinct 44",
            "sample_ballot_url": "https://www.votetexas.gov",
            "candidates": [
                {"id": "casey-nguyen", "race": "County Commissioner", "name": "Casey Nguyen", "party": "Sample Party A", "website": "https://example.org/casey-nguyen", "statement": "Prioritizes road maintenance, emergency services, and county transparency.", "issues": {"Roads": "Publish repair priority maps.", "Emergency": "Fund volunteer response training.", "Budget": "Quarterly open budget forums."}, "source": "Sample county filing"},
                {"id": "morgan-shaw", "race": "County Commissioner", "name": "Morgan Shaw", "party": "Sample Party B", "website": "https://example.org/morgan-shaw", "statement": "Prioritizes rural broadband, property tax oversight, and senior services.", "issues": {"Roads": "Use performance contracts.", "Emergency": "Upgrade dispatch software.", "Budget": "Create tax impact calculator."}, "source": "Sample county filing"},
            ],
            "measures": [
                {"id": "proposition-1", "title": "Proposition 1: Emergency communications upgrade", "summary": "Funds a countywide emergency communications replacement.", "fiscal_impact": "Estimated levy published in the sample order.", "arguments_for": "Supporters cite faster response coordination.", "arguments_against": "Opponents cite cost and procurement risk.", "source": "Sample county measure filing"}
            ],
        },
        "polling": {
            "assigned": {
                "name": "Lone Star Civic Hall",
                "address": "220 County Square, Sample Town, TX",
                "hours": "7:00 AM to 7:00 PM",
                "wait_minutes": 26,
                "parking": "Lot parking with two accessible spaces near the front door.",
                "transit": "Demand response transit available by advance request.",
                "directions_url": "https://maps.google.com",
                "accessibility": ["Accessible entrance", "Accessible voting system", "Curbside voting by request"],
                "languages": ["English", "Spanish", "Vietnamese"],
            },
            "alternatives": [
                {"name": "West Library Vote Center", "distance_miles": 4.4, "hours": "8:00 AM to 5:00 PM", "wait_minutes": 14},
                {"name": "County Annex", "distance_miles": 9.1, "hours": "7:00 AM to 7:00 PM", "wait_minutes": 35},
            ],
        },
        "contacts": {
            "official": "County Voter Registrar: 555-0144",
            "hotline": "Voter assistance hotline: 866-OUR-VOTE",
            "rights_restoration": "Review Texas voting rights restoration rules with the county registrar or official state guidance.",
        },
    },
    "new-york": {
        "name": "New York",
        "timezone": "America/New_York",
        "timezone_label": "Eastern Time",
        "official": {
            "elections_url": "https://elections.ny.gov",
            "registration_url": "https://elections.ny.gov/voter-registration-process",
            "status_url": "https://voterlookup.elections.ny.gov",
            "mail_tracking_url": "https://voterlookup.elections.ny.gov",
        },
        "registration": {
            "status": "Needs confirmation",
            "methods": ["Online DMV-linked registration", "Paper form by mail", "County board of elections office"],
            "required_documents": ["Name", "Date of birth", "Address", "DMV record or signed official form"],
            "processing_time": "County processing time varies around deadlines",
            "fallback": "Contact the county board of elections for manual verification.",
        },
        "eligibility": {
            "min_age": 18,
            "preregister_age": 16,
            "citizenship_required": True,
            "residency_rule": "Must be a resident for the required period and meet state eligibility rules.",
        },
        "deadlines": [
            {"id": "ny-registration", "title": "Registration deadline", "date": "2026-10-24T23:59:00-04:00", "category": "Registration", "critical": True, "description": "Registration must meet official deadline rules.", "source": "New York Board of Elections sample feed"},
            {"id": "ny-early-start", "title": "Early voting begins", "date": "2026-10-24T09:00:00-04:00", "category": "Early voting", "critical": False, "description": "Early voting dates and hours vary by county.", "source": "County sample feed"},
            {"id": "ny-absentee-request", "title": "Absentee ballot request target", "date": "2026-10-26T17:00:00-04:00", "category": "Absentee", "critical": True, "description": "Use official request rules for online, mail, or in-person methods.", "source": "New York Board of Elections sample feed"},
            {"id": "ny-election-day", "title": "General election day", "date": "2026-11-03T21:00:00-05:00", "category": "Election Day", "critical": True, "description": "Polls close at 9:00 PM local time.", "source": "New York Board of Elections sample feed"},
        ],
        "process_steps": COMMON_PROCESS_STEPS,
        "voting_methods": [
            {"id": "early", "name": "Early voting", "available": True, "deadline": "County schedule before election day", "requirements": "Check assigned county early voting sites.", "procedure": "Visit an early voting site during posted hours.", "accessibility": "Accessible systems and language support vary by site."},
            {"id": "election-day", "name": "Election day in person", "available": True, "deadline": "Polls close at 9:00 PM local time.", "requirements": "Use assigned polling location.", "procedure": "Check in and cast a ballot at the assigned site.", "accessibility": "Accessible voting machines and assistance available."},
            {"id": "absentee", "name": "Absentee voting", "available": True, "deadline": "Request and return deadlines follow official state rules.", "requirements": "Meet absentee eligibility or early mail voting rules if available.", "procedure": "Request ballot, complete it, and return by official deadline.", "accessibility": "Accessible absentee ballot services may be available."},
        ],
        "ballot": {
            "district": "Sample Assembly District 8",
            "sample_ballot_url": "https://elections.ny.gov",
            "candidates": [
                {"id": "riley-chen", "race": "Assembly District 8", "name": "Riley Chen", "party": "Sample Party A", "website": "https://example.org/riley-chen", "statement": "Focuses on school facilities, commuter service, and constituent casework.", "issues": {"Schools": "Renovate high-need buildings.", "Transit": "Add commuter reliability targets.", "Services": "Open mobile district hours."}, "source": "Sample candidate filing"},
                {"id": "samir-patel", "race": "Assembly District 8", "name": "Samir Patel", "party": "Sample Party B", "website": "https://example.org/samir-patel", "statement": "Focuses on housing stability, environmental cleanup, and tax transparency.", "issues": {"Schools": "Expand after-school programs.", "Transit": "Fund station accessibility.", "Services": "Publish benefit navigation guides."}, "source": "Sample candidate filing"},
            ],
            "measures": [
                {"id": "proposal-b", "title": "Proposal B: Park resilience fund", "summary": "Creates a dedicated fund for flood-resilient park repairs.", "fiscal_impact": "Costs and funding plan listed in the sample abstract.", "arguments_for": "Supporters cite climate resilience and safer recreation.", "arguments_against": "Opponents cite dedicated fund restrictions.", "source": "Sample ballot proposal abstract"}
            ],
        },
        "polling": {
            "assigned": {
                "name": "Riverside School Gym",
                "address": "88 Riverside Avenue, Sample Borough, NY",
                "hours": "6:00 AM to 9:00 PM",
                "wait_minutes": 12,
                "parking": "Limited parking; accessible drop-off at main entrance.",
                "transit": "Subway station and bus stop within three blocks.",
                "directions_url": "https://maps.google.com",
                "accessibility": ["Ramp entrance", "Accessible ballot marking device", "Audio ballot support"],
                "languages": ["English", "Spanish", "Chinese", "Russian"],
            },
            "alternatives": [
                {"name": "Downtown Early Vote Center", "distance_miles": 2.7, "hours": "9:00 AM to 5:00 PM", "wait_minutes": 8},
                {"name": "County Board Office", "distance_miles": 7.8, "hours": "9:00 AM to 7:00 PM", "wait_minutes": 19},
            ],
        },
        "contacts": {
            "official": "County Board of Elections: 555-0188",
            "hotline": "Voter assistance hotline: 866-OUR-VOTE",
            "rights_restoration": "Review New York rights restoration guidance with the county board or official state resources.",
        },
    },
}

EDUCATION_MODULES = [
    {
        "id": "counting-votes",
        "title": "How votes are counted",
        "audience": "First-time voters",
        "summary": "Explains check-in, ballot scanning, reconciliation, canvassing, certification, and recount triggers.",
        "transcript": "Captioned transcript covers every stage from ballot casting to certification.",
        "duration": "8 minutes",
    },
    {
        "id": "ballot-measures",
        "title": "Understanding ballot measures",
        "audience": "General public",
        "summary": "Explains measure text, fiscal analysis, arguments, and local rule effects.",
        "transcript": "Transcript includes examples of bonds, charters, and advisory questions.",
        "duration": "10 minutes",
    },
    {
        "id": "voting-rights-history",
        "title": "Voting rights and reforms",
        "audience": "Students and civic groups",
        "summary": "Provides historical context about voting rights expansions, access barriers, and modern reforms.",
        "transcript": "Transcript includes timelines, court milestones, and local participation prompts.",
        "duration": "12 minutes",
    },
]

INNOVATIONS = [
    {
        "id": "ranked-choice",
        "title": "Ranked choice voting",
        "benefits": "Lets voters rank candidates and can reduce vote splitting.",
        "challenges": "Requires clear voter education and accessible ballot design.",
        "example": "Used in selected local and state contests.",
        "advocacy": "Ask officials for public pilots, tabulation transparency, and accessible ballot testing.",
    },
    {
        "id": "approval",
        "title": "Approval voting",
        "benefits": "Allows voters to support every acceptable candidate.",
        "challenges": "Different strategy and reporting expectations require education.",
        "example": "Used in some municipal contexts.",
        "advocacy": "Request neutral simulations and community briefings.",
    },
    {
        "id": "star",
        "title": "STAR voting",
        "benefits": "Combines score voting with an automatic runoff between top candidates.",
        "challenges": "Needs tabulation software, voter education, and legal authorization.",
        "example": "Discussed by election reform organizations and local campaigns.",
        "advocacy": "Use template letters and legislative contact lists to start policy review.",
    },
]

PROCESS_IMPROVEMENTS = [
    "Automatic voter registration",
    "Election day registration",
    "Extended early voting periods",
    "Accessible ballot tracking",
    "Plain-language ballot summaries",
]

ORGANIZER_TOOLKIT = {
    "best_practices": [
        "Train volunteers on neutral assistance",
        "Use official forms only",
        "Protect personal data",
        "Track submissions without storing sensitive identifiers",
    ],
    "legal_requirements": [
        "Follow jurisdiction rules for form handling",
        "Do not pressure party or candidate choices",
        "Submit forms by official deadlines",
    ],
    "materials": [
        "Printable registration checklist",
        "Multilingual flyer",
        "QR-style portal card",
        "Volunteer shift sheet",
    ],
}

INCIDENT_TYPES = [
    {
        "id": "long-wait",
        "label": "Long wait time",
        "guidance": "Check alternative locations, stay in line if polls are closing, and report the site and time.",
        "critical": False,
    },
    {
        "id": "equipment",
        "label": "Equipment issue",
        "guidance": "Ask for a replacement ballot or accessible device support and document the issue.",
        "critical": True,
    },
    {
        "id": "intimidation",
        "label": "Voter intimidation",
        "guidance": "Move to a safe location, call the voter hotline, and notify election officials immediately.",
        "critical": True,
    },
    {
        "id": "registration-problem",
        "label": "Registration problem",
        "guidance": "Ask about provisional ballot options and verify status with local officials.",
        "critical": False,
    },
]

INTEGRATION_SCHEMAS = {
    "registration_status": ["jurisdiction", "name", "birth_year", "address"],
    "polling_location": ["jurisdiction", "address"],
    "ballot_information": ["jurisdiction", "district"],
}

TRANSLATIONS = {
    "en": {
        "kicker": "Personalized civic readiness",
        "workspace": "Your election workspace",
        "saved": "Saved.",
        "mock": "Using mock demonstration data until official feeds are connected.",
    },
    "es": {
        "kicker": "Preparación cívica personalizada",
        "workspace": "Tu espacio electoral",
        "saved": "Guardado.",
        "mock": "Usando datos de demostración hasta conectar fuentes oficiales.",
    },
    "zh": {"kicker": "个性化公民准备", "workspace": "您的选举工作区", "saved": "已保存。", "mock": "在连接官方数据前使用演示数据。"},
    "vi": {"kicker": "Sẵn sàng bầu cử cá nhân", "workspace": "Không gian bầu cử của bạn", "saved": "Đã lưu.", "mock": "Đang dùng dữ liệu minh họa đến khi kết nối nguồn chính thức."},
    "ko": {"kicker": "맞춤형 시민 준비", "workspace": "나의 선거 작업공간", "saved": "저장됨.", "mock": "공식 피드 연결 전까지 데모 데이터를 사용합니다."},
    "tl": {"kicker": "Personal na paghahanda sa halalan", "workspace": "Iyong workspace sa halalan", "saved": "Nai-save.", "mock": "Gumagamit ng demo data hanggang makonekta ang opisyal na feeds."},
    "ar": {"kicker": "استعداد مدني مخصص", "workspace": "مساحة عمل الانتخابات", "saved": "تم الحفظ.", "mock": "يتم استخدام بيانات تجريبية إلى حين ربط المصادر الرسمية."},
    "fr": {"kicker": "Préparation civique personnalisée", "workspace": "Votre espace électoral", "saved": "Enregistré.", "mock": "Données de démonstration jusqu'à la connexion des sources officielles."},
    "ru": {"kicker": "Персональная гражданская готовность", "workspace": "Ваше пространство выборов", "saved": "Сохранено.", "mock": "Используются демонстрационные данные до подключения официальных источников."},
    "pt": {"kicker": "Preparação cívica personalizada", "workspace": "Seu espaço eleitoral", "saved": "Salvo.", "mock": "Usando dados demonstrativos até conectar fontes oficiais."},
}
