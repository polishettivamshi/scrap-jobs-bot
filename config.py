import os
import sys
from dotenv import load_dotenv

load_dotenv()

# ── Chat IDs ──────────────────────────────────────────────────────────────────

BACKEND_CHAT_ID  = os.getenv("SST_BACKEND_JOBS_CHAT_ID")
FRONTEND_CHAT_ID = os.getenv("SST_FRONTEND_JOBS_CHAT_ID")
DEVOPS_CHAT_ID   = os.getenv("SST_DEVOPS_JOBS_CHAT_ID")

# Uncomment as you add more Telegram channels:
# DATA_AI_CHAT_ID  = os.getenv("SST_DATA_AI_JOBS_CHAT_ID")
# MOBILE_CHAT_ID   = os.getenv("SST_MOBILE_JOBS_CHAT_ID")
# QA_CHAT_ID       = os.getenv("SST_QA_JOBS_CHAT_ID")
# SECURITY_CHAT_ID = os.getenv("SST_SECURITY_JOBS_CHAT_ID")
# DESIGN_CHAT_ID   = os.getenv("SST_DESIGN_JOBS_CHAT_ID")
# MGMT_CHAT_ID     = os.getenv("SST_MGMT_JOBS_CHAT_ID")


# ── Location filter ───────────────────────────────────────────────────────────
# All job searches are scoped to this city. Change here to update everywhere.
LOCATION = "Hyderabad"


# ── Job Categories ────────────────────────────────────────────────────────────
#
# KEYWORD STRATEGY:
#   Keep 4–6 keywords per category — precise enough to avoid noise, broad enough
#   to catch variants. Each keyword = 1 request per source (6 sources), so every
#   extra keyword adds ~6 HTTP calls per run.
#
#   ✅ Good: "python developer", "backend engineer"
#   ❌ Avoid: "software engineer" (too broad — floods all categories with the same jobs)

JOB_CATEGORIES = {
    "backend": {
        "chat_id": BACKEND_CHAT_ID,
        "keywords": [
            "python developer",
            "java developer",
            "node.js developer",
            "backend developer",
            "golang developer",
            "rust developer",
        ],
    },
    "frontend": {
        "chat_id": FRONTEND_CHAT_ID,
        "keywords": [
            "react developer",
            "frontend developer",
            "angular developer",
            "vue.js developer",
            "typescript developer",
        ],
    },
    "devops": {
        "chat_id": DEVOPS_CHAT_ID,
        "keywords": [
            "devops engineer",
            "cloud engineer",
            "site reliability engineer",
            "platform engineer",
            "kubernetes engineer",
        ],
    },

    # ── Uncomment to activate additional channels ──────────────────────────

    # "data_ai": {
    #     "chat_id": DATA_AI_CHAT_ID,
    #     "keywords": [
    #         "data engineer",
    #         "machine learning engineer",
    #         "mlops engineer",
    #         "data scientist",
    #         "ai engineer",
    #     ],
    # },
    # "mobile": {
    #     "chat_id": MOBILE_CHAT_ID,
    #     "keywords": [
    #         "ios developer",
    #         "android developer",
    #         "flutter developer",
    #         "react native developer",
    #     ],
    # },
    # "qa_testing": {
    #     "chat_id": QA_CHAT_ID,
    #     "keywords": [
    #         "qa engineer",
    #         "sdet",                   # was "sdete" — typo fixed
    #         "automation test engineer",
    #         "qa automation engineer",
    #     ],
    # },
    # "security": {
    #     "chat_id": SECURITY_CHAT_ID,
    #     "keywords": [
    #         "security engineer",
    #         "devsecops engineer",
    #         "penetration tester",
    #         "cybersecurity analyst",
    #     ],
    # },
    # "design": {
    #     "chat_id": DESIGN_CHAT_ID,
    #     "keywords": [
    #         "ux designer",
    #         "product designer",
    #         "ui ux designer",
    #     ],
    # },
    # "management": {
    #     "chat_id": MGMT_CHAT_ID,
    #     "keywords": [
    #         "engineering manager",
    #         "product manager",
    #         "technical lead",
    #         "scrum master",
    #     ],
    # },
}


# ── Startup Validation ────────────────────────────────────────────────────────
#
# Runs once on import. Fails fast with a clear error instead of silently
# dropping Telegram messages mid-run due to a None chat_id.

def _validate():
    missing_env = []
    missing_chat = []

    if not os.getenv("SST_BOT_TOKEN"):
        missing_env.append("SST_BOT_TOKEN")

    for category, cfg in JOB_CATEGORIES.items():
        if not cfg.get("chat_id"):
            missing_chat.append(f"  • {category.upper()} → chat_id is None (check your .env)")

    if missing_env:
        print(f"❌ Missing required env vars: {', '.join(missing_env)}")
        sys.exit(1)

    if missing_chat:
        print("❌ Missing Telegram chat IDs for active categories:")
        print("\n".join(missing_chat))
        print("\nEither add the missing vars to .env or comment out those categories.")
        sys.exit(1)

    print(f"✅ Config OK — {len(JOB_CATEGORIES)} active categories, "
          f"{sum(len(c['keywords']) for c in JOB_CATEGORIES.values())} keywords total")

_validate()