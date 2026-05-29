import os
from dotenv import load_dotenv

load_dotenv()

BACKEND_CHAT_ID = os.getenv("SST_BACKEND_JOBS_CHAT_ID")
FRONTEND_CHAT_ID = os.getenv("SST_FRONTEND_JOBS_CHAT_ID")
DEVOPS_CHAT_ID = os.getenv("SST_DEVOPS_JOBS_CHAT_ID")

JOB_CATEGORIES = {
    "backend": {
        "chat_id": BACKEND_CHAT_ID,
        "keywords": ["python developer", "java developer", "node js developer", "backend developer", "golang developer", "software engineer", "php developer", "ruby on rails developer", "c# developer", "rust developer"]
    },
    "frontend": {
        "chat_id": FRONTEND_CHAT_ID,
        "keywords": ["react developer", "frontend developer", "angular developer", "vue js developer", "ui developer", "javascript developer", "typescript developer", "web developer"]
    },
    "devops": {
        "chat_id": DEVOPS_CHAT_ID,
        "keywords": ["devops engineer", "aws engineer", "cloud engineer", "kubernetes engineer", "site reliability engineer", "docker engineer", "platform engineer", "infra engineer"]
    },
    # "data_ai": {
    #     "chat_id": DATA_AI_CHAT_ID,
    #     "keywords": ["data scientist", "data engineer", "machine learning engineer", "ai engineer", "data analyst", "nlp engineer", "computer vision engineer", "business intelligence developer"]
    # },
    # "mobile": {
    #     "chat_id": MOBILE_CHAT_ID,
    #     "keywords": ["ios developer", "android developer", "flutter developer", "react native developer", "mobile developer", "swift developer", "kotlin developer"]
    # },
    # "qa_testing": {
    #     "chat_id": QA_CHAT_ID,
    #     "keywords": ["qa engineer", "quality assurance", "automation engineer", "test engineer", "sdete", "manual tester", "performance engineer"]
    # },
    # "security": {
    #     "chat_id": SECURITY_CHAT_ID,
    #     "keywords": ["security engineer", "cybersecurity analyst", "pentester", "penetration tester", "security consultant", "information security", "devsecops"]
    # },
    # "design": {
    #     "chat_id": DESIGN_CHAT_ID,
    #     "keywords": ["ux designer", "ui designer", "product designer", "graphic designer", "web designer", "ux researcher"]
    # },
    # "management": {
    #     "chat_id": MGMT_CHAT_ID,
    #     "keywords": ["product manager", "project manager", "engineering manager", "cto", "technical lead", "team lead", "scrum master"]
    # }
}