
import re

def is_browser_user_agent(user_agent: str) -> bool:
    if not user_agent:
        return False

    if "electron/" in user_agent.lower():
        return False

    browser_patterns = ["chrome/", "firefox/", "safari/", "edg/"]
    return any(re.search(pat, user_agent, re.IGNORECASE) for pat in browser_patterns)